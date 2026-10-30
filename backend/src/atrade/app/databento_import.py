"""Databento import program. The user runs it one time after the purchase (docs/architecture.md section 6.4).

    python -m atrade.app.databento_import <directory> [--job-id <batch job ID> ...]

With `--job-id`, the program first downloads the files of each batch job to `<directory>/<job ID>/`. This needs
`DATABENTO_API_KEY`. Then it imports all DBN files (`*.dbn`, `*.dbn.zst`) below `<directory>` into databento_bar.
At the end, it calculates the quarterly US universe of each quarter without members (market_data.md section 8.9).
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from atrade.foundation.settings import Settings
from atrade.market_data import (
    DatabentoClient,
    DatabentoHistoricalClient,
    DatabentoImportError,
    DatabentoImportReport,
    UsUniverseCalculationError,
    calculate_us_universe_history,
    import_databento_files,
)

logger = logging.getLogger(__name__)
DBN_FILE_PATTERNS = ("*.dbn", "*.dbn.zst")


def find_dbn_files(directory: Path) -> list[Path]:
    return sorted(path for pattern in DBN_FILE_PATTERNS for path in directory.rglob(pattern))


def run_databento_import(
    *, database_url: str, directory: Path, job_ids: list[str], client: DatabentoClient | None
) -> DatabentoImportReport:
    if job_ids:
        if client is None:
            message = "Downloading batch jobs needs a Databento client."
            raise DatabentoImportError(message)
        for job_id in job_ids:
            client.download_batch_job(job_id, directory)
    return import_databento_files(database_url=database_url, file_paths=find_dbn_files(directory))


def read_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Imports the bought Databento daily bars into databento_bar.")
    parser.add_argument("directory", type=Path, help="The directory of the DBN files.")
    parser.add_argument("--job-id", action="append", default=[], dest="job_ids", help="A batch job to download first.")
    return parser.parse_args(arguments)


def log_report(report: DatabentoImportReport) -> None:
    logger.info("Saved %d Databento daily bars.", report.saved_bar_count)
    logger.info(
        "%d symbols have no official close (stat_type 11) and no bar: %s",
        len(report.symbols_without_official_close),
        " ".join(report.symbols_without_official_close),
    )
    logger.info(
        "%d EQUS.SUMMARY symbols have no listing exchange and no bar: %s",
        len(report.symbols_without_listing_exchange),
        " ".join(report.symbols_without_listing_exchange),
    )


def main(arguments: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    options = read_arguments(arguments)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("The Databento import does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    job_ids: list[str] = options.job_ids
    client: DatabentoClient | None = None
    if job_ids:
        if settings.databento_api_key is None:
            logger.error("The Databento import does not download. DATABENTO_API_KEY is empty.")
            sys.exit(1)
        client = DatabentoHistoricalClient(settings.databento_api_key.get_secret_value())
    try:
        report = run_databento_import(
            database_url=settings.database_url, directory=options.directory, job_ids=job_ids, client=client
        )
    except DatabentoImportError as error:
        logger.error("The Databento import saved nothing. %s", error)
        sys.exit(1)
    log_report(report)
    try:
        quarter_count = calculate_us_universe_history(database_url=settings.database_url)
    except UsUniverseCalculationError as error:
        logger.error("The quarterly US universe saved nothing. %s", error)
        sys.exit(1)
    logger.info("Calculated the US universe of %d quarters.", quarter_count)


if __name__ == "__main__":
    main()
