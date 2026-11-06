"""The backtest runner keeps its children and its queue when PostgreSQL is not reachable for a time.

Real PostgreSQL. The child process is a short sleep: the database loss is the subject, not the backtest.
"""

import asyncio
import sys

import httpx
import pytest

from atrade.backtest import BacktestRunner
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
    wait_for_status,
)
from tests.fakes.clock import FixedClock

UNREACHABLE_DATABASE_URL = "postgresql://atrade:wrong@127.0.0.1:1/atrade?connect_timeout=1"
CHILD_SECONDS = 1.0
SHORT_CHILD_COMMAND = [sys.executable, "-c", f"import time; time.sleep({CHILD_SECONDS})"]


@pytest.mark.anyio
async def test_a_lost_database_stops_neither_the_runner_nor_its_child(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    code = TEST_STRATEGY_FILE.read_text()
    first_backtest_id = await start_backtest(web_client, code)
    runner = BacktestRunner(database_url=database_url, clock=clock, process_command=SHORT_CHILD_COMMAND)
    runner_task = asyncio.create_task(runner.keep_running())
    await wait_for_status(web_client, first_backtest_id, "running")

    runner.database_url = UNREACHABLE_DATABASE_URL
    await asyncio.sleep(CHILD_SECONDS + 0.5)
    assert not runner_task.done()
    runner.database_url = database_url

    first_backtest = await wait_for_final_status(web_client, first_backtest_id)
    assert "exit code 0" in first_backtest["error_message"]
    second_backtest_id = await start_backtest(web_client, code, strategy_name="Second")
    await wait_for_final_status(web_client, second_backtest_id)
    runner_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner_task


@pytest.mark.anyio
async def test_the_runner_waits_for_the_database_at_its_start(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())
    runner = BacktestRunner(database_url=UNREACHABLE_DATABASE_URL, clock=clock, process_command=SHORT_CHILD_COMMAND)
    runner_task = asyncio.create_task(runner.keep_running())
    await asyncio.sleep(0.1)
    assert not runner_task.done()

    runner.database_url = database_url

    await wait_for_final_status(web_client, backtest_id)
    runner_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner_task
