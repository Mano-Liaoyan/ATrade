"""The daily stock split check of the forward-test worker: the try times, the retries, and the restart request
(docs/architecture/forward_test.md section 12.22). Real PostgreSQL, the IBKR fake, and a fixed clock."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from atrade.forward_test import MARKETS, StockSplitCheck, find_try_times
from atrade.foundation.bar import Bar
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_stock_position
from tests.paper_trading.stock_split_setup import (
    ACCOUNT_ID,
    APPLE,
    DAY_BEFORE_UTC,
    read_split_checks,
    save_close_before_ex_date,
    write_ledger_start,
    write_owner_fill,
)

[US_MARKET, HK_MARKET] = MARKETS
# Friday 2 January 2026, the ex-date of the tests. 08:00 ET is 13:00 UTC, 08:30 HKT is 00:30 UTC.
EX_DAY = date(2026, 1, 2)


def utc(hour: int, minute: int, day: int = 2) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


class CheckRun:
    """The check with a fake gateway that counts the connections."""

    def __init__(self, database_url: str, clock: FixedClock, apple_quantity: str) -> None:
        self.gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
        self.gateway_connection.portfolio = [
            make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity=apple_quantity, market_price="100")
        ]
        self.connection_count = 0
        self.restarts: list[list[int]] = []
        self.check = StockSplitCheck(
            database_url=database_url,
            clock=clock,
            settings=Settings(database_url=database_url, ibkr_account_id=ACCOUNT_ID),
            open_gateway_connection=self.open_gateway_connection,
            connection_lock=asyncio.Lock(),
            request_restart=self.restarts.append,
        )

    def open_gateway_connection(self) -> GatewayConnection:
        self.connection_count += 1
        return self.gateway_connection


def test_the_tries_start_at_08_00_et_and_08_30_hkt_and_end_5_minutes_before_the_open() -> None:
    assert find_try_times(US_MARKET, EX_DAY) == [
        utc(13, 0),
        utc(13, 15),
        utc(13, 30),
        utc(13, 45),
        utc(14, 0),
        utc(14, 15),
    ]
    assert find_try_times(HK_MARKET, EX_DAY) == [utc(0, 30), utc(0, 45), utc(1, 0), utc(1, 15)]


@pytest.mark.anyio
async def test_incomplete_evidence_tries_again_every_15_minutes_and_the_last_try_writes_the_state(
    database_url: str, clock: FixedClock
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="400")
    run = CheckRun(database_url, clock, apple_quantity="40")

    connection_counts: list[int] = []
    for now_utc in [utc(12, 59), utc(13, 0), utc(13, 10), utc(13, 15), utc(14, 0), utc(14, 15), utc(14, 20)]:
        clock.now_utc = now_utc
        await run.check.run_due_tries()
        connection_counts.append(run.connection_count)
        if now_utc == utc(14, 0):
            assert read_split_checks(database_url) == []

    # The HK try of 00:30 UTC had no HKD instrument. The US tries: 13:00, 13:15, 14:00, and the last at 14:15.
    assert connection_counts == [0, 1, 1, 2, 3, 4, 4]
    assert read_split_checks(database_url) == [("AAPL", "position_only", "needed")]


@pytest.mark.anyio
async def test_no_try_runs_on_a_day_without_trading(database_url: str, clock: FixedClock) -> None:
    run = CheckRun(database_url, clock, apple_quantity="40")
    clock.now_utc = utc(13, 0, day=3)

    await run.check.run_due_tries()

    assert run.connection_count == 0


@pytest.mark.anyio
async def test_a_confirmed_split_asks_the_worker_to_restart_the_forward_tests_that_hold_the_instrument(
    database_url: str, clock: FixedClock
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="400")
    await save_close_before_ex_date(database_url, "400")
    run = CheckRun(database_url, clock, apple_quantity="40")
    # IBKR adjusted its bar of the stored day for a 4:1 split: evidence A.
    new_close = Decimal(100)
    run.gateway_connection.historical_bars[APPLE] = [
        Bar(start_utc=DAY_BEFORE_UTC, open=new_close, high=new_close, low=new_close, close=new_close, volume=Decimal(1))
    ]
    clock.now_utc = utc(13, 0)

    await run.check.run_due_tries()
    clock.now_utc = utc(13, 15)
    await run.check.run_due_tries()

    assert run.restarts == [[1]]
    assert run.connection_count == 1
    assert read_split_checks(database_url) == []


@pytest.mark.anyio
async def test_an_unreachable_gateway_at_the_last_try_leaves_the_check_to_the_next_trading_day(
    database_url: str, clock: FixedClock
) -> None:
    write_ledger_start(database_url)
    write_owner_fill(database_url, forward_test_id=1, quantity=10, price="400")
    run = CheckRun(database_url, clock, apple_quantity="40")
    run.gateway_connection.is_gateway_reachable = False
    clock.now_utc = utc(14, 15)

    await run.check.run_due_tries()
    clock.now_utc = utc(14, 20)
    await run.check.run_due_tries()

    assert run.connection_count == 1
    assert read_split_checks(database_url) == []
