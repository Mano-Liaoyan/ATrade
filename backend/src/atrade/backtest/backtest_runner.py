"""The backtest queue of the Web process: starts one child process per backtest and stops it after the timeout.

The queue is the "queued" rows of the backtest table, so queued backtests stay queued after a restart. The runner
reads the timeout and the concurrency from the backtest_limits table at each queue check, so a change in the UI
applies to the next backtest that starts.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_limits import read_backtest_limits
from atrade.foundation.clock import Clock
from atrade.foundation.process_protection import create_child_environment

QUEUE_CHECK_INTERVAL_SECONDS = 0.5
# A failed child shows the end of its error output. The start of a long traceback is less useful.
MAX_ERROR_OUTPUT_CHARACTERS = 4000
RESTART_ERROR_MESSAGE = "The Web process stopped during the backtest. Start the backtest again."
CHILD_RUN_ERROR_MESSAGE = "ATrade could not run the backtest process. The Web log has the error."

logger = logging.getLogger(__name__)


def describe_child_failure(return_code: int, error_output: bytes) -> str:
    # PostgreSQL text cannot hold a NUL byte.
    error_text = error_output.decode(errors="replace").replace("\0", "").strip()[-MAX_ERROR_OUTPUT_CHARACTERS:]
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
        self.queue_error: str | None = None

    async def keep_running(self) -> None:
        """Runs until it is cancelled. Cancellation stops the running children."""
        await self.retry_until_database_answers(self.fail_running_backtests)
        async with asyncio.TaskGroup() as task_group:
            while True:
                await self.check_queue(task_group)
                await asyncio.sleep(QUEUE_CHECK_INTERVAL_SECONDS)

    async def check_queue(self, task_group: asyncio.TaskGroup) -> None:
        """An error here must not leave the TaskGroup: that cancels the running children. The next check of
        `keep_running` tries again. The same error gets one log entry."""
        try:
            await self.retry_until_database_answers(lambda: self.start_queued_backtests(task_group))
        except Exception as error:
            if self.queue_error != repr(error):
                self.queue_error = repr(error)
                logger.exception("The backtest queue check failed. The next check tries again.")
        else:
            self.queue_error = None

    async def retry_until_database_answers(self, database_step: Callable[[], Awaitable[None]]) -> None:
        """A PostgreSQL restart must not cancel the running children."""
        while True:
            try:
                await database_step()
            except psycopg.OperationalError as error:
                logger.warning("The backtest runner lost the database connection. It tries again. %s", error)
                await asyncio.sleep(QUEUE_CHECK_INTERVAL_SECONDS)
            else:
                return

    async def fail_running_backtests(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            # No child of an earlier Web process is still running: the children end with their parent.
            await backtest_store.fail_running_backtests(
                connection, ended_at_utc=self.clock.read_now_utc(), error_message=RESTART_ERROR_MESSAGE
            )

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
        """An error here must not leave this task: the TaskGroup would cancel all children and the queue."""
        try:
            await self.run_child_until_end(backtest_id, timeout_seconds=timeout_seconds)
        except Exception:
            logger.exception("The backtest runner could not run backtest %s.", backtest_id)
            await self.fail_backtest(backtest_id)
        finally:
            self.running_count -= 1

    async def fail_backtest(self, backtest_id: int) -> None:
        try:
            await self.end_backtest(backtest_id, status_if_running="failed", error_message=CHILD_RUN_ERROR_MESSAGE)
        except Exception:
            logger.exception("The backtest runner could not write the end of backtest %s.", backtest_id)

    async def run_child_until_end(self, backtest_id: int, *, timeout_seconds: int) -> None:
        process = await asyncio.create_subprocess_exec(
            *self.process_command,
            str(backtest_id),
            env={**create_child_environment(), "DATABASE_URL": self.database_url},
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
        async def write_end() -> None:
            async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
                await backtest_store.end_backtest(
                    connection,
                    backtest_id=backtest_id,
                    ended_at_utc=self.clock.read_now_utc(),
                    status_if_running=status_if_running,
                    error_message=error_message,
                )

        await self.retry_until_database_answers(write_end)
