"""The child of a multi-instrument forward test with a real LiveNode (docs/architecture/forward_test.md section 12.17).

The child body runs with the IBKR fake. The LiveNode has the ATrade data client on the bar store and the ATrade
execution client with the owner ledger fake. The ATrade clock is fixed: it decides the quarter. The NautilusTrader
clock is the real time: the bars are saved relative to today.
"""

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import psycopg
import pytest
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, CustomData, DataType
from nautilus_trader.trading import Strategy

from atrade.backtest import UNIVERSE_UPDATE
from atrade.forward_test import (
    GatewayWatch,
    IbkrAccess,
    LiveNodeEnd,
    LiveNodeInput,
    OwnerFill,
    UniverseRunOptions,
    create_universe_clients,
    run_forward_test_child,
    run_universe_node,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, save_received_bars
from atrade.paper_trading import ForwardTestLedger
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection
from tests.fakes.owner_ledger import FakeOwnerLedger
from tests.forward_test.test_forward_test_child import ACCOUNT_ID, make_forward_test_gateway, make_settings
from tests.forward_test.test_forward_test_routes import (
    FORWARD_TESTS_PATH,
    make_universe_request,
    save_test_strategy_version,
)
from tests.forward_test.test_universe_forward_test_detail import APPLE

MICROSOFT = Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD")
NVIDIA = Instrument(symbol="NVDA", exchange="NASDAQ", currency="USD")
DAILY = BarPeriod.ONE_DAY
WARM_UP = timedelta(days=365)
SAVED_DAY_COUNT = 400
WAIT_SECONDS = 30.0
POLL_SECONDS = 0.05
TODAY_UTC = floor_to_bar_start(datetime.now(UTC), DAILY)


def find_quarter_start(time_utc: datetime) -> datetime:
    return datetime(time_utc.year, 3 * ((time_utc.month - 1) // 3) + 1, 1, tzinfo=UTC)


THIS_QUARTER_UTC = find_quarter_start(TODAY_UTC)
NEXT_QUARTER_UTC = find_quarter_start(THIS_QUARTER_UTC + timedelta(days=95))


def bar_type_name(instrument: Instrument) -> str:
    return f"{instrument.symbol}.{instrument.exchange}-1-DAY-LAST-EXTERNAL"


@pytest.fixture
def clock() -> FixedClock:
    """The Web app and the child start the forward test now, in the current quarter."""
    return FixedClock(datetime.now(UTC))


class FollowMembersConfig(StrategyConfig):
    pass


class FollowMembersStrategy(Strategy):
    """Like the multi-instrument templates: subscribes to each new member and asks for 1 year of its bars."""

    def __init__(self, config: FollowMembersConfig) -> None:
        super().__init__(config)
        self.lists: list[tuple[str, ...]] = []
        self.historical_bars: dict[str, list[NautilusBar]] = {}
        self.bars: list[NautilusBar] = []

    def on_start(self) -> None:
        self.subscribe_data(DataType(UNIVERSE_UPDATE))  # pyright: ignore[reportUnknownMemberType]

    def on_data(self, data: object) -> None:
        assert isinstance(data, CustomData)
        bar_types = tuple(str(data.data.bar_types).split(","))  # pyright: ignore[reportAttributeAccessIssue]
        for name in bar_types:
            if not any(name in earlier for earlier in self.lists):
                bar_type = BarType.from_str(name)
                self.request_bars(bar_type, start=self.clock.utc_now() - WARM_UP)  # pyright: ignore[reportUnknownMemberType]
                self.subscribe_bars(bar_type)  # pyright: ignore[reportUnknownMemberType]
        self.lists.append(bar_types)

    def on_historical_bars(self, bars: Sequence[NautilusBar]) -> None:
        for bar in bars:
            self.historical_bars.setdefault(str(bar.bar_type), []).append(bar)

    def on_bar(self, bar: NautilusBar) -> None:
        self.bars.append(bar)


async def save_daily_bars(database_url: str, instrument: Instrument, first_day_utc: datetime, day_count: int) -> None:
    bars = [
        Bar(
            start_utc=first_day_utc + timedelta(days=index),
            open=Decimal(100),
            high=Decimal(120),
            low=Decimal(100),
            close=Decimal(120),
            volume=Decimal(1000),
        )
        for index in range(day_count)
    ]
    time_range = TimeRange(first_day_utc, first_day_utc + timedelta(days=day_count))
    await save_received_bars(
        database_url=database_url, bar_request=BarRequest(instrument, DAILY, time_range), bars=bars
    )


def save_us_universe(database_url: str, quarter_start_utc: datetime, instruments: list[Instrument]) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        for rank, instrument in enumerate(instruments, start=1):
            connection.execute(
                """
                INSERT INTO us_universe_member (
                    quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
                )
                VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, %(exchange)s, 'USD', 1000000, %(quarter_start_utc)s)
                """,
                {
                    "quarter_start_utc": quarter_start_utc,
                    "rank": rank,
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                },
            )


def read_recorded_quarters(database_url: str, forward_test_id: int) -> dict[datetime, list[str]]:
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT quarter_start_utc, symbol FROM forward_test_universe_member
            WHERE forward_test_id = %(id)s ORDER BY quarter_start_utc, symbol
            """,
            {"id": forward_test_id},
        ).fetchall()
    quarters: dict[datetime, list[str]] = {}
    for quarter_start_utc, symbol in rows:
        quarters.setdefault(quarter_start_utc, []).append(symbol)
    return quarters


async def start_top_2_forward_test(web_client: httpx.AsyncClient, database_url: str) -> int:
    save_us_universe(database_url, THIS_QUARTER_UTC, [APPLE, MICROSOFT, NVIDIA])
    for instrument in (APPLE, MICROSOFT, NVIDIA):
        await save_daily_bars(database_url, instrument, TODAY_UTC - timedelta(days=SAVED_DAY_COUNT), SAVED_DAY_COUNT)
    strategy_version_id = await save_test_strategy_version(web_client)
    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "rule", "top_n": 2})
    )
    assert response.status_code == 201
    return response.json()["id"]


async def wait_until(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while not condition():
            await asyncio.sleep(POLL_SECONDS)


class UniverseChildRun:
    """One start of the child: the child body with the IBKR fake, then the real LiveNode with the test strategy."""

    def __init__(self, database_url: str, frontend_build_dir: Path, clock: FixedClock) -> None:
        self.database_url = database_url
        self.frontend_build_dir = frontend_build_dir
        self.clock = clock
        self.gateway = make_forward_test_gateway()
        self.strategy = FollowMembersStrategy(FollowMembersConfig())
        self.inputs: list[LiveNodeInput] = []
        self.stop_requested = asyncio.Event()
        self.task: asyncio.Task[int] | None = None

    async def run_node(self, live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
        self.inputs.append(live_node_input)
        clients = create_universe_clients(
            live_node_input,
            FakeOwnerLedger(cash_usd=Decimal(10000)),
            FakeGatewayConnection(managed_accounts=[ACCOUNT_ID], client_id=live_node_input.client_id),
        )
        options = UniverseRunOptions(
            clock=self.clock, gateway_watch=GatewayWatch(lost_after_seconds=3600.0), poll_seconds=POLL_SECONDS
        )
        return await run_universe_node(live_node_input, self.strategy, clients, stop_requested, options)

    def start(self, forward_test_id: int) -> None:
        self.task = asyncio.create_task(
            run_forward_test_child(
                settings=make_settings(self.database_url, self.frontend_build_dir),
                forward_test_id=forward_test_id,
                mode="run",
                ibkr_access=IbkrAccess(
                    open_gateway_connection=lambda _client_id: self.gateway,
                    run_live_node=self.run_node,
                    clock=self.clock,
                ),
                stop_requested=self.stop_requested,
            )
        )

    async def stop(self) -> int:
        assert self.task is not None
        self.stop_requested.set()
        return await asyncio.wait_for(self.task, WAIT_SECONDS)


@pytest.mark.anyio
async def test_the_live_node_gives_the_strategy_1_year_of_warm_up_and_new_daily_bars_from_the_bar_store(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path, clock: FixedClock
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(child.strategy.historical_bars) == 2)
        await save_daily_bars(database_url, APPLE, TODAY_UTC, 1)
        await wait_until(lambda: bool(child.strategy.bars))
    finally:
        exit_code = await child.stop()

    assert exit_code == 0
    [live_node_input] = child.inputs
    assert live_node_input.instrument is None
    assert live_node_input.warm_up_bars == ()
    # The instrument IDs are SYMBOL.<primary exchange> (section 12.17).
    assert child.strategy.lists == [(bar_type_name(APPLE), bar_type_name(MICROSOFT))]
    apple_warm_up = child.strategy.historical_bars[bar_type_name(APPLE)]
    first_warm_up_start = datetime.fromtimestamp(apple_warm_up[0].ts_event / 10**9, UTC) - DAILY.length
    assert TODAY_UTC - WARM_UP <= first_warm_up_start <= TODAY_UTC - WARM_UP + timedelta(days=1)
    assert len(apple_warm_up) >= 364
    assert [str(bar.bar_type) for bar in child.strategy.bars] == [bar_type_name(APPLE)]
    # No bar request to IBKR: not in the child and not in the LiveNode.
    assert child.gateway.historical_bar_requests == []


@pytest.mark.anyio
async def test_at_a_quarter_start_the_strategy_gets_the_new_members_and_their_bars(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path, clock: FixedClock
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(child.strategy.historical_bars) == 2)
        save_us_universe(database_url, NEXT_QUARTER_UTC, [NVIDIA, APPLE])
        clock.now_utc = NEXT_QUARTER_UTC + timedelta(hours=12)
        await wait_until(lambda: len(child.strategy.lists) == 2 and len(child.strategy.historical_bars) == 3)
    finally:
        await child.stop()

    assert child.strategy.lists[1] == (bar_type_name(NVIDIA), bar_type_name(APPLE))
    assert len(child.strategy.historical_bars[bar_type_name(NVIDIA)]) >= 364
    assert read_recorded_quarters(database_url, forward_test_id) == {
        THIS_QUARTER_UTC: ["AAPL", "MSFT"],
        NEXT_QUARTER_UTC: ["AAPL", "NVDA"],
    }


@pytest.mark.anyio
async def test_after_a_quarter_change_in_an_interruption_the_restarted_strategy_gets_the_current_members(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path, clock: FixedClock
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    # The child is not running when the quarter changes.
    save_us_universe(database_url, NEXT_QUARTER_UTC, [NVIDIA, APPLE])
    clock.now_utc = NEXT_QUARTER_UTC + timedelta(hours=12)

    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(child.strategy.historical_bars) == 2)
    finally:
        await child.stop()

    assert child.strategy.lists == [(bar_type_name(NVIDIA), bar_type_name(APPLE))]
    assert sorted(read_recorded_quarters(database_url, forward_test_id)) == [THIS_QUARTER_UTC, NEXT_QUARTER_UTC]


@pytest.mark.anyio
async def test_the_equity_is_the_capital_plus_the_fill_cash_plus_the_positions_at_the_daily_close(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path, clock: FixedClock
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    ledger = ForwardTestLedger(
        database_url=database_url,
        account=ACCOUNT_ID,
        forward_test_id=forward_test_id,
        gateway_connection=FakeGatewayConnection(managed_accounts=[ACCOUNT_ID]),
        clock=clock,
    )
    await ledger.save_fill(
        OwnerFill(
            forward_test_id=forward_test_id,
            instrument=APPLE,
            side="BUY",
            quantity=Decimal(10),
            price=Decimal(100),
            time_utc=clock.now_utc,
            order_ref=f"O-FT{forward_test_id}-1",
            execution_id="0000e0d5.1",
            ibkr_order_id=1,
            commission=Decimal(1),
        )
    )
    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(child.strategy.historical_bars) == 2)
        await save_daily_bars(database_url, APPLE, TODAY_UTC, 1)
        await wait_until(lambda: bool(child.strategy.bars))
        detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test_id}")).json()
        for _ in range(100):
            if detail["equity_curve"]:
                break
            await asyncio.sleep(POLL_SECONDS)
            detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test_id}")).json()
    finally:
        await child.stop()

    # 10,000 allocated - 10 × 100 - 1 commission + 10 × 120 at the daily close.
    assert detail["equity_curve"] == [
        {"time_utc": (TODAY_UTC + DAILY.length).isoformat().replace("+00:00", "Z"), "equity_usd": "10199"}
    ]
