"""Helpers of the tests that run backtests in real child processes: save the bars and the strategy, start the
backtest through the HTTP routes, wait for its end, and run a real backtest runner.
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
from atrade.foundation.instrument import Instrument
from tests.fakes.clock import FixedClock
from tests.saved_ranges import save_ibkr_saved_range

TEST_DIRECTORY = Path(__file__).parent
TEST_STRATEGY_FILE = TEST_DIRECTORY / "strategies" / "buy_and_sell_by_bar_count.py"
TEST_BAR_FILE = TEST_DIRECTORY / "bars" / "btest_arca_usd_1_day.csv"
FINAL_STATUSES = {"finished", "failed", "timed_out"}
WAIT_STEP_SECONDS = 0.2
MAX_WAIT_SECONDS = 60


def save_test_bars(database_url: str, *, exchange: str = "ARCA", currency: str = "USD") -> None:
    """Saves the bars of the bar file as BTEST bars of the exchange and the currency."""
    with TEST_BAR_FILE.open() as bar_file:
        bar_rows = [{**row, "exchange": exchange, "currency": currency} for row in csv.DictReader(bar_file)]
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('BTEST', %(exchange)s, %(currency)s, '1-DAY', %(start_utc)s, %(open)s, %(high)s, %(low)s,
                %(close)s, %(volume)s)
            """,
            bar_rows,
        )
        save_ibkr_saved_range(connection, Instrument(symbol="BTEST", exchange=exchange, currency=currency), "1-DAY")


async def start_backtest(web_client: httpx.AsyncClient, code: str, *, strategy_name: str = "Bar count") -> int:
    strategy = (await web_client.post("/api/strategies", json={"name": strategy_name})).json()
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


async def wait_for_status(web_client: httpx.AsyncClient, backtest_id: int, status: str) -> dict[str, Any]:
    for _ in range(int(MAX_WAIT_SECONDS / WAIT_STEP_SECONDS)):
        backtest = (await web_client.get(f"/api/backtests/{backtest_id}")).json()
        if backtest["status"] == status:
            return backtest
        await asyncio.sleep(WAIT_STEP_SECONDS)
    message = f"Backtest {backtest_id} did not get the status {status} in {MAX_WAIT_SECONDS} seconds."
    raise AssertionError(message)


@asynccontextmanager
async def run_backtest_runner(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, *, timeout_seconds: int, concurrency: int = 1
) -> AsyncGenerator[None]:
    """Sets the backtest limits through the HTTP route, then runs a real runner until the block ends."""
    limits = {"timeout_seconds": timeout_seconds, "concurrency": concurrency}
    assert (await web_client.put("/api/backtest-limits", json=limits)).status_code == 200
    runner = BacktestRunner(database_url=database_url, clock=clock, process_command=BACKTEST_PROCESS_COMMAND)
    runner_task = asyncio.create_task(runner.keep_running())
    try:
        yield
    finally:
        runner_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner_task
