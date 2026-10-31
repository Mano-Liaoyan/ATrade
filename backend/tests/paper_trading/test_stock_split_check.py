"""The stock split check of one instrument: the ledger change of a confirmed stock split and the "Split check needed"
state (docs/architecture/paper_trading.md section 11.11). Real PostgreSQL and the IBKR fake."""

from decimal import Decimal
from pathlib import Path

import pytest

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.market_data import BarRequest, BarSource, StockSplitCandidate, read_saved_bars
from atrade.paper_trading import ForwardTestLedger, InstrumentCheck, StockSplitLedger
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values, make_stock_position
from tests.paper_trading.stock_split_setup import (
    ACCOUNT_ID,
    APPLE,
    DAY_BEFORE_UTC,
    EX_DATE_UTC,
    read_split_checks,
    save_close_before_ex_date,
    write_candidate,
    write_ledger_start,
    write_owner_fill,
)
from tests.paper_trading.test_owner_ledger import BY_HAND, find_position, open_client, read_account


def make_gateway(apple_quantity: str) -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="15000", cash_usd="10000")
    gateway_connection.portfolio = [
        make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity=apple_quantity, market_price="20")
    ]
    return gateway_connection


def forward_test_owner(forward_test_id: int) -> dict[str, object]:
    return {"kind": "forward_test", "forward_test_id": forward_test_id}


async def run_check(
    database_url: str,
    clock: FixedClock,
    *,
    account_quantity: str,
    candidate: StockSplitCandidate | None,
    is_last_try: bool = True,
) -> tuple[str, list[int]]:
    ledger = StockSplitLedger(database_url=database_url, gateway_connection=make_gateway(account_quantity), clock=clock)
    outcome = await ledger.check_instrument(
        InstrumentCheck(
            account=ACCOUNT_ID,
            instrument=APPLE,
            account_quantity=Decimal(account_quantity),
            candidate=candidate,
            check_day_utc=EX_DATE_UTC,
            is_last_try=is_last_try,
        )
    )
    return outcome.result, outcome.forward_test_ids


async def read_forward_test_cash(database_url: str, clock: FixedClock, forward_test_id: int) -> Decimal:
    ledger = ForwardTestLedger(
        database_url=database_url,
        account=ACCOUNT_ID,
        forward_test_id=forward_test_id,
        gateway_connection=make_gateway("0"),
        clock=clock,
    )
    return await ledger.read_cash_usd(forward_test_id)


@pytest.mark.anyio
async def test_a_confirmed_3_for_2_split_changes_the_ledger_and_the_stored_bars(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=3, price="30")
    write_owner_fill(database_url, forward_test_id=2, quantity=5, price="30")
    await save_close_before_ex_date(database_url, "30")
    candidate = write_candidate(database_url, "1.5")

    result = await run_check(database_url, clock, account_quantity="12", candidate=candidate)

    assert result == ("confirmed", [1, 2])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=make_gateway("12"),
    ) as client:
        position = find_position(await read_account(client), "AAPL")
    # The total cost stays: 3 x 30 = 90 for 4 shares, 5 x 30 = 150 for 7 shares. "By hand" gets 1 share at 20.
    assert position["owners"] == [
        {"owner": forward_test_owner(1), "quantity": "4", "average_cost": "22.5"},
        {"owner": forward_test_owner(2), "quantity": "7", "average_cost": "21.42857142857142857142857143"},
        {"owner": BY_HAND, "quantity": "1", "average_cost": "20"},
    ]
    assert position["unattributed_quantity"] == "0"
    assert position["split_check"] is None
    # Cash in lieu for 0.5 share at 30 / 1.5 = 20.
    assert await read_forward_test_cash(database_url, clock, 1) == Decimal(-90) + Decimal(10)
    assert await read_forward_test_cash(database_url, clock, 2) == Decimal(-150) + Decimal(10)
    saved = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DAY_BEFORE_UTC, EX_DATE_UTC)),
        source_order=[BarSource.IBKR],
    )
    assert [bar.close for bar in saved.bars] == [Decimal(20)]


@pytest.mark.anyio
async def test_a_confirmed_1_for_10_split_keeps_the_owner_sum_equal_to_the_ibkr_position(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=15, price="5")
    write_owner_fill(database_url, forward_test_id=2, quantity=7, price="5")
    await save_close_before_ex_date(database_url, "5")
    candidate = write_candidate(database_url, "0.1")

    result = await run_check(database_url, clock, account_quantity="2", candidate=candidate)

    assert result == ("confirmed", [1, 2])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=make_gateway("2"),
    ) as client:
        position = find_position(await read_account(client), "AAPL")
    assert position["owners"] == [
        {"owner": forward_test_owner(1), "quantity": "1", "average_cost": "75"},
        {"owner": BY_HAND, "quantity": "1", "average_cost": "50"},
    ]
    assert position["unattributed_quantity"] == "0"
    # Cash in lieu for 0.5 and 0.7 share at 5 / 0.1 = 50.
    assert await read_forward_test_cash(database_url, clock, 1) == Decimal(-75) + Decimal(25)
    assert await read_forward_test_cash(database_url, clock, 2) == Decimal(-35) + Decimal(35)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("split_ratio", "account_quantity", "evidence"),
    [
        ("4", "10", "bar_ratio_only"),
        (None, "40", "position_only"),
        ("4", "20", "ratios_differ"),
        ("4", "39", "share_count_differs"),
        ("1.37", "13", "unusual_ratio"),
    ],
)
async def test_evidence_that_does_not_agree_gives_the_split_check_needed_state(
    database_url: str, clock: FixedClock, split_ratio: str | None, account_quantity: str, evidence: str
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="30")
    candidate = None if split_ratio is None else write_candidate(database_url, split_ratio)

    result = await run_check(database_url, clock, account_quantity=account_quantity, candidate=candidate)

    assert result == ("split_check_needed", [])
    assert read_split_checks(database_url) == [("AAPL", evidence, "needed")]


@pytest.mark.anyio
async def test_incomplete_evidence_waits_for_the_next_try_before_the_last_try(
    database_url: str, clock: FixedClock
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="30")

    result = await run_check(database_url, clock, account_quantity="40", candidate=None, is_last_try=False)

    assert result == ("incomplete", [])
    assert read_split_checks(database_url) == []


@pytest.mark.anyio
async def test_evidence_a_alone_confirms_the_split_of_an_instrument_that_no_owner_holds(
    database_url: str, clock: FixedClock
) -> None:
    write_ledger_start(database_url)
    await save_close_before_ex_date(database_url, "40")
    candidate = write_candidate(database_url, "4")

    result = await run_check(database_url, clock, account_quantity="0", candidate=candidate)

    assert result == ("confirmed", [])
    saved = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DAY_BEFORE_UTC, EX_DATE_UTC)),
        source_order=[BarSource.IBKR],
    )
    assert [bar.close for bar in saved.bars] == [Decimal(10)]
