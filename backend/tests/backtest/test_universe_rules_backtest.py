"""The code of the universe mode runs a multi-instrument backtest in a real child process (#201).

The first quarter has AAA and BBB, the second quarter BBB and CCC. The close of each instrument goes up by 1 each day.
At the range start the closes are AAA 500, BBB 600, and CCC 700, so the rank by SMA high to low is CCC, BBB, AAA.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import psycopg
import pytest

from atrade.foundation.instrument import Instrument
from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.backtest.universe_data import (
    AAA,
    BBB,
    CCC,
    QUARTER_MEMBERS,
    RANGE_END_UTC,
    RANGE_START_UTC,
    SECOND_QUARTER_START_UTC,
    make_universe_request,
    save_us_universe_quarters,
)
from tests.fakes.clock import FixedClock
from tests.saved_ranges import save_ibkr_saved_range
from tests.strategy.rules_examples import Json, condition, group, indicator, make_universe_rules, number, price

FIRST_BAR_UTC = RANGE_START_UTC - timedelta(days=400)
START_PRICES = {AAA: 100, BBB: 200, CCC: 300}


def save_test_data(database_url: str) -> None:
    save_us_universe_quarters(database_url, QUARTER_MEMBERS)
    with psycopg.connect(database_url, autocommit=True) as connection:
        for instrument, start_price in START_PRICES.items():
            connection.cursor().executemany(
                """
                INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close,
                    volume)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, '1-DAY', %(start_utc)s, %(price)s, %(price)s,
                    %(price)s, %(price)s, 1000000)
                """,
                [
                    {
                        "symbol": instrument.symbol,
                        "exchange": instrument.exchange,
                        "currency": instrument.currency,
                        "start_utc": FIRST_BAR_UTC + timedelta(days=index),
                        "price": Decimal(start_price + index),
                    }
                    for index in range((RANGE_END_UTC - FIRST_BAR_UTC).days)
                ],
            )
            save_ibkr_saved_range(connection, instrument, "1-DAY")


def rank_rules(hold_count: int, entry: Json | None = None, exits: Json | None = None) -> Json:
    return make_universe_rules(
        entry, exits=exits, rank_indicator=indicator("sma", period=5), hold_count=hold_count, rebalance_period="monthly"
    )


async def run_rules(web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, rules: Json) -> list[Any]:
    save_test_data(database_url)
    strategy = (await web_client.post("/api/strategies", json={"name": "Universe rules"})).json()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"rules": rules})).json()
    request = make_universe_request(version["id"], universe_kind="rule", top_n=2)
    response = await web_client.post("/api/backtests", json=request)
    assert response.status_code == 201, response.text
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=120):
        backtest = await wait_for_final_status(web_client, response.json()["id"])
    assert backtest["status"] == "finished", backtest["error_message"]
    return backtest["trades"]


def read_time(trade: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(trade["time_utc"])


def find_sides(trades: list[Any], instrument: Instrument) -> list[str]:
    return [trade["side"] for trade in trades if trade["symbol"] == instrument.symbol]


def count_max_positions(trades: list[Any]) -> int:
    held: dict[str, Decimal] = {}
    most = 0
    for trade in sorted(trades, key=read_time):
        shares = Decimal(trade["quantity_shares"])
        held[trade["symbol"]] = held.get(trade["symbol"], Decimal(0)) + (shares if trade["side"] == "BUY" else -shares)
        most = max(most, sum(1 for value in held.values() if value != 0))
    return most


@pytest.mark.anyio
async def test_each_rebalance_sells_first_and_holds_at_most_n_members(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    trades = await run_rules(web_client, database_url, clock, rank_rules(hold_count=1))

    # BBB has the best rank in the first quarter. CCC replaces it in the second quarter.
    assert find_sides(trades, AAA) == []
    assert find_sides(trades, BBB) == ["BUY", "SELL"]
    assert find_sides(trades, CCC) == ["BUY"]
    sell_bbb = next(trade for trade in trades if trade["symbol"] == BBB.symbol and trade["side"] == "SELL")
    buy_ccc = next(trade for trade in trades if trade["symbol"] == CCC.symbol)
    # The buy goes after the sell fills. Both fill on the bars of the same day.
    assert SECOND_QUARTER_START_UTC < read_time(sell_bbb) <= read_time(buy_ccc)
    assert trades.index(sell_bbb) < trades.index(buy_ccc)
    assert count_max_positions(trades) == 1


@pytest.mark.anyio
async def test_each_member_gets_an_equal_weight(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    trades = await run_rules(web_client, database_url, clock, rank_rules(hold_count=2))

    first_buys = [trade for trade in sorted(trades, key=read_time) if trade["side"] == "BUY"][:2]
    assert {trade["symbol"] for trade in first_buys} == {AAA.symbol, BBB.symbol}
    values = [Decimal(trade["quantity_shares"]) * Decimal(trade["price_usd"]) for trade in first_buys]
    # Each value is near 95% of 100000 / 2. The fill price is a little higher than the close of the rank.
    for value in values:
        assert abs(value - Decimal(47500)) < Decimal(475)
    assert count_max_positions(trades) == 2


@pytest.mark.anyio
async def test_a_member_that_does_not_pass_the_filter_gets_no_rank(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    entry = group("all_of", condition(price(), "below", number(550)))

    trades = await run_rules(web_client, database_url, clock, rank_rules(hold_count=1, entry=entry))

    # BBB has the better rank, but only AAA passes the filter.
    assert find_sides(trades, BBB) == []
    assert find_sides(trades, AAA)[0] == "BUY"


@pytest.mark.anyio
async def test_the_exit_items_run_on_each_bar_of_each_member(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    trades = await run_rules(web_client, database_url, clock, rank_rules(hold_count=2, exits={"exit_after_bars": 3}))

    for instrument in (AAA, BBB):
        member_trades = [trade for trade in sorted(trades, key=read_time) if trade["symbol"] == instrument.symbol]
        assert [trade["side"] for trade in member_trades[:2]] == ["BUY", "SELL"]
        held_for = read_time(member_trades[1]) - read_time(member_trades[0])
        # The buy fills at the close after the rank. The sell order goes at the third bar with the position.
        assert timedelta(days=2) <= held_for <= timedelta(days=4)
