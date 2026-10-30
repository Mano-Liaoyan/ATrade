"""The ATrade execution client in a LiveNode with the real owner ledger in PostgreSQL and the IBKR fake
(docs/architecture/forward_test.md sections 12.18 and 12.19, paper_trading.md section 11.10).
"""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest

from atrade.paper_trading import write_capital_allocation
from tests.fakes.ibkr import make_execution
from tests.forward_test.atrade_clients_node import (
    ACCOUNT_ID,
    APPLE,
    BUY_QUANTITY,
    CLIENT_ID,
    FORWARD_TEST_ID,
    make_strategy,
    make_world_with_owner_ledger,
    run_node,
    send_today_bar,
    wait_until,
)

FILL_PRICE = "20.5"


async def allocate_capital(database_url: str, allocated_capital_usd: str) -> None:
    """The Web process moves the allocated capital from "By hand" to the forward test at the start."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        await write_capital_allocation(
            connection,
            account=ACCOUNT_ID,
            forward_test_id=FORWARD_TEST_ID,
            allocated_capital_usd=Decimal(allocated_capital_usd),
            time_utc=datetime(2026, 1, 2, tzinfo=UTC),
        )
        await connection.commit()


def count_fill_rows(database_url: str) -> int:
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT count(*) FROM owner_ledger_entry WHERE entry_kind = 'fill' AND owner_kind = 'forward_test'"
        ).fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.anyio
async def test_a_buy_larger_than_the_owner_cash_gets_order_denied(database_url: str) -> None:
    world = make_world_with_owner_ledger(database_url)
    # NautilusTrader checks 10 x 100 (the bar close) against the owner cash and lets the order pass. The ledger uses
    # the last daily close of IBKR (at least 100.5 in the fake) and refuses it (paper_trading.md section 11.13).
    await allocate_capital(database_url, "1001")

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(strategy.denied_reasons))

    [reason] = strategy.denied_reasons
    assert reason.startswith("Forward test 7 has 1001.00 USD cash and open buy orders for 0.00 USD.")
    assert world.gateway.open_orders == []


@pytest.mark.anyio
async def test_a_sell_larger_than_the_owner_position_gets_order_denied(database_url: str) -> None:
    world = make_world_with_owner_ledger(database_url)
    await allocate_capital(database_url, "10000")

    strategy = make_strategy(claims_external_orders=True, sell_quantity=1)
    async with run_node(world, strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(strategy.denied_reasons))

    assert strategy.denied_reasons == [
        "Forward test 7 holds 0 AAPL and has open sell orders for 0. ATrade refuses a sell order for 1."
    ]
    assert world.gateway.open_orders == []


@pytest.mark.anyio
async def test_the_fill_goes_into_the_owner_ledger_once_and_the_restart_gets_the_owner_position(
    database_url: str,
) -> None:
    world = make_world_with_owner_ledger(database_url)
    await allocate_capital(database_url, "10000")

    first_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, first_strategy, 1) as data_factory:
        await send_today_bar(world, data_factory, "100")
        await wait_until(lambda: bool(world.gateway.open_orders))
        open_order = world.gateway.open_orders.pop()
        world.gateway.executions.append(
            make_execution(
                ACCOUNT_ID, order_id=open_order.order_id, quantity="10", price=FILL_PRICE, client_id=CLIENT_ID
            )
        )
        await wait_until(lambda: bool(first_strategy.own_positions()))

    assert count_fill_rows(database_url) == 1
    assert await world.ledger.read_cash_usd(FORWARD_TEST_ID) == Decimal(10000) - BUY_QUANTITY * Decimal(FILL_PRICE)

    # The restart reads the same execution again. It adds no row, and the strategy gets the owner position.
    restarted_strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, restarted_strategy, 2) as data_factory:
        await send_today_bar(world, data_factory, "101")
        await wait_until(lambda: bool(restarted_strategy.bars))

    assert restarted_strategy.positions_at_start == [(Decimal(BUY_QUANTITY), Decimal(FILL_PRICE))]
    assert world.gateway.open_orders == []
    assert count_fill_rows(database_url) == 1
    [position] = await world.ledger.read_positions(FORWARD_TEST_ID)
    assert (position.instrument, position.quantity, position.average_price) == (APPLE, 10, Decimal(FILL_PRICE))
