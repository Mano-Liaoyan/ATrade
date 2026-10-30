"""Forward-test worker entry point: compares the forward test states every 2 seconds and runs the child processes.
It also runs the bar fetcher with its own client ID (docs/architecture/forward_test.md section 12.20) and the quarterly
US universe update (docs/architecture/market_data.md section 8.9).

Run with `python -m atrade.app.forward_test_worker`. The Compose service `forward-test` runs this module, so a
restart of `web` does not stop forward tests (docs/architecture.md section 6.4).
"""

import asyncio
import logging
import signal
import sys
from contextlib import suppress
from pathlib import Path

from pydantic import ValidationError

from atrade.app.forward_test_process import FORWARD_TEST_PROCESS_COMMAND
from atrade.forward_test import BarFetcher, ChildMode, ForwardTestRow, ForwardTestWorker, read_running_member_lists
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection
from atrade.market_data import DatabentoHistoricalClient, UsUniverseUpdate

logger = logging.getLogger("atrade.forward_test_worker")
# The service is read-only with a tmpfs on /tmp (deploy/compose.yaml). The import reads the file, so it can go.
UNIVERSE_DOWNLOAD_DIR = Path("/tmp/databento")


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


def create_us_universe_update(settings: Settings, clock: Clock) -> UsUniverseUpdate | None:
    """None without DATABENTO_API_KEY: the quarterly update does not run, and the log tells why."""
    if settings.databento_api_key is None:
        logger.warning("The quarterly US universe update does not run. DATABENTO_API_KEY is empty.")
        return None
    return UsUniverseUpdate(
        database_url=settings.database_url,
        clock=clock,
        client=DatabentoHistoricalClient(settings.databento_api_key.get_secret_value()),
        download_dir=UNIVERSE_DOWNLOAD_DIR,
    )


async def run_worker(settings: Settings) -> None:
    clock = SystemClock()
    universe_update = create_us_universe_update(settings, clock)

    def open_bar_fetcher_connection() -> GatewayConnection:
        return IbAsyncGatewayConnection(
            host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=settings.ibkr_bar_fetcher_client_id
        )

    bar_fetcher = BarFetcher(
        database_url=settings.database_url,
        clock=clock,
        open_gateway_connection=open_bar_fetcher_connection,
        read_member_lists=lambda: read_running_member_lists(settings.database_url),
    )

    def is_ready_to_run(row: ForwardTestRow) -> bool:
        # A multi-instrument child starts after the bar fetcher filled its 1-year warm-up (section 12.17).
        return row.universe_kind == "single" or bar_fetcher.is_warm_up_filled(row.id)

    worker = ForwardTestWorker(
        database_url=settings.database_url,
        clock=clock,
        start_child=start_forward_test_process,
        is_ready_to_run=is_ready_to_run,
    )
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(worker.keep_comparing())
        task_group.create_task(bar_fetcher.keep_fetching())
        if universe_update is not None:
            task_group.create_task(universe_update.keep_updating())


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
