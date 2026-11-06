"""The code templates restore their position state at a forward test restart (docs/architecture/strategy.md section
9.2). A restart gives the strategy its position from the owner ledger, and new objects."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from nautilus_trader.config import StrategyConfig

from atrade.forward_test import OwnerFill
from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.strategy import STRATEGY_TEMPLATE, load_strategy_classes
from atrade.strategy.strategy_templates import TEMPLATES_BY_ID
from tests.fakes.ibkr import LIVE_BAR_NOW_UTC
from tests.forward_test.atrade_clients_node import (
    APPLE,
    APPLE_ID,
    DAY_BAR_TYPE,
    FORWARD_TEST_ID,
    ClientsWorld,
    make_world,
    run_node,
)

RESTORED_SHARES = 40


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


@pytest.mark.anyio
async def test_the_default_template_knows_its_restored_position(database_url: str, tmp_path: Path) -> None:
    world = await make_world_with_position(database_url)
    strategy_class, config_class = load_strategy_classes(STRATEGY_TEMPLATE, tmp_path)
    strategy: Any = strategy_class(create_config(config_class, instrument_id=APPLE_ID, bar_type=DAY_BAR_TYPE))

    async with run_node(world, strategy, 1):
        assert strategy.is_long is True


@pytest.mark.anyio
async def test_the_default_template_starts_flat_without_a_position(database_url: str, tmp_path: Path) -> None:
    strategy_class, config_class = load_strategy_classes(STRATEGY_TEMPLATE, tmp_path)
    strategy: Any = strategy_class(create_config(config_class, instrument_id=APPLE_ID, bar_type=DAY_BAR_TYPE))

    async with run_node(make_world(database_url), strategy, 1):
        assert strategy.is_long is False


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
