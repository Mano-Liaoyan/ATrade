"""Generated code that sizes an order from the equity places orders in a real LiveNode (docs/architecture/strategy.md
section 9.8.2). The account of a forward test is on the venue ATRADE, not on the venue of an instrument."""

from pathlib import Path
from typing import Any

import httpx
import pytest
from nautilus_trader.config import StrategyConfig

from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.strategy import load_strategy_classes
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.strategy_templates import TEMPLATES_BY_ID
from tests.fakes.clock import FixedClock
from tests.forward_test.atrade_clients_node import (
    APPLE,
    APPLE_ID,
    DAY_BAR_TYPE,
    FORWARD_TEST_ID,
    make_world,
    run_node,
    send_today_bar,
    wait_until,
)
from tests.forward_test.test_universe_forward_test_child import (
    TODAY_UTC,
    UniverseChildRun,
    clock,  # noqa: F401  # pyright: ignore[reportUnusedImport] - a pytest fixture
    save_daily_bars,
    start_top_2_forward_test,
)
from tests.strategy.rules_examples import condition, group, make_rules, make_universe_rules, number, price

PERCENT_OF_EQUITY = {"type": "percent_of_equity", "percent": 50}
CLOSE = "100"


def make_universe_strategy(code: str, work_directory: Path) -> Any:
    strategy_class, config_class = load_strategy_classes(code, work_directory)
    return strategy_class(config_class())


@pytest.mark.anyio
async def test_a_single_instrument_buy_sends_the_percent_of_the_equity(database_url: str, tmp_path: Path) -> None:
    entry = group("all_of", condition(price(), "above", number(1)))
    code = make_rules_code(StrategyRules.model_validate(make_rules(entry, position_size=PERCENT_OF_EQUITY)))
    strategy_class, config_class = load_strategy_classes(code, tmp_path)
    # The NautilusTrader fields go to __new__, as in `live_node_run.create_strategy_config`.
    tag = format_forward_test_order_tag(FORWARD_TEST_ID)
    config: StrategyConfig = config_class.__new__(config_class, order_id_tag=tag)  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
    config.__init__(instrument_id=APPLE_ID, bar_type=DAY_BAR_TYPE)  # pyright: ignore[reportCallIssue, reportUnknownMemberType]
    strategy = strategy_class(config)  # pyright: ignore[reportUnknownArgumentType]
    world = make_world(database_url)

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, CLOSE)
        await wait_until(lambda: bool(world.gateway.open_orders))

    # 50% of 10,000 at the close 100.
    assert [(order.instrument, order.side, order.quantity) for order in world.gateway.open_orders] == [
        (APPLE, "BUY", 50)
    ]


@pytest.mark.anyio
async def test_the_m1_template_sends_buys_from_the_account_cash(
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    code = TEMPLATES_BY_ID["m1"].code
    assert code is not None
    strategy = make_universe_strategy(code, tmp_path)
    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.strategy = strategy
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(strategy.members) == 2)
        await save_daily_bars(database_url, APPLE, TODAY_UTC, 1)
        await wait_until(lambda: bool(strategy.cache.orders()))
        sides = {order.side.name for order in strategy.cache.orders()}
    finally:
        await child.stop()

    assert sides == {"BUY"}


@pytest.mark.anyio
async def test_the_buys_of_universe_rules_are_a_share_of_the_account_cash(
    web_client: httpx.AsyncClient,
    database_url: str,
    frontend_build_dir: Path,
    clock: FixedClock,  # noqa: F811
    tmp_path: Path,
) -> None:
    forward_test_id = await start_top_2_forward_test(web_client, database_url)
    strategy = make_universe_strategy(make_rules_code(StrategyRules.model_validate(make_universe_rules())), tmp_path)
    child = UniverseChildRun(database_url, frontend_build_dir, clock)
    child.strategy = strategy
    child.start(forward_test_id)
    try:
        await wait_until(lambda: len(strategy.members) == 2)
        # The rules rebalance only on a second new bar time. The data client does not send a bar of a future day.
        name = next(iter(strategy.members))
        strategy.last_close[name] = float(CLOSE)
        strategy.buys = [name]
        strategy.send_buys()
        quantities = [int(order.quantity) for order in strategy.cache.orders()]
    finally:
        await child.stop()

    # 95% of 10,000 / 2 members at the close 100, rounded down.
    assert quantities == [47]
