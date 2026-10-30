"""The metric functions of the backtest public entry: the equity curve and the metrics from bars and trades."""

from datetime import UTC, datetime
from decimal import Decimal

from atrade.backtest import BacktestTrade, EquityPoint, calculate_equity_curve, calculate_metrics
from atrade.foundation.bar import Bar, BarPeriod, TimeRange


def make_bar(day: int, close: str) -> Bar:
    close_price = Decimal(close)
    return Bar(
        start_utc=datetime(2026, 1, day, tzinfo=UTC),
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Decimal(1000),
    )


TRADES = [
    BacktestTrade(
        time_utc=datetime(2026, 1, 2, tzinfo=UTC),
        side="BUY",
        quantity_shares=Decimal(10),
        price_usd=Decimal(100),
        commission_usd=Decimal(1),
    ),
    BacktestTrade(
        time_utc=datetime(2026, 1, 4, tzinfo=UTC),
        side="SELL",
        quantity_shares=Decimal(10),
        price_usd=Decimal(90),
        commission_usd=Decimal(1),
    ),
]
TIME_RANGE = TimeRange(start_utc=datetime(2026, 1, 1, tzinfo=UTC), end_utc=datetime(2026, 1, 5, tzinfo=UTC))


def test_equity_curve_has_one_point_at_the_end_of_each_bar() -> None:
    bars = [make_bar(1, "100"), make_bar(2, "110"), make_bar(3, "90"), make_bar(4, "120")]

    equity_curve = calculate_equity_curve(
        start_cash=Decimal(10000), bars=bars, bar_period=BarPeriod.ONE_DAY, trades=TRADES
    )

    assert equity_curve == [
        EquityPoint(time_utc=datetime(2026, 1, 2, tzinfo=UTC), equity_usd=Decimal(9999)),
        EquityPoint(time_utc=datetime(2026, 1, 3, tzinfo=UTC), equity_usd=Decimal(10099)),
        EquityPoint(time_utc=datetime(2026, 1, 4, tzinfo=UTC), equity_usd=Decimal(9898)),
        EquityPoint(time_utc=datetime(2026, 1, 5, tzinfo=UTC), equity_usd=Decimal(9898)),
    ]


def test_metrics_measure_return_drawdown_and_trades() -> None:
    equity_curve = [
        EquityPoint(time_utc=datetime(2026, 1, 2, tzinfo=UTC), equity_usd=Decimal(9999)),
        EquityPoint(time_utc=datetime(2026, 1, 3, tzinfo=UTC), equity_usd=Decimal(10099)),
        EquityPoint(time_utc=datetime(2026, 1, 4, tzinfo=UTC), equity_usd=Decimal(9898)),
        EquityPoint(time_utc=datetime(2026, 1, 5, tzinfo=UTC), equity_usd=Decimal(9898)),
    ]

    metrics = calculate_metrics(
        paper_capital_usd=Decimal(10000), time_range=TIME_RANGE, equity_curve=equity_curve, trades=TRADES
    )

    assert metrics.final_equity_usd == Decimal(9898)
    assert metrics.total_return_percent == Decimal("-1.02")
    # The peak is 10099. The lowest point after it is 9898: 201 / 10099 = 1.99 %.
    assert metrics.max_drawdown_percent == Decimal("1.99")
    assert metrics.trade_count == 2


def test_metrics_without_bars_keep_the_paper_capital() -> None:
    metrics = calculate_metrics(paper_capital_usd=Decimal(10000), time_range=TIME_RANGE, equity_curve=[], trades=[])

    assert metrics.final_equity_usd == Decimal(10000)
    assert metrics.total_return_percent == Decimal("0.00")
    assert metrics.max_drawdown_percent == Decimal("0.00")
