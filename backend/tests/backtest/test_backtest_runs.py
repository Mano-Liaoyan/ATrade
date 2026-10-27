"""Backtests that run in a real child process on the small bar file and the test strategy.

The runner of each test starts real child processes (`python -m atrade.app.backtest_process`). The tests read
the status and the result through the HTTP routes.
"""

import asyncio
import csv
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from atrade.app.backtest_process import BACKTEST_PROCESS_COMMAND
from atrade.backtest import BacktestRunner
from tests.fakes.clock import FixedClock

TEST_DIRECTORY = Path(__file__).parent
TEST_STRATEGY_FILE = TEST_DIRECTORY / "strategies" / "buy_and_sell_by_bar_count.py"
TEST_BAR_FILE = TEST_DIRECTORY / "bars" / "btest_arca_usd_1_day.csv"
FINAL_STATUSES = {"finished", "failed", "timed_out"}
WAIT_STEP_SECONDS = 0.2
MAX_WAIT_SECONDS = 60


def save_test_bars(database_url: str) -> None:
    with TEST_BAR_FILE.open() as bar_file:
        bar_rows = list(csv.DictReader(bar_file))
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', %(start_utc)s, %(open)s, %(high)s, %(low)s, %(close)s,
                %(volume)s)
            """,
            bar_rows,
        )


async def start_backtest(web_client: httpx.AsyncClient, code: str) -> int:
    strategy = (await web_client.post("/api/strategies", json={"name": "Bar count"})).json()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    response = await web_client.post(
        "/api/backtests",
        json={
            "strategy_version_id": version["id"],
            "symbol": "BTEST",
            "exchange": "ARCA",
            "currency": "USD",
            "bar_period": "1-DAY",
            "start_utc": "2026-03-01T00:00:00Z",
            "end_utc": "2026-04-01T00:00:00Z",
            "paper_capital_usd": "10000",
        },
    )
    return response.json()["id"]


async def wait_for_final_status(web_client: httpx.AsyncClient, backtest_id: int) -> dict[str, Any]:
    for _ in range(int(MAX_WAIT_SECONDS / WAIT_STEP_SECONDS)):
        backtest = (await web_client.get(f"/api/backtests/{backtest_id}")).json()
        if backtest["status"] in FINAL_STATUSES:
            return backtest
        await asyncio.sleep(WAIT_STEP_SECONDS)
    message = f"Backtest {backtest_id} did not end in {MAX_WAIT_SECONDS} seconds."
    raise AssertionError(message)


@asynccontextmanager
async def run_backtest_runner(database_url: str, clock: FixedClock, *, timeout_seconds: float) -> AsyncGenerator[None]:
    runner = BacktestRunner(
        database_url=database_url,
        clock=clock,
        process_command=BACKTEST_PROCESS_COMMAND,
        timeout_seconds=timeout_seconds,
        concurrency=1,
    )
    runner_task = asyncio.create_task(runner.keep_running())
    try:
        yield
    finally:
        runner_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner_task


@pytest.mark.anyio
async def test_finished_backtest_shows_metrics_equity_curve_and_trades(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())

    async with run_backtest_runner(database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert backtest["error_message"] is None
    assert backtest["started_at_utc"] == "2026-01-02T03:04:05Z"
    assert backtest["ended_at_utc"] is not None
    # Each market order fills at the close of the bar that sent it: bars 3, 8, and 13 close at 104, 106, and 96.
    assert backtest["trades"] == [
        {
            "time_utc": "2026-03-05T00:00:00Z",
            "side": "BUY",
            "quantity_shares": "10",
            "price_usd": "104.00",
            "commission_usd": "0.00",
        },
        {
            "time_utc": "2026-03-10T00:00:00Z",
            "side": "SELL",
            "quantity_shares": "10",
            "price_usd": "106.00",
            "commission_usd": "0.00",
        },
        {
            "time_utc": "2026-03-15T00:00:00Z",
            "side": "BUY",
            "quantity_shares": "10",
            "price_usd": "96.00",
            "commission_usd": "0.00",
        },
    ]
    # 10000 + 10 * (106 - 104) + 10 * (110 - 96) = 10160. The peak 10060 falls to 10020: 40 / 10060 = 0.40 %.
    assert backtest["metrics"] == {
        "final_equity_usd": "10160.00",
        "total_return_percent": "1.60",
        "max_drawdown_percent": "0.40",
        "trade_count": 3,
    }
    equity_curve = backtest["equity_curve"]
    assert [point["equity_usd"] for point in equity_curve] == [
        "10000.00", "10000.00", "10000.00", "10020.00", "10040.00", "10060.00", "10040.00", "10020.00",
        "10020.00", "10020.00", "10020.00", "10020.00", "10020.00", "10040.00", "10060.00", "10080.00",
        "10100.00", "10120.00", "10140.00", "10160.00",
    ]  # fmt: skip
    assert equity_curve[0]["time_utc"] == "2026-03-03T00:00:00Z"
    assert equity_curve[-1]["time_utc"] == "2026-03-22T00:00:00Z"


@pytest.mark.anyio
async def test_failed_backtest_shows_the_strategy_error(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    failing_code = TEST_STRATEGY_FILE.read_text().replace(
        "        self.bar_count += 1\n", "        self.bar_count += 1\n        raise ValueError('no trade today')\n"
    )
    backtest_id = await start_backtest(web_client, failing_code)

    async with run_backtest_runner(database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "failed"
    assert "ValueError: no trade today" in backtest["error_message"]
    assert "in on_bar" in backtest["error_message"]
    assert backtest["metrics"] is None


@pytest.mark.anyio
async def test_backtest_without_saved_bars_fails_with_a_clear_message(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())

    async with run_backtest_runner(database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "failed"
    assert backtest["error_message"] == (
        "PostgreSQL has no saved 1-DAY bars of BTEST / ARCA / USD from 2026-03-01T00:00:00+00:00"
        " to 2026-04-01T00:00:00+00:00. Open the bar chart of the instrument to load bars from IBKR."
    )


@pytest.mark.anyio
async def test_backtest_longer_than_the_timeout_is_timed_out(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    endless_code = TEST_STRATEGY_FILE.read_text().replace(
        "        self.bar_count += 1\n", "        while self.bar_count >= 0:\n            self.bar_count += 1\n"
    )
    backtest_id = await start_backtest(web_client, endless_code)

    async with run_backtest_runner(database_url, clock, timeout_seconds=2):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "timed_out"
    assert backtest["metrics"] is None
