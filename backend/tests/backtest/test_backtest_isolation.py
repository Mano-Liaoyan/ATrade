"""Isolation of the backtest child process: timeout, queue, environment allow list, oom_score_adj, and nice.

The tests run real child processes with the test strategy `strategies/write_process_facts.py`. The strategy
writes its environment, `oom_score_adj`, niceness, and process ID to a log file in the test directory.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.backtest.real_runner import (
    TEST_DIRECTORY,
    TEST_STRATEGY_FILE,
    run_backtest_runner,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
    wait_for_status,
)
from tests.fakes.clock import FixedClock

PROCESS_FACTS_STRATEGY_FILE = TEST_DIRECTORY / "strategies" / "write_process_facts.py"
IBKR_TEST_VARIABLES = {
    "ATRADE_IBKR_USERNAME": "test-user",
    "ATRADE_IBKR_PASSWORD": "test-password",
    "ATRADE_IBKR_ACCOUNT_ID": "DU1234567",
    "ATRADE_IBKR_HOST": "ib-gateway",
}


def make_process_facts_code(process_facts_file: Path, *, loop_forever_in_on_bar: bool) -> str:
    code = PROCESS_FACTS_STRATEGY_FILE.read_text()
    code = code.replace(
        'PROCESS_FACTS_FILE = "/tmp/process_facts.json"', f'PROCESS_FACTS_FILE = "{process_facts_file}"'
    )
    return code.replace("LOOP_FOREVER_IN_ON_BAR = False", f"LOOP_FOREVER_IN_ON_BAR = {loop_forever_in_on_bar}")


def read_process_facts(process_facts_file: Path) -> dict[str, Any]:
    return json.loads(process_facts_file.read_text())


def is_process_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        # readability-exception: os.kill reports a missing process only as an exception (G1).
        return False
    return True


@pytest.mark.anyio
async def test_backtest_longer_than_the_timeout_is_timed_out_and_its_child_process_ends(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    save_test_bars(database_url)
    process_facts_file = tmp_path / "process_facts.json"
    backtest_id = await start_backtest(
        web_client, make_process_facts_code(process_facts_file, loop_forever_in_on_bar=True)
    )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=2):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "timed_out"
    assert backtest["metrics"] is None
    assert backtest["ended_at_utc"] is not None
    assert not is_process_alive(read_process_facts(process_facts_file)["process_id"])


@pytest.mark.anyio
async def test_child_process_gets_no_ibkr_variables(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in IBKR_TEST_VARIABLES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("TZ", "UTC")
    save_test_bars(database_url)
    process_facts_file = tmp_path / "process_facts.json"
    backtest_id = await start_backtest(
        web_client, make_process_facts_code(process_facts_file, loop_forever_in_on_bar=False)
    )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    environment = read_process_facts(process_facts_file)["environment"]
    assert [name for name in environment if "IBKR" in name] == []
    assert environment["DATABASE_URL"] == database_url
    assert environment["TZ"] == "UTC"
    assert [name for name in environment if name.startswith("ATRADE_")] == []


@pytest.mark.anyio
async def test_child_process_is_the_first_to_stop_when_memory_is_low_and_runs_with_nice_10(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    save_test_bars(database_url)
    process_facts_file = tmp_path / "process_facts.json"
    backtest_id = await start_backtest(
        web_client, make_process_facts_code(process_facts_file, loop_forever_in_on_bar=False)
    )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    process_facts = read_process_facts(process_facts_file)
    assert process_facts["oom_score_adj"] == 1000
    assert process_facts["niceness"] == os.nice(0) + 10


@pytest.mark.anyio
async def test_with_concurrency_1_the_second_backtest_waits_in_the_queue(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    save_test_bars(database_url)
    endless_code = make_process_facts_code(tmp_path / "process_facts.json", loop_forever_in_on_bar=True)
    first_backtest_id = await start_backtest(web_client, endless_code)
    second_backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text(), strategy_name="Second")

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=3, concurrency=1):
        await wait_for_status(web_client, first_backtest_id, "running")
        await asyncio.sleep(1)
        second_backtest_while_first_runs = (await web_client.get(f"/api/backtests/{second_backtest_id}")).json()
        first_backtest = await wait_for_final_status(web_client, first_backtest_id)
        second_backtest = await wait_for_final_status(web_client, second_backtest_id)

    assert second_backtest_while_first_runs["status"] == "queued"
    assert first_backtest["status"] == "timed_out"
    assert second_backtest["status"] == "finished", second_backtest["error_message"]


@pytest.mark.anyio
async def test_with_concurrency_2_two_backtests_run_at_the_same_time(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    save_test_bars(database_url)
    first_backtest_id = await start_backtest(
        web_client, make_process_facts_code(tmp_path / "first.json", loop_forever_in_on_bar=True)
    )
    second_backtest_id = await start_backtest(
        web_client,
        make_process_facts_code(tmp_path / "second.json", loop_forever_in_on_bar=True),
        strategy_name="Second",
    )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=3, concurrency=2):
        await wait_for_status(web_client, first_backtest_id, "running")
        await wait_for_status(web_client, second_backtest_id, "running")
        first_backtest_while_second_runs = (await web_client.get(f"/api/backtests/{first_backtest_id}")).json()
        second_backtest = await wait_for_final_status(web_client, second_backtest_id)

    assert first_backtest_while_second_runs["status"] == "running"
    assert second_backtest["status"] == "timed_out"
