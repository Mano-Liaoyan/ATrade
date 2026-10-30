"""An indicator class of `atrade.indicator` registers with `register_indicator_for_bars`, and strategy code that
imports `atrade.indicator` runs in a backtest (docs/architecture/indicator.md sections 23.1 and 23.3, #160).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from atrade.backtest.backtest_store import BacktestRequest
from atrade.backtest.strategy_engine_run import StrategyRun, run_strategy_on_bars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from tests.backtest.real_runner import run_backtest_runner, save_test_bars, start_backtest, wait_for_final_status
from tests.fakes.clock import FixedClock

RECORD_BAR_CLOSE_STRATEGY_FILE = Path(__file__).parent / "strategies" / "record_bar_close.py"
FIRST_BAR_UTC = datetime(2026, 1, 1, tzinfo=UTC)


def read_record_strategy_code(record_file: Path) -> str:
    return RECORD_BAR_CLOSE_STRATEGY_FILE.read_text().replace("/tmp/bar_close_records.txt", str(record_file))


def make_bar(index: int, close: int) -> Bar:
    return Bar(
        start_utc=FIRST_BAR_UTC + timedelta(days=index),
        open=Decimal(close),
        high=Decimal(close + 1),
        low=Decimal(close - 1),
        close=Decimal(close),
        volume=Decimal(1000),
    )


def test_on_bar_reads_an_indicator_value_that_includes_the_current_bar(tmp_path: Path) -> None:
    record_file = tmp_path / "records.txt"
    bars = [make_bar(index, close) for index, close in enumerate([101, 104, 99])]
    request = BacktestRequest(
        strategy_version_id=1,
        instrument=Instrument(symbol="CLOSE", exchange="ARCA", currency="USD"),
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=FIRST_BAR_UTC, end_utc=FIRST_BAR_UTC + timedelta(days=3)),
        paper_capital_usd=Decimal(10000),
    )
    work_directory = tmp_path / "work"
    work_directory.mkdir()

    run_strategy_on_bars(
        StrategyRun(
            code=read_record_strategy_code(record_file),
            request=request,
            starting_cash=Decimal(10000),
            bars=bars,
            look_back_bars=[],
        ),
        work_directory,
    )

    assert record_file.read_text().splitlines() == ["101.0 101.0", "104.0 104.0", "99.0 99.0"]


@pytest.mark.anyio
async def test_a_strategy_that_imports_atrade_indicator_finishes_in_a_backtest_child(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    record_file = tmp_path / "records.txt"
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, read_record_strategy_code(record_file), strategy_name="Indicator")

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    # The child received the 20 bars of the bar file, and the indicator value of each bar was its close.
    records = [line.split() for line in record_file.read_text().splitlines()]
    assert len(records) == 20
    assert all(bar_close == value for bar_close, value in records)
