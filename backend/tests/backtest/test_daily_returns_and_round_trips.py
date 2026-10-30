"""The daily returns and the round trips of the backtest public entry (docs/architecture/backtest.md 10.9.1, 10.9.2)."""

from datetime import UTC, datetime
from decimal import Decimal

from atrade.backtest import BacktestTrade, EquityPoint, RoundTrip, calculate_daily_returns, find_round_trips


def point(day: int, hour: int, equity: str) -> EquityPoint:
    return EquityPoint(time_utc=datetime(2026, 3, day, hour, tzinfo=UTC), equity_usd=Decimal(equity))


def trade(day: int, side: str, quantity: str, price: str, commission: str = "0") -> BacktestTrade:
    return BacktestTrade(
        time_utc=datetime(2026, 3, day, tzinfo=UTC),
        side="BUY" if side == "BUY" else "SELL",
        quantity_shares=Decimal(quantity),
        price_usd=Decimal(price),
        commission_usd=Decimal(commission),
    )


def test_a_daily_return_uses_the_last_point_of_each_utc_day_and_the_paper_capital_before_the_first_day() -> None:
    # 1-hour bars: 3 points on March 2 and 2 points on March 3. Only the last point of each day counts.
    equity_curve = [
        point(2, 15, "10100"),
        point(2, 16, "9000"),
        point(2, 17, "10200"),
        point(3, 15, "9000"),
        point(3, 16, "10098"),
    ]

    daily_returns = calculate_daily_returns(start_capital_usd=Decimal(10000), equity_curve=equity_curve)

    # 10200 / 10000 - 1 = 0.02. 10098 / 10200 - 1 = -0.01.
    assert daily_returns == [Decimal("0.02"), Decimal("-0.01")]


def test_daily_returns_of_an_empty_equity_curve_are_empty() -> None:
    assert calculate_daily_returns(start_capital_usd=Decimal(10000), equity_curve=[]) == []


def test_a_round_trip_goes_from_no_position_back_to_no_position_with_the_profit_after_commissions() -> None:
    trades = [
        trade(2, "BUY", "10", "100", "1"),
        trade(3, "BUY", "10", "110", "1"),
        trade(4, "SELL", "20", "120", "2"),
        trade(5, "SELL", "5", "50", "1"),
        trade(6, "BUY", "5", "60", "1"),
        # A position that is still open is not a round trip.
        trade(7, "BUY", "1", "60"),
    ]

    round_trips = find_round_trips(trades)

    assert round_trips == [
        # 20 * 120 - 10 * 100 - 10 * 110 - 4 = 296. The entry amount is 1000 + 1100 = 2100.
        RoundTrip(
            start_utc=datetime(2026, 3, 2, tzinfo=UTC),
            end_utc=datetime(2026, 3, 4, tzinfo=UTC),
            profit_usd=Decimal(296),
            entry_amount_usd=Decimal(2100),
        ),
        # A short sale: 5 * 50 - 5 * 60 - 2 = -52. The entry amount is 250.
        RoundTrip(
            start_utc=datetime(2026, 3, 5, tzinfo=UTC),
            end_utc=datetime(2026, 3, 6, tzinfo=UTC),
            profit_usd=Decimal(-52),
            entry_amount_usd=Decimal(250),
        ),
    ]
