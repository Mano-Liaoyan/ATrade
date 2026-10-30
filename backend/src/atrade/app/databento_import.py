"""Databento import program. The user runs it one time after the purchase (docs/architecture.md section 6.4).

    python -m atrade.app.databento_import <directory> [--job-id <batch job ID> ...] [--ibkr-client-id <ID>]
    python -m atrade.app.databento_import --hourly-cost

With `--job-id`, the program first downloads the files of each batch job to `<directory>/<job ID>/`. This needs
`DATABENTO_API_KEY`. Then it imports all DBN files (`*.dbn`, `*.dbn.zst`) below `<directory>` into databento_bar.
The import reads the IBKR daily closes of the instruments that still trade to find their stock splits, so it needs
IB Gateway (market_data.md section 8.8.3). It connects with its own client ID, default 30.
At the end, it calculates the quarterly US universe of each quarter without members (market_data.md section 8.9).

With `--hourly-cost`, the program imports nothing. It prints the purchase list of the hourly bars (the universe
instruments of each quarter) and its cost from `metadata.get_cost`, before the user buys them (market_data.md section
8.8.1). Reading the cost is free. This needs `DATABENTO_API_KEY`.
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from atrade.foundation.settings import Settings, require_usable_client_id
from atrade.ibkr import GatewayConnection, GatewayRequestError, IbAsyncGatewayConnection
from atrade.market_data import (
    DatabentoClient,
    DatabentoHistoricalClient,
    DatabentoImportError,
    DatabentoImportReport,
    UsUniverseCalculationError,
    calculate_us_universe_history,
    import_databento_files_with_ibkr,
    list_hourly_purchases,
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
    parser = argparse.ArgumentParser(description="Imports the bought Databento bars into databento_bar.")
    parser.add_argument("directory", type=Path, nargs="?", help="The directory of the DBN files.")
    parser.add_argument(
        "--hourly-cost", action="store_true", help="Print the hourly bar purchase list and its cost. Imports nothing."
    )
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
    if report.symbols_without_daily_bar:
        logger.info(
            "%d symbols have hourly bars on a day without a Databento daily bar. No hourly bar of that day: %s",
            len(report.symbols_without_daily_bar),
            " ".join(report.symbols_without_daily_bar),
        )


def log_hourly_costs(*, database_url: str, client: DatabentoClient, end_day: date) -> Decimal:
    """Prints the hourly bar purchase list and its cost (section 8.8.1). Returns the total cost in USD."""
    purchases = list_hourly_purchases(database_url=database_url, end_day=end_day)
    total = Decimal(0)
    for purchase in purchases:
        cost = client.read_hourly_cost(purchase.symbols, purchase.start, purchase.end)
        total += cost
        logger.info(
            "XNAS.ITCH ohlcv-1h %s to %s: %d symbols, %s USD: %s",
            purchase.start,
            purchase.end,
            len(purchase.symbols),
            cost,
            " ".join(purchase.symbols),
        )
    logger.info("The hourly bars of %d quarters cost %s USD.", len(purchases), total)
    return total


def calculate_us_universe_quarters(database_url: str) -> None:
    try:
        quarter_count = calculate_us_universe_history(database_url=database_url)
    except UsUniverseCalculationError as error:
        logger.error("The quarterly US universe saved nothing. %s", error)
        sys.exit(1)
    logger.info("Calculated the US universe of %d quarters.", quarter_count)


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
    if options.hourly_cost:
        if settings.databento_api_key is None:
            logger.error("The program does not read the cost. DATABENTO_API_KEY is empty.")
            sys.exit(1)
        hourly_client = DatabentoHistoricalClient(settings.databento_api_key.get_secret_value())
        log_hourly_costs(database_url=settings.database_url, client=hourly_client, end_day=datetime.now(UTC).date())
        return
    if options.directory is None:
        logger.error("The Databento import needs the directory of the DBN files.")
        sys.exit(1)
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
    calculate_us_universe_quarters(settings.database_url)


if __name__ == "__main__":
    main()
