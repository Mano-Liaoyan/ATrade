"""The code templates restore their position state at a forward test restart (docs/architecture/strategy.md section
9.2). A restart gives the strategy its position from the owner ledger, and new objects."""

import asyncio
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import Price

from atrade.forward_test import OwnerFill
from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.strategy import STRATEGY_TEMPLATE, load_strategy_classes
from atrade.strategy.strategy_templates import TEMPLATES_BY_ID
from tests.fakes.ibkr import LIVE_BAR_NOW_UTC, make_execution
from tests.forward_test.atrade_clients_node import (
    ACCOUNT_ID,
    APPLE,
    APPLE_ID,
    CLIENT_ID,
    DAY_BAR_TYPE,
    FORWARD_TEST_ID,
    ClientsWorld,
    make_day_bar,
    make_world,
    run_node,
    save_day_bars,
    send_today_bar,
    today_start_utc,
    wait_until,
)

RESTORED_SHARES = 40
REFUSAL_WAIT_SECONDS = 0.2


async def make_world_with_position(database_url: str) -> ClientsWorld:
    world = make_world(database_url)
    await world.ledger.save_fill(
        OwnerFill(
            FORWARD_TEST_ID,
            APPLE,
            "BUY",
            Decimal(RESTORED_SHARES),
            Decimal(100),
            LIVE_BAR_NOW_UTC,
            "FT7",
            "0001",
            1,
            Decimal(0),
        )
    )
    return world


def create_config(config_class: Any, **fields: Any) -> StrategyConfig:
    """The NautilusTrader fields go to __new__, as in `live_node_run.create_strategy_config`."""
    config = config_class.__new__(
        config_class,
        order_id_tag=format_forward_test_order_tag(FORWARD_TEST_ID),
        external_order_instrument_ids=[APPLE_ID],
    )
    config.__init__(**fields)
    return config


def make_template_strategy(tmp_path: Path) -> Any:
    strategy_class, config_class = load_strategy_classes(STRATEGY_TEMPLATE, tmp_path)
    return strategy_class(create_config(config_class, instrument_id=APPLE_ID, bar_type=DAY_BAR_TYPE))


async def save_warm_up_bars(database_url: str) -> None:
    first_bar_utc = today_start_utc() - timedelta(days=30)
    await save_day_bars(database_url, [make_day_bar(first_bar_utc + timedelta(days=day), "100") for day in range(30)])


def read_orders(world: ClientsWorld) -> list[tuple[str, Decimal]]:
    return [(order.side, order.quantity) for order in world.gateway.open_orders]


async def wait_for_refusal(world: ClientsWorld) -> None:
    await wait_until(lambda: bool(world.ledger.checked_orders))
    await asyncio.sleep(REFUSAL_WAIT_SECONDS)


def replace_close(bar: NautilusBar, close: float) -> NautilusBar:
    price = Price(close, bar.close.precision)
    return NautilusBar(bar.bar_type, price, price, price, price, bar.volume, bar.ts_event, bar.ts_init)


def repeat_last_bar(strategy: Any) -> None:
    """The next bar with the same close. The data client sends 1 bar for each day."""
    strategy.on_bar(strategy.cache.bar(DAY_BAR_TYPE))


@pytest.mark.anyio
async def test_the_default_template_sells_again_on_the_next_bar_after_a_denied_sell(
    database_url: str, tmp_path: Path
) -> None:
    world = await make_world_with_position(database_url)
    await save_warm_up_bars(database_url)
    strategy = make_template_strategy(tmp_path)
    world.ledger.split_check_needed.add(APPLE)

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "50")
        await wait_for_refusal(world)
        assert read_orders(world) == []
        world.ledger.split_check_needed.clear()
        repeat_last_bar(strategy)
        await wait_until(lambda: bool(world.gateway.open_orders))

        assert read_orders(world) == [("SELL", Decimal(RESTORED_SHARES))]


@pytest.mark.anyio
async def test_the_default_template_does_not_buy_more_after_a_denied_sell(database_url: str, tmp_path: Path) -> None:
    world = await make_world_with_position(database_url)
    await save_warm_up_bars(database_url)
    strategy = make_template_strategy(tmp_path)
    world.ledger.split_check_needed.add(APPLE)

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "50")
        await wait_for_refusal(world)
        world.ledger.split_check_needed.clear()
        strategy.on_bar(replace_close(strategy.cache.bar(DAY_BAR_TYPE), 200))
        await asyncio.sleep(REFUSAL_WAIT_SECONDS)

        assert read_orders(world) == []


@pytest.mark.anyio
async def test_the_default_template_buys_again_on_the_next_bar_after_a_rejected_buy(
    database_url: str, tmp_path: Path
) -> None:
    world = make_world(database_url)
    await save_warm_up_bars(database_url)
    strategy = make_template_strategy(tmp_path)
    world.gateway.order_error_message = "Rejected by IBKR"

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "200")
        await wait_for_refusal(world)
        world.gateway.order_error_message = None
        repeat_last_bar(strategy)
        await wait_until(lambda: bool(world.gateway.open_orders))

        assert read_orders(world) == [("BUY", Decimal(10))]


@pytest.mark.anyio
async def test_the_default_template_exit_cancels_the_open_buy_and_sells_the_filled_part(
    database_url: str, tmp_path: Path
) -> None:
    world = make_world(database_url)
    await save_warm_up_bars(database_url)
    strategy = make_template_strategy(tmp_path)

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "200")
        await wait_until(lambda: bool(world.gateway.open_orders))
        order_id = world.gateway.open_orders[0].order_id
        world.gateway.executions.append(
            make_execution(ACCOUNT_ID, order_id=order_id, quantity="4", price="200", client_id=CLIENT_ID)
        )
        await wait_until(lambda: bool(strategy.cache.positions_open(strategy_id=strategy.strategy_id)))
        strategy.on_bar(replace_close(strategy.cache.bar(DAY_BAR_TYPE), 50))
        await wait_until(lambda: read_orders(world) == [("SELL", Decimal(4))])


@pytest.mark.anyio
async def test_the_default_template_exit_sells_all_restored_shares(database_url: str, tmp_path: Path) -> None:
    """A stock split or a partial fill leaves another quantity than the trade quantity of 10 shares."""
    world = await make_world_with_position(database_url)
    await save_warm_up_bars(database_url)
    strategy = make_template_strategy(tmp_path)

    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "50")
        await wait_until(lambda: bool(world.gateway.open_orders))
        orders = [(order.side, order.quantity) for order in world.gateway.open_orders]

    assert orders == [("SELL", RESTORED_SHARES)]


@pytest.mark.anyio
async def test_the_m1_template_knows_its_restored_shares(database_url: str, tmp_path: Path) -> None:
    world = await make_world_with_position(database_url)
    code = TEMPLATES_BY_ID["m1"].code
    assert code is not None
    strategy_class, config_class = load_strategy_classes(code, tmp_path)

    class SubscribingStrategy(strategy_class):
        """`run_node` waits for a bar subscription. The universe poller is not part of this test."""

        def on_start(self) -> None:
            super().on_start()
            self.subscribe_bars(DAY_BAR_TYPE)  # pyright: ignore[reportUnknownMemberType]

    strategy: Any = SubscribingStrategy(create_config(config_class))

    async with run_node(world, strategy, 1):
        assert strategy.shares == {str(APPLE_ID): RESTORED_SHARES}
