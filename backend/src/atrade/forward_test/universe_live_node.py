"""The LiveNode of a multi-instrument forward test (docs/architecture/forward_test.md section 12.17): the ATrade data
client gives the strategy the daily bars of the bar store, and the ATrade execution client checks each order against
the owner ledger (section 12.19). The node sends no bar request to IBKR.

The universe poller of the child reads the bar store and the quarter every UNIVERSE_POLL_SECONDS: it sends the new
daily bars that the bar fetcher saved, records the equity, and at a new quarter sends the new members as
`UniverseUpdate` (section 12.24).
"""

import asyncio
import contextlib
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from nautilus_trader.common import Environment
from nautilus_trader.config import StrategyConfig
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode, LiveNodeBuilder, LiveNodeConfig
from nautilus_trader.model import TraderId
from nautilus_trader.trading import Strategy

from atrade.backtest import EquityPoint, calculate_universe_equity_curve
from atrade.forward_test import forward_test_records
from atrade.forward_test.atrade_instruments import create_instrument_id
from atrade.forward_test.atrade_live_node import add_atrade_clients
from atrade.forward_test.bar_store_data_client import BarStoreDataClientFactory, BarStoreInput
from atrade.forward_test.forward_test_child import LiveNodeEnd, LiveNodeInput
from atrade.forward_test.forward_test_universe import UniverseNodeInput, UniverseQuarter, update_current_quarter
from atrade.forward_test.live_node_run import (
    TRADER_ID_PREFIX,
    GatewayWatch,
    run_live_node,
    wait_for_end_or_stop,
)
from atrade.forward_test.owner_ledger import OwnerLedger
from atrade.forward_test.owner_ledger_execution_client import (
    OrderGateway,
    OwnerLedgerExecutionClientFactory,
    OwnerLedgerInput,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import IbAsyncGatewayConnection
from atrade.market_data import BarRequest, read_saved_bars, read_source_order, read_unsaved_ranges
from atrade.paper_trading import ForwardTestLedger, read_forward_test_fills
from atrade.strategy import load_strategy_classes

DAILY = BarPeriod.ONE_DAY
# The bar fetcher saves the daily bars after 00:30 UTC (section 12.24). One minute later the strategy gets them.
UNIVERSE_POLL_SECONDS = 60.0
# The 1-year warm-up of a new member (section 12.17).
WARM_UP_LENGTH = timedelta(days=365)
# At a new quarter, the update waits at most this long for the warm-up of the new members.
NEW_MEMBER_WARM_UP_WAIT = timedelta(minutes=30)

logger = logging.getLogger("atrade.universe_live_node")


@dataclass(frozen=True)
class UniverseClients:
    data_factory: BarStoreDataClientFactory
    execution_factory: OwnerLedgerExecutionClientFactory


def find_bar_type_names(members: tuple[Instrument, ...]) -> tuple[str, ...]:
    """`SYMBOL.<primary exchange>-1-DAY-LAST-EXTERNAL`: the strategy uses only these instrument IDs (ADR 0003)."""
    return tuple(f"{create_instrument_id(member)}-{DAILY.value}-LAST-EXTERNAL" for member in members)


def read_universe(live_node_input: LiveNodeInput) -> UniverseNodeInput:
    if live_node_input.universe is None:
        message = f"Forward test {live_node_input.forward_test_id} has no universe."
        raise ValueError(message)
    return live_node_input.universe


def find_node_instruments(universe: UniverseNodeInput) -> tuple[Instrument, ...]:
    return tuple(dict.fromkeys(universe.known_instruments + universe.quarter.members))


def create_universe_clients(
    live_node_input: LiveNodeInput, ledger: OwnerLedger, gateway: OrderGateway
) -> UniverseClients:
    """The ATrade data client on the bar store, and the ATrade execution client with the owner ledger and the
    connection with the client ID of the forward test (section 12.19)."""
    universe = read_universe(live_node_input)
    return UniverseClients(
        data_factory=BarStoreDataClientFactory(
            BarStoreInput(
                database_url=live_node_input.database_url,
                instruments=find_node_instruments(universe),
            )
        ),
        execution_factory=OwnerLedgerExecutionClientFactory(
            OwnerLedgerInput(
                forward_test_id=live_node_input.forward_test_id,
                client_id=live_node_input.client_id,
                account_id=live_node_input.account_id,
                instruments=find_node_instruments(universe),
            ),
            ledger,
            gateway,
        ),
    )


def create_production_clients(live_node_input: LiveNodeInput) -> UniverseClients:
    """The owner ledger in PostgreSQL and one ib_async connection with the client ID of the forward test."""
    gateway_connection = IbAsyncGatewayConnection(
        host=live_node_input.gateway_host, port=live_node_input.gateway_port, client_id=live_node_input.client_id
    )
    ledger = ForwardTestLedger(
        database_url=live_node_input.database_url,
        account=live_node_input.account_id,
        forward_test_id=live_node_input.forward_test_id,
        gateway_connection=gateway_connection,
        clock=SystemClock(),
    )
    return create_universe_clients(live_node_input, ledger, gateway_connection)


def build_universe_node(live_node_input: LiveNodeInput, clients: UniverseClients) -> LiveNode:
    """No catalog: the data client answers each `request_bars` from the bar store (section 12.19)."""
    instrument_ids = [
        str(create_instrument_id(instrument)) for instrument in find_node_instruments(read_universe(live_node_input))
    ]
    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId(f"{TRADER_ID_PREFIX}-{live_node_input.forward_test_id:03d}"),
        exec_engine=LiveExecutionEngineConfig(reconciliation=True, reconciliation_instrument_ids=instrument_ids),
    )
    # The stub types the unused factory dicts without key and value types.
    builder: LiveNodeBuilder = LiveNodeBuilder.from_config(f"forward-test-{live_node_input.forward_test_id}", config)  # pyright: ignore[reportUnknownMemberType]
    return add_atrade_clients(builder, clients.data_factory, clients.execution_factory).build()


def create_universe_strategy_config(
    config_class: type[StrategyConfig], live_node_input: LiveNodeInput
) -> StrategyConfig:
    """A multi-instrument configuration has no `instrument_id` and no `bar_type` (backtest.md section 10.10.8). The
    strategy owns the restored positions of all known members (section 12.7). A multi-instrument `__init__` passes
    the other keywords to `StrategyConfig.__init__` (strategy.md section 9.2), as in the multi-instrument backtest."""
    instrument_ids = [
        create_instrument_id(instrument) for instrument in find_node_instruments(read_universe(live_node_input))
    ]
    return config_class(order_id_tag=live_node_input.order_id_tag, external_order_instrument_ids=instrument_ids)  # pyright: ignore[reportCallIssue]


async def read_daily_bars(database_url: str, instrument: Instrument, time_range: TimeRange) -> list[Bar]:
    source_order = await read_source_order(database_url=database_url)
    saved_bars = await read_saved_bars(
        database_url=database_url, bar_request=BarRequest(instrument, DAILY, time_range), source_order=source_order
    )
    return saved_bars.bars


async def record_universe_equity(
    live_node_input: LiveNodeInput, members: tuple[Instrument, ...], now_utc: datetime
) -> list[EquityPoint]:
    """Equity = the allocated capital + the cash of the fills + each position at the daily close of the bar store,
    in USD (section 12.8). One point at each daily bar end after the start. A saved point stays."""
    universe = read_universe(live_node_input)
    database_url = live_node_input.database_url
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        fills = [
            forward_test_records.convert_ledger_fill(fill)
            for fill in await read_forward_test_fills(connection, live_node_input.forward_test_id)
        ]
        instruments = dict.fromkeys([*members, *(fill.instrument for fill in fills)])
        time_range = TimeRange(floor_to_bar_start(universe.row.created_at_utc, DAILY), now_utc)
        bars_by_instrument: dict[tuple[str | None, str | None], list[Bar]] = {
            (instrument.symbol, instrument.exchange): await read_daily_bars(database_url, instrument, time_range)
            for instrument in instruments
        }
        equity_curve = [
            point
            for point in calculate_universe_equity_curve(
                start_cash=live_node_input.start_balance_usd,
                bars_by_instrument=bars_by_instrument,
                bar_period=DAILY,
                trades=[fill.trade for fill in fills],
            )
            if universe.row.created_at_utc < point.time_utc
        ]
        await forward_test_records.save_equity_points(
            connection, forward_test_id=live_node_input.forward_test_id, equity_points=equity_curve
        )
    return equity_curve


@dataclass
class UniversePoller:
    """Keeps the strategy of a running multi-instrument LiveNode up to date (section 12.24)."""

    live_node_input: LiveNodeInput
    clients: UniverseClients
    strategy: Strategy
    clock: Clock
    quarter: UniverseQuarter = field(init=False)
    is_first_update_sent: bool = field(init=False, default=False)
    # The new members of a new quarter whose update waits for their warm-up in the bar store, and the start of the
    # wait.
    waiting_members: tuple[Instrument, ...] = field(init=False, default=())
    wait_start_utc: datetime | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.quarter = read_universe(self.live_node_input).quarter

    async def is_warm_up_saved(self, now_utc: datetime) -> bool:
        """True when a bar source saved the 1-year warm-up of each waiting member (the bar fetcher fills it a few
        seconds after the new quarter is recorded), or after NEW_MEMBER_WARM_UP_WAIT."""
        assert self.wait_start_utc is not None
        if now_utc - self.wait_start_utc >= NEW_MEMBER_WARM_UP_WAIT:
            logger.warning(
                "Forward test %s: the warm-up of the new members is not complete. The strategy gets them now.",
                self.live_node_input.forward_test_id,
            )
            return True
        end_utc = floor_to_bar_start(now_utc, DAILY)
        warm_up_range = TimeRange(end_utc - WARM_UP_LENGTH, end_utc)
        for instrument in self.waiting_members:
            bar_request = BarRequest(instrument, DAILY, warm_up_range)
            if await read_unsaved_ranges(database_url=self.live_node_input.database_url, bar_request=bar_request):
                return False
        return True

    async def poll(self) -> None:
        """One check: a new quarter first, then the new daily bars, then the equity."""
        data_client = self.clients.data_factory.client
        if data_client is None or not data_client.is_connected:
            return
        now_utc = self.clock.read_now_utc()
        quarter = await update_current_quarter(
            database_url=self.live_node_input.database_url, row=read_universe(self.live_node_input).row, now_utc=now_utc
        )
        if quarter.quarter_start_utc != self.quarter.quarter_start_utc:
            new_members = tuple(instrument for instrument in quarter.members if instrument not in self.quarter.members)
            self.quarter = quarter
            data_client.add_instruments(quarter.members)
            if self.clients.execution_factory.client is not None:
                self.clients.execution_factory.client.add_instruments(quarter.members)
            if self.is_first_update_sent:
                # The update waits until the bar fetcher saved the warm-up of the new members (section 12.17).
                self.waiting_members = new_members
                self.wait_start_utc = now_utc
        if self.wait_start_utc is not None and await self.is_warm_up_saved(now_utc):
            data_client.send_universe_update(find_bar_type_names(self.quarter.members))
            self.waiting_members = ()
            self.wait_start_utc = None
        if not self.is_first_update_sent and self.strategy.is_running():
            # The strategy subscribed in `on_start`. A restart gives it the members of the current quarter.
            data_client.send_universe_update(find_bar_type_names(self.quarter.members))
            self.is_first_update_sent = True
        if await data_client.send_new_bars():
            await record_universe_equity(self.live_node_input, self.quarter.members, now_utc)

    async def keep_polling(self, poll_seconds: float) -> None:
        """Runs until the caller cancels it. A failed check is logged. The next check tries again."""
        while True:
            try:
                await self.poll()
            except Exception:
                # Any failed check is logged: the poll must keep running for the next bars and quarters.
                logger.exception("Forward test %s: the universe check failed.", self.live_node_input.forward_test_id)
            await asyncio.sleep(poll_seconds)


@dataclass(frozen=True)
class UniverseRunOptions:
    clock: Clock = field(default_factory=SystemClock)
    gateway_watch: GatewayWatch = field(default_factory=GatewayWatch)
    poll_seconds: float = UNIVERSE_POLL_SECONDS


async def run_universe_node(
    live_node_input: LiveNodeInput,
    strategy: Strategy,
    clients: UniverseClients,
    stop_requested: asyncio.Event,
    options: UniverseRunOptions,
) -> LiveNodeEnd:
    """Runs the node with the strategy until the stop request, the loss of IB Gateway, or its own end."""
    live_node = build_universe_node(live_node_input, clients)
    live_node.add_strategy(strategy)
    poller = UniversePoller(live_node_input, clients, strategy, options.clock)
    poll_task = asyncio.create_task(poller.keep_polling(options.poll_seconds))
    try:
        return await wait_for_end_or_stop(live_node, live_node_input, stop_requested, options.gateway_watch)
    finally:
        poll_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poll_task
        live_node.dispose()


async def run_universe_live_node(
    live_node_input: LiveNodeInput, stop_requested: asyncio.Event, options: UniverseRunOptions | None = None
) -> LiveNodeEnd:
    with tempfile.TemporaryDirectory(prefix=f"atrade-forward-test-{live_node_input.forward_test_id}-") as directory:
        strategy_class, config_class = load_strategy_classes(live_node_input.strategy_code, Path(directory))
        strategy = strategy_class(create_universe_strategy_config(config_class, live_node_input))
        return await run_universe_node(
            live_node_input,
            strategy,
            create_production_clients(live_node_input),
            stop_requested,
            options or UniverseRunOptions(),
        )


async def run_forward_test_live_node(live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
    """The LiveNode of the child process: the universe node for a multi-instrument forward test, else the
    single-instrument node with the IB data client (section 12.15)."""
    if live_node_input.universe is not None:
        return await run_universe_live_node(live_node_input, stop_requested)
    return await run_live_node(live_node_input, stop_requested)
