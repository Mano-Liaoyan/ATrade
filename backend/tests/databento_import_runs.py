"""Test helper: the Databento import of the import program, then the IBKR stock split check program with the IBKR fake
(docs/architecture/market_data.md section 8.8.3)."""

from datetime import UTC, datetime
from pathlib import Path

from atrade.market_data import DatabentoImportReport, import_databento_files, run_ibkr_split_check
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

SPLIT_CHECK_TIME_UTC = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


async def skip_wait(_seconds: float) -> None:
    return None


async def import_and_check_splits(
    database_url: str, file_paths: list[Path], gateway: FakeGatewayConnection
) -> DatabentoImportReport:
    report = import_databento_files(database_url=database_url, file_paths=file_paths, still_trading_rule="ibkr_check")
    await run_ibkr_split_check(
        database_url=database_url, gateway=gateway, clock=FixedClock(SPLIT_CHECK_TIME_UTC), wait=skip_wait
    )
    return report
