"""The backtest runner keeps its children and its queue when PostgreSQL is not reachable for a time.

Real PostgreSQL. The child process is a short sleep: the database loss is the subject, not the backtest.
"""

import asyncio
import sys
import time

import httpx
import psycopg
import pytest

from atrade.backtest import BacktestRunner, backtest_runner
from atrade.backtest.backtest_limits import BacktestLimits, read_backtest_limits
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
    wait_for_status,
)
from tests.fakes.clock import FixedClock

# The text of a backtest that the runner could not run (backtest_runner.py).
CHILD_RUN_ERROR_MESSAGE = "ATrade could not run the backtest process. The Web log has the error."
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
async def test_a_nul_byte_in_the_child_error_output_ends_only_that_backtest(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    """PostgreSQL text cannot hold a NUL byte. The write raises DataError without the removal."""
    save_test_bars(database_url)
    code = TEST_STRATEGY_FILE.read_text()
    first_backtest_id = await start_backtest(web_client, code)
    command = [sys.executable, "-c", r"import sys; sys.stderr.write('before\0after')"]
    runner = BacktestRunner(database_url=database_url, clock=clock, process_command=command)
    runner_task = asyncio.create_task(runner.keep_running())

    await asyncio.wait({runner_task}, timeout=2.0)
    assert not runner_task.done()
    first_backtest = await wait_for_final_status(web_client, first_backtest_id)
    second_backtest_id = await start_backtest(web_client, code, strategy_name="Second")
    await wait_for_final_status(web_client, second_backtest_id)

    assert first_backtest["status"] == "failed"
    assert first_backtest["error_message"].endswith("beforeafter")
    runner_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner_task


@pytest.mark.anyio
async def test_a_child_that_does_not_start_fails_its_backtest_and_the_runner_continues(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    code = TEST_STRATEGY_FILE.read_text()
    first_backtest_id = await start_backtest(web_client, code)
    runner = BacktestRunner(database_url=database_url, clock=clock, process_command=["/no/such/backtest/command"])
    runner_task = asyncio.create_task(runner.keep_running())

    await asyncio.wait({runner_task}, timeout=2.0)
    assert not runner_task.done()
    first_backtest = await wait_for_final_status(web_client, first_backtest_id)
    second_backtest_id = await start_backtest(web_client, code, strategy_name="Second")
    second_backtest = await wait_for_final_status(web_client, second_backtest_id)

    assert first_backtest["status"] == "failed"
    assert first_backtest["error_message"] == CHILD_RUN_ERROR_MESSAGE
    assert second_backtest["status"] == "failed"
    assert runner.running_count == 0
    runner_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await runner_task


@pytest.mark.anyio
async def test_an_error_of_the_queue_check_does_not_end_the_runner_and_it_waits_before_the_next_check(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())
    check_times: list[float] = []

    async def fail_two_times(connection: psycopg.AsyncConnection) -> BacktestLimits:
        check_times.append(time.monotonic())
        if len(check_times) <= 2:
            message = "not an operational error"
            raise ValueError(message)
        return await read_backtest_limits(connection)

    monkeypatch.setattr(backtest_runner, "read_backtest_limits", fail_two_times)
    runner = BacktestRunner(database_url=database_url, clock=clock, process_command=SHORT_CHILD_COMMAND)
    runner_task = asyncio.create_task(runner.keep_running())

    await asyncio.wait({runner_task}, timeout=2.0)
    assert not runner_task.done()
    await wait_for_final_status(web_client, backtest_id)

    assert check_times[1] - check_times[0] >= backtest_runner.QUEUE_CHECK_INTERVAL_SECONDS / 2
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
