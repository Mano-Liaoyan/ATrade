"""The real LiveNode run without IB Gateway: it builds the node with the strategy version, stops at the request, and
stops when IB Gateway is not reachable for too long.

Orders on a real paper account are in test_forward_test_paper_contract.py (ibkr_paper).
"""

import asyncio
import socket
from pathlib import Path

import pytest

from atrade.forward_test import GatewayWatch, LiveNodeInput, run_live_node
from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument

TEST_STRATEGY_FILE = Path(__file__).parents[1] / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
STOP_AFTER_SECONDS = 1.0
MAX_STOP_SECONDS = 30.0


def find_closed_port() -> int:
    with socket.socket() as free_socket:
        free_socket.bind(("127.0.0.1", 0))
        return free_socket.getsockname()[1]


def make_live_node_input() -> LiveNodeInput:
    return LiveNodeInput(
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


@pytest.mark.anyio
async def test_the_live_node_stops_at_the_stop_request_while_it_waits_for_ib_gateway() -> None:
    stop_requested = asyncio.Event()

    run_task = asyncio.create_task(run_live_node(make_live_node_input(), stop_requested))
    await asyncio.sleep(STOP_AFTER_SECONDS)
    # The node waits for the IB clients to connect. It does not end by itself.
    assert not run_task.done()
    stop_requested.set()

    assert await asyncio.wait_for(run_task, MAX_STOP_SECONDS) == "ended"


@pytest.mark.anyio
async def test_the_live_node_stops_when_ib_gateway_is_not_reachable_for_too_long() -> None:
    gateway_watch = GatewayWatch(check_interval_seconds=0.1, lost_after_seconds=0.5)

    live_node_end = await asyncio.wait_for(
        run_live_node(make_live_node_input(), asyncio.Event(), gateway_watch=gateway_watch), MAX_STOP_SECONDS
    )

    assert live_node_end == "gateway_lost"
