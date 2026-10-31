"""The "Split check needed" state through the routes: "Apply split", "Keep ledger", the refused orders, and the
`split_check` of /ws/paper-trading (docs/architecture/paper_trading.md sections 11.6, 11.8, and 11.11)."""

from decimal import Decimal
from pathlib import Path

import pytest

from atrade.foundation.instrument import Instrument
from atrade.paper_trading import ForwardTestLedger, InstrumentCheck, OwnerOrder, StockSplitLedger
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values, make_stock_position
from tests.paper_trading.stock_split_setup import (
    ACCOUNT_ID,
    APPLE,
    EX_DATE_UTC,
    read_split_checks,
    save_close_before_ex_date,
    write_candidate,
    write_ledger_start,
    write_owner_fill,
)
from tests.paper_trading.test_owner_ledger import BY_HAND, ORDERS_PATH, find_position, open_client, read_account

MICROSOFT = Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD")
SPLIT_CHECK_NEEDED_DETAIL = "AAPL needs a split check. Apply the split or keep the ledger on the paper trading page."


def make_gateway() -> FakeGatewayConnection:
    """IBKR shows 40 AAPL. The ledger has 10: forward test 1 holds them."""
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="15000", cash_usd="10000")
    gateway_connection.portfolio = [
        make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity="40", market_price="100"),
        make_stock_position(ACCOUNT_ID, symbol="MSFT", quantity="5", market_price="100"),
    ]
    return gateway_connection


async def start_split_check_needed(database_url: str, clock: FixedClock) -> int:
    """Evidence A shows 4:1, the IBKR position shows 4:1, but only after the last try: the check writes the state
    with the evidence `ratios_differ`, because IBKR shows 20 shares, not 40."""
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="400")
    write_owner_fill(database_url, forward_test_id=None, quantity=5, price="100", instrument=MICROSOFT)
    await save_close_before_ex_date(database_url, "400")
    candidate = write_candidate(database_url, "4")
    ledger = StockSplitLedger(database_url=database_url, gateway_connection=make_gateway(), clock=clock)
    await ledger.check_instrument(
        InstrumentCheck(
            account=ACCOUNT_ID,
            instrument=APPLE,
            account_quantity=Decimal(20),
            candidate=candidate,
            check_day_utc=EX_DATE_UTC,
            is_last_try=True,
        )
    )
    return candidate.id


@pytest.mark.anyio
async def test_the_position_shows_the_split_check_and_apply_split_changes_the_ledger(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    stock_split_id = await start_split_check_needed(database_url, clock)
    async with open_client(
        database_url=database_url, clock=clock, frontend_build_dir=frontend_build_dir, gateway_connection=make_gateway()
    ) as client:
        before = find_position(await read_account(client), "AAPL")
        response = await client.post(f"/api/paper-trading/stock-splits/{before['split_check']['id']}/apply")
        again = await client.post(f"/api/paper-trading/stock-splits/{before['split_check']['id']}/apply")
        after = find_position(await read_account(client), "AAPL")

    assert before["split_check"] == {
        "id": 1,
        "stock_split_id": stock_split_id,
        "split_ratio": "4",
        "account_quantity_before": "10",
        "account_quantity_after": "20",
    }
    assert response.status_code == 200
    # The IBKR position of the check is 20: forward test 1 gets 40 shares, "By hand" gives 20 (section 11.11 step 4).
    assert response.json()["owners"] == [
        {"owner": {"kind": "forward_test", "forward_test_id": 1}, "quantity": "40", "average_cost": "100"},
        {"owner": BY_HAND, "quantity": "-20", "average_cost": None},
    ]
    assert again.status_code == 409
    assert after["split_check"] is None
    assert read_split_checks(database_url) == [("AAPL", "ratios_differ", "applied")]


@pytest.mark.anyio
async def test_keep_ledger_ends_the_state_and_the_difference_stays_unattributed(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    await start_split_check_needed(database_url, clock)
    async with open_client(
        database_url=database_url, clock=clock, frontend_build_dir=frontend_build_dir, gateway_connection=make_gateway()
    ) as client:
        response = await client.post("/api/paper-trading/stock-splits/1/keep-ledger")
        again = await client.post("/api/paper-trading/stock-splits/1/keep-ledger")
        unknown_apply = await client.post("/api/paper-trading/stock-splits/99/apply")
        unknown_keep = await client.post("/api/paper-trading/stock-splits/99/keep-ledger")
        position = find_position(await read_account(client), "AAPL")

    assert response.status_code == 200
    assert response.json() == {"id": 1, "symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD", "status": "kept"}
    assert again.status_code == 409
    assert unknown_apply.status_code == 404
    assert unknown_keep.status_code == 404
    assert position["split_check"] is None
    assert position["unattributed_quantity"] == "30"


@pytest.mark.anyio
async def test_an_order_by_hand_on_the_instrument_gets_409_and_other_instruments_trade(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    await start_split_check_needed(database_url, clock)
    async with open_client(
        database_url=database_url, clock=clock, frontend_build_dir=frontend_build_dir, gateway_connection=make_gateway()
    ) as client:
        await read_account(client)
        order = {
            "exchange": "NASDAQ",
            "currency": "USD",
            "side": "SELL",
            "quantity": 1,
            "order_type": "LMT",
            "limit_price": "100",
            "time_in_force": "DAY",
        }
        refused = await client.post(ORDERS_PATH, json={**order, "symbol": "AAPL"})
        sent = await client.post(ORDERS_PATH, json={**order, "symbol": "MSFT"})

    assert refused.status_code == 409
    assert refused.json() == {"detail": SPLIT_CHECK_NEEDED_DETAIL, "rule": "split_check_needed"}
    assert sent.status_code == 201


@pytest.mark.anyio
async def test_an_order_of_a_forward_test_on_the_instrument_is_refused(database_url: str, clock: FixedClock) -> None:
    await start_split_check_needed(database_url, clock)
    ledger = ForwardTestLedger(
        database_url=database_url, account=ACCOUNT_ID, forward_test_id=1, gateway_connection=make_gateway(), clock=clock
    )

    reason = await ledger.check_order(
        OwnerOrder(forward_test_id=1, instrument=APPLE, side="SELL", quantity=Decimal(1), limit_price=Decimal(100))
    )

    assert reason == SPLIT_CHECK_NEEDED_DETAIL
