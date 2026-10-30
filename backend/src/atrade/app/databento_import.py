"""Databento import program. The user runs it one time after the purchase (docs/architecture.md section 6.4).

    python -m atrade.app.databento_import <directory> [--job-id <batch job ID> ...] [--ibkr-client-id <ID>]

With `--job-id`, the program first downloads the files of each batch job to `<directory>/<job ID>/`. This needs
`DATABENTO_API_KEY`. Then it imports all DBN files (`*.dbn`, `*.dbn.zst`) below `<directory>` into databento_bar.
The import reads the IBKR daily closes of the instruments that still trade to find their stock splits, so it needs
IB Gateway (market_data.md section 8.8.3). It connects with its own client ID, default 30.
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from atrade.foundation.settings import Settings, require_usable_client_id
from atrade.ibkr import GatewayConnection, GatewayRequestError, IbAsyncGatewayConnection
from atrade.market_data import (
    DatabentoClient,
    DatabentoHistoricalClient,
    DatabentoImportError,
    DatabentoImportReport,
    import_databento_files_with_ibkr,
)

logger = logging.getLogger(__name__)
DBN_FILE_PATTERNS = ("*.dbn", "*.dbn.zst")
DEFAULT_IBKR_CLIENT_ID = 30


def find_dbn_files(directory: Path) -> list[Path]:
    return sorted(path for pattern in DBN_FILE_PATTERNS for path in directory.rglob(pattern))


async def run_databento_import(
    *,
    database_url: str,
    directory: Path,
    job_ids: list[str],
    client: DatabentoClient | None,
    gateway: GatewayConnection,
) -> DatabentoImportReport:
    if job_ids:
        if client is None:
            message = "Downloading batch jobs needs a Databento client."
            raise DatabentoImportError(message)
        for job_id in job_ids:
            client.download_batch_job(job_id, directory)
    return await import_databento_files_with_ibkr(
        database_url=database_url, file_paths=find_dbn_files(directory), gateway=gateway
    )


def read_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Imports the bought Databento daily bars into databento_bar.")
    parser.add_argument("directory", type=Path, help="The directory of the DBN files.")
    parser.add_argument("--job-id", action="append", default=[], dest="job_ids", help="A batch job to download first.")
    parser.add_argument(
        "--ibkr-client-id", type=int, default=DEFAULT_IBKR_CLIENT_ID, help="The IB Gateway client ID of the import."
    )
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
    waiting_count = sum(1 for split in report.stock_splits if split.confirmation is None)
    logger.info(
        "Found %d stock splits. %d of them wait for the check. Found %d symbol links.",
        len(report.stock_splits),
        waiting_count,
        len(report.symbol_links),
    )
    logger.info("Check them with: python -m atrade.app.databento_check")


async def import_with_gateway(
    *, settings: Settings, options: argparse.Namespace, client: DatabentoClient | None
) -> DatabentoImportReport:
    client_id: int = options.ibkr_client_id
    gateway = IbAsyncGatewayConnection(host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=client_id)
    await gateway.connect()
    try:
        return await run_databento_import(
            database_url=settings.database_url,
            directory=options.directory,
            job_ids=options.job_ids,
            client=client,
            gateway=gateway,
        )
    finally:
        gateway.disconnect()


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
        require_usable_client_id(options.ibkr_client_id)
        report = asyncio.run(import_with_gateway(settings=settings, options=options, client=client))
    except (DatabentoImportError, GatewayRequestError, ValueError) as error:
        logger.error("The Databento import saved nothing. %s", error)
        sys.exit(1)
    log_report(report)


if __name__ == "__main__":
    main()
