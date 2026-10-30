"""A LiveNode with the ATrade execution and data clients, the fake IBKR connection, and the fake owner ledger.

The tests of test_atrade_clients_live_node.py and test_bar_store_data_client.py use it. One `run` is one start of a
forward test child: new clients and a new NautilusTrader cache, with the same ledger, IBKR fake, and bar store.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from nautilus_trader.common import Environment
from nautilus_trader.config import StrategyConfig
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNodeBuilder, LiveNodeConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, InstrumentId, OrderDenied, OrderSide, Quantity, TraderId
from nautilus_trader.trading import Strategy

from atrade.forward_test import (
    BarStoreDataClientFactory,
    BarStoreInput,
    OwnerLedgerExecutionClientFactory,
    OwnerLedgerInput,
    add_atrade_clients,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.market_data import BarRequest, save_received_bars
from tests.fakes.ibkr import FakeGatewayConnection
from tests.fakes.owner_ledger import FakeOwnerLedger

FORWARD_TEST_ID = 7
CLIENT_ID = 11
ACCOUNT_ID = "DU1234567"
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
APPLE_ID = InstrumentId.from_str("AAPL.NASDAQ")
DAY_BAR_TYPE = BarType.from_str("AAPL.NASDAQ-1-DAY-LAST-EXTERNAL")
BUY_QUANTITY = 10
WAIT_SECONDS = 20.0
POLL_SECONDS = 0.05
STOP_WAIT_SECONDS = 30.0


class BuyOnceConfig(StrategyConfig):
    pass


class BuyOnceStrategy(Strategy):
    """Buys 10 shares at market on a bar when it has no position. Records what it sees, for the asserts."""

    def __init__(self, config: BuyOnceConfig) -> None:
        super().__init__(config)
        self.bars: list[NautilusBar] = []
        self.historical_bars: list[NautilusBar] = []
        self.denied_reasons: list[str] = []
        self.positions_at_start: list[tuple[Decimal, Decimal]] = []
        self.positions_at_stop: list[tuple[Decimal, Decimal]] = []
        self.sell_quantity = 0

    def own_positions(self) -> list[tuple[Decimal, Decimal]]:
        return [
            (position.quantity.as_decimal(), Decimal(str(position.avg_px_open)))
            for position in self.cache.positions_open(instrument_id=APPLE_ID)  # pyright: ignore[reportUnknownMemberType]
            if str(position.strategy_id) == str(self.strategy_id)
        ]

    def on_start(self) -> None:
        self.positions_at_start = self.own_positions()
        self.subscribe_bars(DAY_BAR_TYPE)  # pyright: ignore[reportUnknownMemberType]
        self.request_bars(DAY_BAR_TYPE, start=datetime(2026, 1, 1, tzinfo=UTC))  # pyright: ignore[reportUnknownMemberType]

    def on_stop(self) -> None:
        self.positions_at_stop = self.own_positions()

    def on_historical_bars(self, bars: Sequence[NautilusBar]) -> None:
        self.historical_bars.extend(bars)

    def on_bar(self, bar: NautilusBar) -> None:
        self.bars.append(bar)
        if self.sell_quantity:
            side, quantity = OrderSide.SELL, self.sell_quantity
        elif not self.own_positions():
            side, quantity = OrderSide.BUY, BUY_QUANTITY
        else:
            return
        self.submit_order(self.order_factory.market(APPLE_ID, side, Quantity.from_int(quantity)))  # pyright: ignore[reportUnknownMemberType]

    def on_order_denied(self, event: OrderDenied) -> None:
        self.denied_reasons.append(str(event.reason))


@dataclass
class ClientsWorld:
    database_url: str
    gateway: FakeGatewayConnection
    ledger: FakeOwnerLedger
    data_factories: list[BarStoreDataClientFactory] = field(default_factory=list)


def make_world(database_url: str) -> ClientsWorld:
    gateway = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID], client_id=CLIENT_ID)
    return ClientsWorld(database_url, gateway, FakeOwnerLedger(cash_usd=Decimal(10000)))


def build_node(world: ClientsWorld, run_number: int) -> tuple[LiveNodeBuilder, BarStoreDataClientFactory]:
    """The strategy sets `external_order_instrument_ids` (section 12.7 Phase 3). A test without them shows that the
    restored position then belongs to `EXTERNAL`."""
    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId(f"ATRADE-{FORWARD_TEST_ID:03d}"),
        exec_engine=LiveExecutionEngineConfig(reconciliation=True),
    )
    builder = LiveNodeBuilder.from_config(f"atrade-clients-{run_number}", config)  # pyright: ignore[reportUnknownMemberType]
    builder = builder.with_delay_post_stop_secs(0).with_delay_shutdown_secs(0)
    data_factory = BarStoreDataClientFactory(BarStoreInput(world.database_url, (APPLE,)))
    execution_factory = OwnerLedgerExecutionClientFactory(
        OwnerLedgerInput(
            forward_test_id=FORWARD_TEST_ID,
            client_id=CLIENT_ID,
            account_id=ACCOUNT_ID,
            instruments=(APPLE,),
            fill_check_interval_seconds=POLL_SECONDS,
        ),
        world.ledger,
        world.gateway,
    )
    return add_atrade_clients(builder, data_factory, execution_factory), data_factory


def make_strategy(*, claims_external_orders: bool, sell_quantity: int = 0) -> BuyOnceStrategy:
    external_ids = [APPLE_ID] if claims_external_orders else None
    strategy = BuyOnceStrategy(
        BuyOnceConfig(
            order_id_tag=format_forward_test_order_tag(FORWARD_TEST_ID), external_order_instrument_ids=external_ids
        )  # pyright: ignore[reportCallIssue]
    )
    strategy.sell_quantity = sell_quantity
    return strategy


async def wait_until(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while not condition():
            await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def run_node(
    world: ClientsWorld, strategy: BuyOnceStrategy, run_number: int
) -> AsyncGenerator[BarStoreDataClientFactory]:
    builder, data_factory = build_node(world, run_number)
    live_node = builder.build()
    live_node.add_strategy(strategy)
    run_task = asyncio.create_task(live_node.run_async())
    try:
        await wait_until(lambda: data_factory.client is not None and bool(data_factory.client.next_bar_starts))
        yield data_factory
    finally:
        live_node.handle().stop()
        await asyncio.wait_for(run_task, STOP_WAIT_SECONDS)
        live_node.dispose()


def make_day_bar(start_utc: datetime, close: str) -> Bar:
    price = Decimal(close)
    return Bar(start_utc=start_utc, open=price, high=price, low=price, close=price, volume=Decimal(1000))


async def save_day_bars(database_url: str, bars: list[Bar]) -> None:
    time_range = TimeRange(bars[0].start_utc, bars[-1].start_utc + BarPeriod.ONE_DAY.length)
    await save_received_bars(
        database_url=database_url, bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, time_range), bars=bars
    )


def today_start_utc() -> datetime:
    return floor_to_bar_start(datetime.now(UTC), BarPeriod.ONE_DAY)


async def send_today_bar(world: ClientsWorld, data_factory: BarStoreDataClientFactory, close: str) -> None:
    """Saves the bar of today, like the bar fetcher, and sends it to the strategy (section 12.24)."""
    await save_day_bars(world.database_url, [make_day_bar(today_start_utc(), close)])
    assert data_factory.client is not None
    await data_factory.client.send_new_bars()
