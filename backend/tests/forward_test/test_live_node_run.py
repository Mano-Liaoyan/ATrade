"""The real LiveNode run without IB Gateway: it builds the node with the strategy version and stops at the request.

Orders on a real paper account are in test_forward_test_paper_contract.py (ibkr_paper).
"""

import asyncio
import socket
from pathlib import Path

import pytest

from atrade.forward_test import LiveNodeInput, run_live_node
from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument

TEST_STRATEGY_FILE = Path(__file__).parents[1] / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
STOP_AFTER_SECONDS = 1.0
MAX_STOP_SECONDS = 30.0


def find_closed_port() -> int:
    with socket.socket() as free_socket:
        free_socket.bind(("127.0.0.1", 0))
        return free_socket.getsockname()[1]


@pytest.mark.anyio
async def test_the_live_node_stops_at_the_stop_request_while_it_waits_for_ib_gateway() -> None:
    live_node_input = LiveNodeInput(
        forward_test_id=1,
        client_id=10,
        account_id="DU1234567",
        order_id_tag="FT1",
        instrument=Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD"),
        bar_period=BarPeriod.ONE_MINUTE,
        strategy_code=TEST_STRATEGY_FILE.read_text(),
        gateway_host="127.0.0.1",
        gateway_port=find_closed_port(),
    )
    stop_requested = asyncio.Event()

    run_task = asyncio.create_task(run_live_node(live_node_input, stop_requested))
    await asyncio.sleep(STOP_AFTER_SECONDS)
    # The node waits for the IB clients to connect. It does not end by itself.
    assert not run_task.done()
    stop_requested.set()

    await asyncio.wait_for(run_task, MAX_STOP_SECONDS)
