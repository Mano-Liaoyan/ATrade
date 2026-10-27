"""The real LiveNode run without IB Gateway: it builds the node with the strategy version, stops at the request, and
stops when IB Gateway is not reachable for too long. The warm-up catalog answers `request_bars` without IBKR.

Orders on a real paper account are in test_forward_test_paper_contract.py (ibkr_paper).
"""

import asyncio
import socket
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType
from nautilus_trader.trading import Strategy

from atrade.backtest import write_look_back_catalog
from atrade.forward_test import GatewayWatch, LiveNodeInput, run_live_node
from atrade.forward_test.live_node_run import create_live_node_builder
from atrade.foundation.bar import Bar, BarPeriod, floor_to_bar_start
from atrade.foundation.instrument import Instrument

TEST_STRATEGY_FILE = Path(__file__).parents[1] / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
STOP_AFTER_SECONDS = 1.0
MAX_STOP_SECONDS = 30.0


def find_closed_port() -> int:
    with socket.socket() as free_socket:
        free_socket.bind(("127.0.0.1", 0))
        return free_socket.getsockname()[1]


def make_live_node_input(database_url: str) -> LiveNodeInput:
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
        database_url=database_url,
        start_balance_usd=Decimal(100000),
        warm_up_bars=(),
    )


@pytest.mark.anyio
async def test_the_live_node_stops_at_the_stop_request_while_it_waits_for_ib_gateway(database_url: str) -> None:
    stop_requested = asyncio.Event()

    run_task = asyncio.create_task(run_live_node(make_live_node_input(database_url), stop_requested))
    await asyncio.sleep(STOP_AFTER_SECONDS)
    # The node waits for the IB clients to connect. It does not end by itself.
    assert not run_task.done()
    stop_requested.set()

    assert await asyncio.wait_for(run_task, MAX_STOP_SECONDS) == "ended"


@pytest.mark.anyio
async def test_the_live_node_stops_when_ib_gateway_is_not_reachable_for_too_long(database_url: str) -> None:
    gateway_watch = GatewayWatch(check_interval_seconds=0.1, lost_after_seconds=0.5)

    live_node_end = await asyncio.wait_for(
        run_live_node(make_live_node_input(database_url), asyncio.Event(), gateway_watch=gateway_watch),
        MAX_STOP_SECONDS,
    )

    assert live_node_end == "gateway_lost"


APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
WARM_UP_BAR_COUNT = 3000
BAR_TYPE = "AAPL.NASDAQ-1-MINUTE-LAST-EXTERNAL"
REQUEST_WAIT_SECONDS = 2.0


class WarmUpConfig(StrategyConfig):
    pass


class WarmUpStrategy(Strategy):
    """Asks for 7 days of 1-minute bars, like the example strategies. IBKR refuses that request (error 321)."""

    def __init__(self, config: WarmUpConfig) -> None:
        super().__init__(config)
        self.received_bars: list[NautilusBar] = []

    def on_start(self) -> None:
        self.request_bars(BarType.from_str(BAR_TYPE), start=self.clock.utc_now() - timedelta(days=7))  # pyright: ignore[reportUnknownMemberType]

    def on_historical_bars(self, bars: Sequence[NautilusBar]) -> None:
        self.received_bars.extend(bars)


def make_warm_up_bars() -> tuple[Bar, ...]:
    end_utc = floor_to_bar_start(datetime.now(UTC), BarPeriod.ONE_MINUTE)
    return tuple(
        Bar(
            start_utc=end_utc - timedelta(minutes=WARM_UP_BAR_COUNT - index),
            open=Decimal("100.5"),
            high=Decimal(101),
            low=Decimal(100),
            close=Decimal("100.25"),
            volume=Decimal(10),
        )
        for index in range(WARM_UP_BAR_COUNT)
    )


@pytest.mark.anyio
async def test_the_warm_up_catalog_answers_a_7_day_request_of_1_minute_bars(database_url: str, tmp_path: Path) -> None:
    live_node_input = make_live_node_input(database_url)
    catalog = write_look_back_catalog(list(make_warm_up_bars()), APPLE, BarPeriod.ONE_MINUTE, tmp_path)
    # No IB clients: the request can reach only the catalog.
    live_node = create_live_node_builder(live_node_input, BarType.from_str(BAR_TYPE).instrument_id, catalog).build()
    strategy = WarmUpStrategy(WarmUpConfig())
    live_node.add_strategy(strategy)
    run_task = asyncio.create_task(live_node.run_async())
    try:
        await asyncio.sleep(REQUEST_WAIT_SECONDS)
    finally:
        live_node.handle().stop()
        await asyncio.wait_for(run_task, MAX_STOP_SECONDS)
        live_node.dispose()

    assert len(strategy.received_bars) == WARM_UP_BAR_COUNT
    assert strategy.received_bars[-1].close.as_double() == pytest.approx(100.25)
