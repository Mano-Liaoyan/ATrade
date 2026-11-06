"""The ATrade execution client and data client in a real LiveNode, with the IBKR fake and the owner ledger fake
(docs/architecture/forward_test.md section 12.19, docs/architecture.md section 17.4).

Each `run_node` is one start of a forward test child. The restart steps: send an order, fill it, restart, and check
the strategy position. Then a stock split changes the owner position, and a restart restores the new position.
"""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from atrade.forward_test import ForwardTestPosition, OwnerFill
from atrade.foundation.order_ref import read_order_source
from atrade.ibkr import OpenOrder
from tests.fakes.ibkr import LIVE_BAR_NOW_UTC, make_execution, make_forward_test_order
from tests.fakes.owner_ledger import SELL_TOO_LARGE_REASON, SPLIT_CHECK_NEEDED_REASON
from tests.forward_test.atrade_clients_node import (
    ACCOUNT_ID,
    APPLE,
    BUY_QUANTITY,
    CLIENT_ID,
    FORWARD_TEST_ID,
    POLL_SECONDS,
    ClientsWorld,
    make_strategy,
    make_world,
    run_node,
    send_today_bar,
    wait_until,
)

FILL_PRICE = "100.25"
OTHER_CLIENT_ID = 12


def fill_open_order(world: ClientsWorld, price: str = FILL_PRICE) -> OpenOrder:
    """IBKR fills the open order of the forward test completely."""
    open_order = world.gateway.open_orders.pop()
    world.gateway.executions.append(
        make_execution(
            ACCOUNT_ID,
            order_id=open_order.order_id,
            quantity=str(open_order.quantity),
            price=price,
            client_id=open_order.client_id,
        )
    )
    return open_order


@pytest.mark.anyio
async def test_the_restarted_strategy_gets_its_position_from_the_owner_ledger_and_does_not_buy_again(
    database_url: str,
) -> None:
    world = make_world(database_url)

    first_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, first_strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        open_order = fill_open_order(world)
        await wait_until(lambda: bool(first_strategy.own_positions()))

    # The orderRef is the ClientOrderId with FT<ID>, and the order went out with the client ID of the forward test.
    assert read_order_source(open_order.order_ref).forward_test_id == FORWARD_TEST_ID
    assert open_order.client_id == CLIENT_ID
    assert open_order.side == "BUY"
    assert open_order.quantity == BUY_QUANTITY
    assert first_strategy.positions_at_stop == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))]
    assert world.ledger.read_quantity(FORWARD_TEST_ID, APPLE) == BUY_QUANTITY
    assert world.ledger.cash_usd == Decimal(10000) - BUY_QUANTITY * Decimal(FILL_PRICE)

    restarted_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, restarted_strategy, 2) as data_factory:
        await send_today_bar(world, data_factory, "101")
        await wait_until(lambda: bool(restarted_strategy.bars))

    assert restarted_strategy.positions_at_start == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))]
    # No second buy: the ledger checked 1 order, and IBKR got no new order.
    assert len(world.ledger.checked_orders) == 1
    assert world.gateway.open_orders == []

    # Stock split 2-for-1: the ledger change doubles the owner position and halves the average price (section 11.11).
    world.ledger.positions[FORWARD_TEST_ID, APPLE] = ForwardTestPosition(
        APPLE, Decimal(2 * BUY_QUANTITY), Decimal(FILL_PRICE) / 2
    )
    strategy_after_split = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy_after_split, 3) as data_factory:
        await send_today_bar(world, data_factory, "50.5")
        await wait_until(lambda: bool(strategy_after_split.bars))

    assert strategy_after_split.positions_at_start == [(Decimal(2 * BUY_QUANTITY), Decimal("50.125"))]
    assert len(world.ledger.checked_orders) == 1


@pytest.mark.anyio
async def test_the_account_balance_follows_the_owner_ledger_cash_after_each_fill_and_at_a_restart(
    database_url: str,
) -> None:
    world = make_world(database_url)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        fill_open_order(world, "100")
        await wait_until(lambda: strategy.read_cash() == Decimal(9000))

    restored_strategy = make_strategy(claims_external_orders=True, sell_quantity=BUY_QUANTITY)
    async with run_node(world, restored_strategy, 2) as data_factory:
        assert restored_strategy.read_cash() == Decimal(9000)
        await send_today_bar(world, data_factory, "150")
        await wait_until(lambda: bool(world.gateway.open_orders))
        fill_open_order(world, "150")
        await wait_until(lambda: restored_strategy.read_cash() == Decimal(10500))

    assert world.ledger.cash_usd == Decimal(10500)
    assert world.ledger.read_quantity(FORWARD_TEST_ID, APPLE) == 0


@pytest.mark.anyio
async def test_a_fill_above_the_cash_gives_a_balance_of_0_also_at_a_restart(database_url: str) -> None:
    """A market order can fill above the price of the ledger check. The engine refuses a negative balance."""
    world = make_world(database_url)
    world.ledger.cash_usd = Decimal(100)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "10")
        await wait_until(lambda: bool(world.gateway.open_orders))
        fill_open_order(world, "11")
        await wait_until(lambda: strategy.read_cash() == 0)

    restarted_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, restarted_strategy, 2):
        assert restarted_strategy.read_cash() == 0

    assert world.ledger.cash_usd == Decimal(-10)


@pytest.mark.anyio
async def test_without_external_order_claims_the_restored_position_is_not_the_strategy_position(
    database_url: str,
) -> None:
    """Fact for section 21.1: NautilusTrader 2.0.0rc7 makes an external order and an inferred fill from the position
    report. Without `external_order_instrument_ids`, the position belongs to the strategy `EXTERNAL`."""
    world = make_world(database_url)
    await world.ledger.save_fill(
        OwnerFill(
            FORWARD_TEST_ID, APPLE, "BUY", Decimal(5), Decimal(100), LIVE_BAR_NOW_UTC, "FT7", "0001", 1, Decimal(0)
        )
    )

    strategy = make_strategy(claims_external_orders=False)
    async with run_node(world, strategy, 1):
        pass

    assert strategy.positions_at_start == []


@pytest.mark.anyio
async def test_an_order_that_fails_a_ledger_rule_gets_order_denied_and_goes_nowhere(database_url: str) -> None:
    world = make_world(database_url)
    world.ledger.split_check_needed.add(APPLE)

    buying_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, buying_strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(buying_strategy.denied_reasons))
    world.ledger.split_check_needed.clear()
    selling_strategy = make_strategy(claims_external_orders=True, sell_quantity=1)
    async with run_node(world, selling_strategy, 2) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(selling_strategy.denied_reasons))

    assert buying_strategy.denied_reasons == [SPLIT_CHECK_NEEDED_REASON]
    assert selling_strategy.denied_reasons == [SELL_TOO_LARGE_REASON]
    assert world.gateway.open_orders == []


@pytest.mark.anyio
async def test_the_client_reports_only_the_orders_and_fills_of_its_own_client_id(database_url: str) -> None:
    world = make_world(database_url)
    # An open order and a fill of another client ID on the same paper account, and an own fill before this run.
    world.gateway.open_orders.append(
        make_forward_test_order(ACCOUNT_ID, forward_test_id=8, order_id=900, client_id=OTHER_CLIENT_ID)
    )
    world.gateway.executions.append(
        make_execution(ACCOUNT_ID, order_id=900, quantity="5", price="10.50", client_id=OTHER_CLIENT_ID)
    )

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: len(world.gateway.open_orders) == 2)
        own_order = world.gateway.open_orders.pop()
        world.gateway.executions.append(
            make_execution(ACCOUNT_ID, order_id=own_order.order_id, quantity="10", price="99", client_id=CLIENT_ID)
        )
        await wait_until(lambda: bool(strategy.own_positions()))
        orders = strategy.cache.orders()  # pyright: ignore[reportUnknownMemberType]

    assert [str(order.client_order_id) for order in orders] == [own_order.order_ref]
    assert strategy.positions_at_stop == [(Decimal(10), Decimal(99))]
    assert world.ledger.fills[0].order_ref == own_order.order_ref
    assert len(world.ledger.fills) == 1
    assert datetime.now(UTC) > world.ledger.fills[0].time_utc


@pytest.mark.anyio
async def test_two_equal_partial_fills_of_one_order_both_go_into_the_owner_ledger(database_url: str) -> None:
    """The execution ID tells the executions apart. The 2 executions have the same quantity, price, and time."""
    world = make_world(database_url)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        open_order = world.gateway.open_orders.pop()
        half = str(open_order.quantity / 2)
        world.gateway.executions.extend(
            make_execution(
                ACCOUNT_ID,
                order_id=open_order.order_id,
                quantity=half,
                price=FILL_PRICE,
                client_id=CLIENT_ID,
                execution_id=f"0000e0d5.{number}",
            )
            for number in range(2)
        )
        # The fill events come to the strategy after the ledger save, so the wait reads the position of the strategy.
        await wait_until(lambda: strategy.own_positions() == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))])

    assert world.ledger.read_quantity(FORWARD_TEST_ID, APPLE) == BUY_QUANTITY
    assert strategy.positions_at_stop == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))]


@pytest.mark.anyio
async def test_an_order_that_ibkr_ends_without_a_fill_is_no_longer_open(database_url: str) -> None:
    world = make_world(database_url)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        await wait_until(lambda: strategy.count_open_orders() == 1)
        world.gateway.open_orders.clear()
        await wait_until(lambda: strategy.count_open_orders() == 0)

    assert world.ledger.fills == []


@pytest.mark.anyio
async def test_a_held_fill_of_an_order_that_left_the_open_orders_does_not_cancel_the_order(database_url: str) -> None:
    """A fill stays out of the fill read until its commission report comes. The open orders no longer show the order."""
    world = make_world(database_url)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        await wait_until(lambda: strategy.count_open_orders() == 1)
        open_order = world.gateway.open_orders.pop()
        execution = make_execution(
            ACCOUNT_ID, order_id=open_order.order_id, quantity="10", price=FILL_PRICE, client_id=CLIENT_ID
        )
        world.gateway.executions.append(replace(execution, is_held=True))
        await asyncio.sleep(POLL_SECONDS * 5)
        assert strategy.count_open_orders() == 1
        world.gateway.executions[0] = execution
        await wait_until(lambda: strategy.own_positions() == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))])


@pytest.mark.anyio
async def test_the_client_connects_again_after_a_gateway_restart_and_reads_the_fill_of_the_gap(
    database_url: str,
) -> None:
    """ib_async does not connect again by itself. The order stays open at IBKR and fills while the socket is down."""
    world = make_world(database_url)

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        open_order = world.gateway.open_orders.pop()
        world.gateway.connected = False
        world.gateway.is_gateway_reachable = False
        world.gateway.executions.append(
            make_execution(
                ACCOUNT_ID, order_id=open_order.order_id, quantity="10", price=FILL_PRICE, client_id=CLIENT_ID
            )
        )
        # The failed connect does not end the fill check.
        await asyncio.sleep(POLL_SECONDS * 5)
        assert world.ledger.fills == []
        world.gateway.is_gateway_reachable = True
        await wait_until(lambda: strategy.own_positions() == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))])

    assert world.gateway.connected is False  # The stop disconnects.
    assert world.ledger.read_quantity(FORWARD_TEST_ID, APPLE) == BUY_QUANTITY
