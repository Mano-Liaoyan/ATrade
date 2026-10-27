"""The backtest queue of the Web process: starts one child process per backtest and stops it after the timeout.

The queue is the "queued" rows of the backtest table, so queued backtests stay queued after a restart. The runner
reads the timeout and the concurrency from the backtest_limits table at each queue check, so a change in the UI
applies to the next backtest that starts.
"""

import asyncio
import os
from contextlib import suppress

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_limits import read_backtest_limits
from atrade.foundation.clock import Clock

QUEUE_CHECK_INTERVAL_SECONDS = 0.5
# The child gets only these variables. IBKR and Cloudflare secrets stay in the Web process (section 10).
CHILD_ENVIRONMENT_ALLOW_LIST = ("PATH", "HOME", "TZ")
# A failed child shows the end of its error output. The start of a long traceback is less useful.
MAX_ERROR_OUTPUT_CHARACTERS = 4000
RESTART_ERROR_MESSAGE = "The Web process stopped during the backtest. Start the backtest again."


def create_child_environment(database_url: str) -> dict[str, str]:
    child_environment = {name: os.environ[name] for name in CHILD_ENVIRONMENT_ALLOW_LIST if name in os.environ}
    child_environment["DATABASE_URL"] = database_url
    return child_environment


def describe_child_failure(return_code: int, error_output: bytes) -> str:
    error_text = error_output.decode(errors="replace").strip()[-MAX_ERROR_OUTPUT_CHARACTERS:]
    if not error_text:
        return f"The backtest process ended with exit code {return_code} and no result."
    return f"The backtest process ended with exit code {return_code} and no result:\n{error_text}"


class BacktestRunner:
    """`process_command` starts the child process. The runner adds the backtest ID as the last argument."""

    def __init__(
        self,
        *,
        database_url: str,
        clock: Clock,
        process_command: list[str],
    ) -> None:
        self.database_url = database_url
        self.clock = clock
        self.process_command = process_command
        self.running_count = 0

    async def keep_running(self) -> None:
        """Runs until it is cancelled. Cancellation stops the running children."""
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            # No child of an earlier Web process is still running: the children end with their parent.
            await backtest_store.fail_running_backtests(
                connection, ended_at_utc=self.clock.read_now_utc(), error_message=RESTART_ERROR_MESSAGE
            )
        async with asyncio.TaskGroup() as task_group:
            while True:
                await self.start_queued_backtests(task_group)
                await asyncio.sleep(QUEUE_CHECK_INTERVAL_SECONDS)

    async def start_queued_backtests(self, task_group: asyncio.TaskGroup) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            limits = await read_backtest_limits(connection)
            while self.running_count < limits.concurrency:
                backtest_id = await backtest_store.start_next_queued_backtest(
                    connection, started_at_utc=self.clock.read_now_utc()
                )
                if backtest_id is None:
                    return
                self.running_count += 1
                task_group.create_task(self.run_child(backtest_id, timeout_seconds=limits.timeout_seconds))

    async def run_child(self, backtest_id: int, *, timeout_seconds: int) -> None:
        try:
            await self.run_child_until_end(backtest_id, timeout_seconds=timeout_seconds)
        finally:
            self.running_count -= 1

    async def run_child_until_end(self, backtest_id: int, *, timeout_seconds: int) -> None:
        process = await asyncio.create_subprocess_exec(
            *self.process_command,
            str(backtest_id),
            env=create_child_environment(self.database_url),
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, error_output = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            # readability-exception: asyncio reports the timeout only as an exception (G1).
            await self.stop_child(process)
            await self.end_backtest(backtest_id, status_if_running="timed_out", error_message=None)
            return
        finally:
            if process.returncode is None:
                await self.stop_child(process)
        return_code = 0 if process.returncode is None else process.returncode
        await self.end_backtest(
            backtest_id, status_if_running="failed", error_message=describe_child_failure(return_code, error_output)
        )

    async def stop_child(self, process: asyncio.subprocess.Process) -> None:
        with suppress(ProcessLookupError):
            process.kill()
        await process.wait()

    async def end_backtest(
        self, backtest_id: int, *, status_if_running: backtest_store.BacktestStatus, error_message: str | None
    ) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await backtest_store.end_backtest(
                connection,
                backtest_id=backtest_id,
                ended_at_utc=self.clock.read_now_utc(),
                status_if_running=status_if_running,
                error_message=error_message,
            )
