"""Forward-test worker entry point: compares the forward test states every 2 seconds and runs the child processes.

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
from atrade.forward_test import ChildMode, ForwardTestWorker
from atrade.foundation.clock import SystemClock
from atrade.foundation.settings import Settings

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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("The forward-test worker does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    worker = ForwardTestWorker(
        database_url=settings.database_url, clock=SystemClock(), start_child=start_forward_test_process
    )
    asyncio.run(worker.keep_comparing())


if __name__ == "__main__":
    main()
