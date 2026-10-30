"""The metric functions with trades of many instruments (docs/architecture/backtest.md sections 10.10.5 and 10.10.8)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from atrade.backtest import (
    BacktestTrade,
    EquityPoint,
    calculate_metrics,
    calculate_universe_equity_curve,
    find_round_trips,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange

DAY_1 = datetime(2026, 3, 2, tzinfo=UTC)


def at_day(day: int) -> datetime:
    return DAY_1 + timedelta(days=day - 1)


def make_trade(day: int, side: Literal["BUY", "SELL"], price: int, symbol: str) -> BacktestTrade:
    return BacktestTrade(
        time_utc=at_day(day),
        side=side,
        quantity_shares=Decimal(10),
        price_usd=Decimal(price),
        commission_usd=Decimal(0),
        symbol=symbol,
        exchange="NASDAQ",
    )


def make_bar(day: int, close: int) -> Bar:
    """A daily bar that ends at the start of `day`."""
    price = Decimal(close)
    return Bar(start_utc=at_day(day - 1), open=price, high=price, low=price, close=price, volume=Decimal(1000))


# AAA: buy at 100 on day 1, sell at 110 on day 3. BBB: buy at 50 on day 2, sell at 45 on day 4.
TRADES = [
    make_trade(1, "BUY", 100, "AAA"),
    make_trade(2, "BUY", 50, "BBB"),
    make_trade(3, "SELL", 110, "AAA"),
    make_trade(4, "SELL", 45, "BBB"),
]


def test_round_trips_count_for_each_instrument() -> None:
    round_trips = find_round_trips(TRADES)

    assert [(trip.start_utc, trip.end_utc, trip.profit_usd) for trip in round_trips] == [
        (at_day(1), at_day(3), Decimal(100)),
        (at_day(2), at_day(4), Decimal(-50)),
    ]


def test_a_buy_of_one_instrument_and_a_sell_of_another_do_not_end_a_round_trip() -> None:
    trades = [make_trade(1, "BUY", 100, "AAA"), make_trade(2, "SELL", 100, "BBB")]

    assert find_round_trips(trades) == []


def test_the_equity_is_the_cash_plus_all_positions_at_their_last_close() -> None:
    bars_by_instrument: dict[tuple[str | None, str | None], list[Bar]] = {
        ("AAA", "NASDAQ"): [make_bar(1, 100), make_bar(2, 105), make_bar(3, 110), make_bar(4, 120)],
        # BBB has no bar that ends on day 3: its last close counts.
        ("BBB", "NASDAQ"): [make_bar(2, 50), make_bar(4, 45)],
    }

    equity_curve = calculate_universe_equity_curve(
        start_cash=Decimal(10000), bars_by_instrument=bars_by_instrument, bar_period=BarPeriod.ONE_DAY, trades=TRADES
    )

    assert equity_curve == [
        EquityPoint(time_utc=at_day(1), equity_usd=Decimal(10000)),
        # Cash 10000 - 1000 - 500, AAA 10 × 105, BBB 10 × 50.
        EquityPoint(time_utc=at_day(2), equity_usd=Decimal(10050)),
        # AAA sold at 110. BBB 10 × 50.
        EquityPoint(time_utc=at_day(3), equity_usd=Decimal(10100)),
        EquityPoint(time_utc=at_day(4), equity_usd=Decimal(10050)),
    ]


def test_the_exposure_counts_the_bars_with_a_position_in_any_instrument() -> None:
    equity_curve = [EquityPoint(time_utc=at_day(day), equity_usd=Decimal(10000)) for day in range(1, 6)]
    # Day 1 and day 2: 10 AAA and -10 BBB. The sum of the shares is 0, but the test has positions. Day 3 to 5: none.
    metrics = calculate_metrics(
        paper_capital_usd=Decimal(10000),
        time_range=TimeRange(start_utc=at_day(1) - timedelta(days=1), end_utc=at_day(5)),
        equity_curve=equity_curve,
        trades=[
            make_trade(1, "BUY", 100, "AAA"),
            make_trade(1, "SELL", 50, "BBB"),
            make_trade(3, "SELL", 100, "AAA"),
            make_trade(3, "BUY", 50, "BBB"),
        ],
    )

    assert metrics.exposure_percent == Decimal("40.00")
