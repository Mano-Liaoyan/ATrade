"""The process pool of a `screen` universe: the periods run in worker processes of the child, and the runner stops the
full process group (docs/architecture/backtest.md section 10.1, docs/architecture/screen.md section 24.9).

A lock on the watchlist table holds each worker in its first read. So the tests see the real child and its real
workers in /proc. The child reads no watchlist, so it gets to the pool.
"""

import asyncio
import os
import signal
import subprocess
import sys
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
import pytest

from atrade.backtest.backtest_store import UniverseScreen
from atrade.backtest.backtest_universe import find_screen_period_starts, find_screen_run_time, run_screen_periods
from atrade.foundation.bar import TimeRange
from atrade.foundation.instrument import Instrument
from atrade.screen import run_screen_at
from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.backtest.test_screen_universe_runs import queue_screen_backtest
from tests.backtest.universe_data import AAA, BBB, CCC, save_universe_test_data
from tests.fakes.clock import FixedClock
from tests.screen.test_screen_run_routes import add_to_watchlist, make_definition

BACKEND_DIRECTORY = Path(__file__).parents[2]
CHILD_MODULE = b"atrade.app.backtest_process"
# The child, the resource tracker, the forkserver, and 1 worker for each of the 3 periods of the monthly backtest.
FULL_GROUP_SIZE = 6
ALLOWED_VARIABLES = {"PATH", "HOME", "TZ", "DATABASE_URL"}
# CPython adds this variable when it starts in the C locale. The forkserver inherits it from the child.
PYTHON_LOCALE_VARIABLE = "LC_CTYPE"
PROCESS_WAIT_STEP_SECONDS = 0.1
MAX_PROCESS_WAIT_SECONDS = 30
# Long enough for the child to start and for the test to read /proc on a loaded CI runner.
TIMEOUT_SECONDS = 20
LONG_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class ProcessFacts:
    process_id: int
    group_id: int
    state: str
    niceness: int


def read_process_ids() -> Iterator[int]:
    return (int(entry.name) for entry in Path("/proc").iterdir() if entry.name.isdigit())


def read_process_facts(process_id: int) -> ProcessFacts | None:
    try:
        stat = Path(f"/proc/{process_id}/stat").read_text()
    except OSError:
        # readability-exception: a process can end between the list of /proc and this read (G1).
        return None
    # The fields after the command name, which can have spaces. The first is field 3, the state.
    fields = stat.rpartition(")")[2].split()
    return ProcessFacts(process_id=process_id, group_id=int(fields[2]), state=fields[0], niceness=int(fields[16]))


def read_environment(process_id: int) -> dict[str, str]:
    variables = Path(f"/proc/{process_id}/environ").read_bytes().decode().split("\0")
    return dict(variable.split("=", 1) for variable in variables if variable)


def read_oom_score_adj(process_id: int) -> str:
    return Path(f"/proc/{process_id}/oom_score_adj").read_text().strip()


def find_child(database_url: str) -> int | None:
    """The backtest child of this test database. Other test workers have other databases."""
    for process_id in read_process_ids():
        try:
            if CHILD_MODULE not in Path(f"/proc/{process_id}/cmdline").read_bytes():
                continue
            if read_environment(process_id).get("DATABASE_URL") == database_url:
                return process_id
        except OSError:
            # readability-exception: a process can end or be of another user during this scan (G1).
            continue
    return None


def find_running_group(child_id: int) -> list[int]:
    """The processes of the group that still run. A killed process can stay a zombie until its new parent waits."""
    all_facts = [read_process_facts(process_id) for process_id in read_process_ids()]
    return [facts.process_id for facts in all_facts if facts and facts.group_id == child_id and facts.state != "Z"]


async def wait_for_full_group(database_url: str) -> tuple[int, list[int]]:
    for _ in range(int(MAX_PROCESS_WAIT_SECONDS / PROCESS_WAIT_STEP_SECONDS)):
        child_id = find_child(database_url)
        if child_id is not None and len(group := find_running_group(child_id)) >= FULL_GROUP_SIZE:
            return child_id, group
        await asyncio.sleep(PROCESS_WAIT_STEP_SECONDS)
    message = f"The process group of the backtest child did not get {FULL_GROUP_SIZE} processes."
    raise AssertionError(message)


async def wait_for_empty_group(child_id: int) -> None:
    for _ in range(int(MAX_PROCESS_WAIT_SECONDS / PROCESS_WAIT_STEP_SECONDS)):
        if not find_running_group(child_id):
            return
        await asyncio.sleep(PROCESS_WAIT_STEP_SECONDS)
    message = f"Processes of the group {child_id} still run: {find_running_group(child_id)}."
    raise AssertionError(message)


@asynccontextmanager
async def hold_workers_in_first_read(database_url: str) -> AsyncGenerator[None]:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        await connection.execute("LOCK TABLE watchlist_instrument IN ACCESS EXCLUSIVE MODE")
        yield
        await connection.rollback()


@pytest.mark.anyio
async def test_parallel_periods_equal_a_serial_run_in_the_same_order(database_url: str) -> None:
    save_universe_test_data(database_url)
    add_to_watchlist(database_url, AAA, BBB, CCC)
    definition = make_definition(filters=[{"field": "last_price", "operator": ">", "value": "500"}])
    screen = UniverseScreen(screen_id=1, name="Test", market="US", definition=definition)
    time_range = TimeRange(start_utc=datetime(2026, 2, 1, tzinfo=UTC), end_utc=datetime(2026, 5, 1, tzinfo=UTC))

    periods = await run_screen_periods(
        database_url=database_url, screen=screen, rebalance_period="month", time_range=time_range
    )

    serial_members: list[tuple[datetime, list[Instrument]]] = []
    for start_utc in find_screen_period_starts(time_range, "month"):
        outcome = await run_screen_at(
            database_url=database_url,
            market="US",
            definition=definition,
            as_of_utc=find_screen_run_time(start_utc),
        )
        serial_members.append((start_utc, [row.instrument for row in outcome.rows]))
    assert [(period.start_utc, period.members) for period in periods] == serial_members
    assert any(period.members for period in periods)


@pytest.mark.anyio
async def test_a_failed_period_fails_the_backtest_with_the_original_error(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    backtest_id = await queue_screen_backtest(web_client, database_url, "month")
    with psycopg.connect(database_url, autocommit=True) as connection:
        # A saved copy with a comparison that no check allows: the period raises KeyError in a worker.
        connection.execute(
            """UPDATE backtest SET universe_screen = jsonb_set(universe_screen, '{definition,filters,0,operator}', '"~"')"""
        )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=LONG_TIMEOUT_SECONDS):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "failed"
    assert "KeyError: '~'" in backtest["error_message"]


@pytest.mark.anyio
async def test_after_a_timeout_no_process_of_the_group_stays_and_each_keeps_the_isolation_controls(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ATRADE_IBKR_PASSWORD", "test-password")
    backtest_id = await queue_screen_backtest(web_client, database_url, "month")

    async with (
        hold_workers_in_first_read(database_url),
        run_backtest_runner(web_client, database_url, clock, timeout_seconds=TIMEOUT_SECONDS),
    ):
        child_id, group = await wait_for_full_group(database_url)
        for process_id in group:
            facts = read_process_facts(process_id)
            assert facts is not None
            assert facts.niceness == os.nice(0) + 10
            assert read_oom_score_adj(process_id) == "1000"
            assert set(read_environment(process_id)) - {PYTHON_LOCALE_VARIABLE} <= ALLOWED_VARIABLES
        backtest = await wait_for_final_status(web_client, backtest_id)

        assert backtest["status"] == "timed_out"
        assert find_running_group(child_id) == []


@pytest.mark.anyio
async def test_cancellation_of_the_runner_ends_the_process_group(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    await queue_screen_backtest(web_client, database_url, "month")

    async with hold_workers_in_first_read(database_url):
        async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=LONG_TIMEOUT_SECONDS):
            child_id, _ = await wait_for_full_group(database_url)

        assert find_running_group(child_id) == []


@pytest.mark.anyio
async def test_a_killed_web_process_leaves_no_process_of_the_group(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    await queue_screen_backtest(web_client, database_url, "month")

    async with hold_workers_in_first_read(database_url):
        web_process = subprocess.Popen(  # noqa: ASYNC220 - the test only starts it and kills it.
            [sys.executable, "-m", "tests.backtest.backtest_runner_program", database_url], cwd=BACKEND_DIRECTORY
        )
        try:
            child_id, _ = await wait_for_full_group(database_url)
        finally:
            web_process.kill()
            web_process.wait()

        await wait_for_empty_group(child_id)


@pytest.mark.anyio
async def test_a_killed_child_fails_the_backtest_and_its_workers_end(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    backtest_id = await queue_screen_backtest(web_client, database_url, "month")

    async with (
        hold_workers_in_first_read(database_url),
        run_backtest_runner(web_client, database_url, clock, timeout_seconds=LONG_TIMEOUT_SECONDS),
    ):
        child_id, _ = await wait_for_full_group(database_url)
        os.kill(child_id, signal.SIGKILL)
        backtest = await wait_for_final_status(web_client, backtest_id)

        assert backtest["status"] == "failed"
        assert "exit code -9" in backtest["error_message"]
        assert find_running_group(child_id) == []
