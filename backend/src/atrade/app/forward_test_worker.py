"""Forward-test worker entry point: compares the forward test states every 2 seconds and runs the child processes.
It also runs the bar fetcher with its own client ID (docs/architecture/forward_test.md section 12.20).

Run with `python -m atrade.app.forward_test_worker`. The Compose service `forward-test` runs this module, so a
restart of `web` does not stop forward tests (docs/architecture.md section 6.4).
"""

import asyncio
import logging
import signal
import sys
from contextlib import suppress

from pydantic import ValidationError

from atrade.app.forward_test_process import FORWARD_TEST_PROCESS_COMMAND
from atrade.forward_test import BarFetcher, ChildMode, ForwardTestWorker
from atrade.foundation.clock import SystemClock
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection

logger = logging.getLogger("atrade.forward_test_worker")


class ForwardTestProcess:
    """One child process. The worker reads its exit code and asks it to stop with SIGTERM."""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self.process = process

    def read_exit_code(self) -> int | None:
        return self.process.returncode

    def request_stop(self) -> None:
        with suppress(ProcessLookupError):
            self.process.send_signal(signal.SIGTERM)


async def start_forward_test_process(forward_test_id: int, mode: ChildMode) -> ForwardTestProcess:
    # The child gets the environment of the worker: the IBKR settings and DATABASE_URL. The forward-test service has
    # no IBKR user name or password (deploy/compose.yaml).
    process = await asyncio.create_subprocess_exec(*FORWARD_TEST_PROCESS_COMMAND, str(forward_test_id), mode)
    logger.info("Started the %s child of forward test %s (PID %s).", mode, forward_test_id, process.pid)
    return ForwardTestProcess(process)


async def read_multi_instrument_member_lists() -> list[list[Instrument]]:
    """The members of each running multi-instrument forward test. There are none until multi-instrument forward tests
    exist (https://github.com/Mano-Liaoyan/ATrade/issues/217)."""
    return []


async def run_worker(settings: Settings) -> None:
    clock = SystemClock()
    worker = ForwardTestWorker(database_url=settings.database_url, clock=clock, start_child=start_forward_test_process)

    def open_bar_fetcher_connection() -> GatewayConnection:
        return IbAsyncGatewayConnection(
            host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=settings.ibkr_bar_fetcher_client_id
        )

    bar_fetcher = BarFetcher(
        database_url=settings.database_url,
        clock=clock,
        open_gateway_connection=open_bar_fetcher_connection,
        read_member_lists=read_multi_instrument_member_lists,
    )
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(worker.keep_comparing())
        task_group.create_task(bar_fetcher.keep_fetching())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("The forward-test worker does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
