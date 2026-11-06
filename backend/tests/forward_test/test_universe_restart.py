"""A multi-instrument strategy after a forward test restart in a new quarter that drops a held instrument
(docs/architecture/strategy.md sections 9.8.6 and 9.9.3). A real LiveNode, the IBKR fake, and the owner ledger fake.

The strategy held MSFT. The new quarter has NVDA and AAPL. So the restart restores a position outside the universe.
"""

import asyncio
from decimal import Decimal
from pathlib import Path
from typing import Any, override

import httpx
import pytest

from atrade.forward_test import (
    ForwardTestPosition,
    GatewayWatch,
    LiveNodeEnd,
    LiveNodeInput,
    UniverseRunOptions,
    create_universe_clients,
    run_universe_node,
)
from atrade.forward_test.universe_live_node import create_universe_strategy_config
from atrade.foundation.instrument import Instrument
from atrade.strategy import load_strategy_classes
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.strategy_templates import TEMPLATES_BY_ID
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection
from tests.fakes.owner_ledger import FakeOwnerLedger
from tests.forward_test.test_forward_test_child import ACCOUNT_ID
from tests.forward_test.test_universe_forward_test_child import (
    MICROSOFT,
    NEXT_QUARTER_UTC,
    NVIDIA,
    POLL_SECONDS,
    TODAY_UTC,
    UniverseChildRun,
    clock,  # noqa: F401  # pyright: ignore[reportUnusedImport] - a pytest fixture
    save_daily_bars,
    save_us_universe,
    start_top_2_forward_test,
    wait_until,
)
from tests.forward_test.test_universe_forward_test_detail import APPLE
from tests.strategy.rules_examples import indicator, make_universe_rules

MSFT_ID = "MSFT.NASDAQ"
HELD_SHARES = 10
WAIT_FOR_DENIAL_SECONDS = POLL_SECONDS * 10


class RestartChildRun(UniverseChildRun):
    """The child with the code of the saved version, and the ledger and the IBKR fake of the node for the asserts."""

    def __init__(self, database_url: str, frontend_build_dir: Path, clock: FixedClock, work_directory: Path) -> None:  # noqa: F811
        super().__init__(database_url, frontend_build_dir, clock)
        self.work_directory = work_directory
        self.ledger = FakeOwnerLedger(cash_usd=Decimal(10000))
        self.node_gateway: FakeGatewayConnection | None = None
        self.strategy_of_version: Any = None

    @override
    async def run_node(self, live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
        strategy_class, config_class = load_strategy_classes(live_node_input.strategy_code, self.work_directory)
        self.strategy_of_version = strategy_class(create_universe_strategy_config(config_class, live_node_input))
        self.node_gateway = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID], client_id=live_node_input.client_id)
        clients = create_universe_clients(live_node_input, self.ledger, self.node_gateway)
        options = UniverseRunOptions(
            clock=self.clock, gateway_watch=GatewayWatch(lost_after_seconds=3600.0), poll_seconds=POLL_SECONDS
        )
        return await run_universe_node(live_node_input, self.strategy_of_version, clients, stop_requested, options)

    def read_orders(self) -> list[tuple[str | None, str, Decimal]]:
        assert self.node_gateway is not None
        return [(order.instrument.symbol, order.side, order.quantity) for order in self.node_gateway.open_orders]

    def has_order(self, instrument: Instrument, side: str) -> bool:
        return (instrument.symbol, side, Decimal(HELD_SHARES)) in self.read_orders()


async def start_restart(  # noqa: PLR0913 - the fixtures of the run
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
    *,
    code: str,
) -> RestartChildRun:
    forward_test_id = await start_top_2_forward_test(web_client, database_url, {"code": code})
    save_us_universe(database_url, NEXT_QUARTER_UTC, [NVIDIA, APPLE])
    clock.now_utc = NEXT_QUARTER_UTC.replace(hour=12)
    child = RestartChildRun(database_url, frontend_build_dir, clock, tmp_path)
    child.ledger.positions[(forward_test_id, MICROSOFT)] = ForwardTestPosition(
        MICROSOFT, Decimal(HELD_SHARES), Decimal(100)
    )
    child.start(forward_test_id)
    await wait_until(lambda: child.strategy_of_version is not None)
    return child


def make_m1_code() -> str:
    code = TEMPLATES_BY_ID["m1"].code
    assert code is not None
    return code


def make_rank_code() -> str:
    rules = make_universe_rules(rank_indicator=indicator("sma", period=3), hold_count=1)
    return make_rules_code(StrategyRules.model_validate(rules))


@pytest.mark.anyio
async def test_the_m1_template_sells_a_restored_position_outside_the_universe(
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
) -> None:
    child = await start_restart(web_client, database_url, frontend_build_dir, clock, tmp_path, code=make_m1_code())
    strategy = child.strategy_of_version
    try:
        await wait_until(lambda: len(strategy.members) == 2 and all(strategy.closes.values()))
        await save_daily_bars(database_url, APPLE, TODAY_UTC, 1)
        await wait_until(lambda: child.has_order(MICROSOFT, "SELL"))
    finally:
        await child.stop()

    assert strategy.closes[MSFT_ID]


@pytest.mark.anyio
async def test_the_m1_template_rebalances_on_the_next_day_after_a_denied_sell(
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
) -> None:
    child = await start_restart(web_client, database_url, frontend_build_dir, clock, tmp_path, code=make_m1_code())
    strategy = child.strategy_of_version
    child.ledger.split_check_needed.add(MICROSOFT)
    try:
        await wait_until(lambda: len(strategy.members) == 2 and all(strategy.closes.values()))
        await save_daily_bars(database_url, APPLE, TODAY_UTC, 1)
        await wait_until(lambda: strategy.open_sell_count == 1 and strategy.last_rebalance_month is not None)
        await asyncio.sleep(WAIT_FOR_DENIAL_SECONDS)
        assert child.read_orders() == []
        # A bar of the next day: the fixed day of the NautilusTrader clock cannot change here.
        child.ledger.split_check_needed.clear()
        strategy.last_day = None
        await save_daily_bars(database_url, NVIDIA, TODAY_UTC, 1)
        await wait_until(lambda: child.has_order(MICROSOFT, "SELL"))
    finally:
        await child.stop()


@pytest.mark.anyio
async def test_a_rule_builder_rebalance_sells_a_restored_position_outside_the_universe(
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
) -> None:
    child = await start_restart(web_client, database_url, frontend_build_dir, clock, tmp_path, code=make_rank_code())
    strategy = child.strategy_of_version
    try:
        await wait_until(lambda: len(strategy.members) == 2)
        await asyncio.sleep(WAIT_FOR_DENIAL_SECONDS)
        await save_daily_bars(database_url, NVIDIA, TODAY_UTC, 1)
        await wait_until(lambda: strategy.values)
        # The rebalance needs a second bar time. The data client does not send a bar of a future day.
        strategy.rebalance()
        await wait_until(lambda: child.has_order(MICROSOFT, "SELL"))
        targets = set(strategy.targets)
    finally:
        await child.stop()

    assert MSFT_ID not in targets
