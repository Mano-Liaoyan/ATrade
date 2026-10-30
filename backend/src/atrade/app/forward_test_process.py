"""Forward test child process entry point: runs one forward test, or only cancels its open orders.

Run with `python -m atrade.app.forward_test_process <forward test ID> <run|cancel_orders>`. The forward-test worker
starts it and sends SIGTERM to stop it (docs/architecture.md section 12.6).
"""

import asyncio
import logging
import signal
import sys

from pydantic import TypeAdapter

from atrade.forward_test import ChildMode, IbkrAccess, run_forward_test_child, run_forward_test_live_node
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection

FORWARD_TEST_PROCESS_COMMAND = [sys.executable, "-m", "atrade.app.forward_test_process"]
CHILD_MODE_ADAPTER: TypeAdapter[ChildMode] = TypeAdapter(ChildMode)


def read_child_mode(text: str) -> ChildMode:
    """The child mode of the command line. A different text raises pydantic.ValidationError."""
    return CHILD_MODE_ADAPTER.validate_python(text)


async def run_child(settings: Settings, forward_test_id: int, mode: ChildMode) -> int:
    stop_requested = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop_requested.set)

    def open_gateway_connection(client_id: int) -> GatewayConnection:
        return IbAsyncGatewayConnection(host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=client_id)

    return await run_forward_test_child(
        settings=settings,
        forward_test_id=forward_test_id,
        mode=mode,
        ibkr_access=IbkrAccess(
            open_gateway_connection=open_gateway_connection, run_live_node=run_forward_test_live_node
        ),
        stop_requested=stop_requested,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    forward_test_id = int(sys.argv[1])
    mode = read_child_mode(sys.argv[2])
    settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    sys.exit(asyncio.run(run_child(settings, forward_test_id, mode)))


if __name__ == "__main__":
    main()
