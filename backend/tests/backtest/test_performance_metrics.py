"""The metrics of docs/architecture/backtest.md section 10.9.2 and the short data rules of section 10.9.3.

The expected values are calculated by hand from the definitions of the specification.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from atrade.backtest import BacktestMetrics, BacktestTrade, EquityPoint, calculate_metrics
from atrade.foundation.bar import TimeRange

PAPER_CAPITAL = Decimal(10000)
# 90 days: the shortest range with a CAGR.
RANGE_OF_90_DAYS = TimeRange(start_utc=datetime(2026, 1, 1, tzinfo=UTC), end_utc=datetime(2026, 4, 1, tzinfo=UTC))
RANGE_OF_89_DAYS = TimeRange(start_utc=datetime(2026, 1, 2, tzinfo=UTC), end_utc=datetime(2026, 4, 1, tzinfo=UTC))


def daily_curve(*equities: str) -> list[EquityPoint]:
    """One point at 21:00 UTC of each day from January 5."""
    return [
        EquityPoint(time_utc=datetime(2026, 1, 5, 21, tzinfo=UTC) + timedelta(days=index), equity_usd=Decimal(equity))
        for index, equity in enumerate(equities)
    ]


def trade(day: int, side: str, quantity: str, price: str, commission: str = "1") -> BacktestTrade:
    return BacktestTrade(
        time_utc=datetime(2026, 1, day, 10, tzinfo=UTC),
        side="BUY" if side == "BUY" else "SELL",
        quantity_shares=Decimal(quantity),
        price_usd=Decimal(price),
        commission_usd=Decimal(commission),
    )


def metrics_of(
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade] | None = None,
    time_range: TimeRange = RANGE_OF_90_DAYS,
) -> BacktestMetrics:
    return calculate_metrics(
        paper_capital_usd=PAPER_CAPITAL, time_range=time_range, equity_curve=equity_curve, trades=trades or []
    )


# Daily returns: 2 %, -1 %, 2.00040 %, -1 %, 1.99078 %.
WORKED_CURVE = daily_curve("10200", "10098", "10300", "10197", "10400")
# A win of 98 (entry 1000) and a loss of -52 (entry 1000). The position is open at the points of January 5, 7, and 8.
WORKED_TRADES = [
    trade(5, "BUY", "10", "100"),
    trade(6, "SELL", "10", "110"),
    trade(7, "BUY", "10", "100"),
    trade(9, "SELL", "10", "95"),
]


def test_every_new_metric_has_the_value_of_its_definition() -> None:
    metrics = metrics_of(WORKED_CURVE, WORKED_TRADES)

    assert metrics.trade_count == 4
    assert metrics.max_drawdown_percent == Decimal("1.00")
    # (10400 / 10000)^(365.25 / 90) - 1 = 17.2538 %.
    assert metrics.cagr_percent == Decimal("17.25")
    # Sample standard deviation 0.016415 * sqrt(252).
    assert metrics.annual_volatility_percent == Decimal("26.06")
    assert metrics.sharpe_ratio == Decimal("7.72")
    # DD = sqrt((0.01² + 0.01²) / 5).
    assert metrics.sortino_ratio == Decimal("20.04")
    # 17.2538 % / 1.00 %.
    assert metrics.calmar_ratio == Decimal("17.25")
    assert metrics.profit_factor == Decimal("1.88")
    assert metrics.average_win_usd == Decimal("98.00")
    assert metrics.average_win_percent == Decimal("9.80")
    assert metrics.average_loss_usd == Decimal("-52.00")
    # 3 of the 5 bar ends have a position.
    assert metrics.exposure_percent == Decimal("60.00")
    # Fills of 1000 + 1100 + 1000 + 950 = 4050, mean equity 10239, 90 / 365.25 years.
    assert metrics.turnover_per_year == Decimal("1.61")
    assert metrics.win_rate_percent == Decimal("50.00")
    assert metrics.missing_reasons == {}


def test_the_sortino_ratio_divides_the_losses_by_the_number_of_all_days() -> None:
    sortino_ratio = metrics_of(WORKED_CURVE, WORKED_TRADES).sortino_ratio

    # With only the 2 days with a loss in the divisor, the value would be 12.67.
    assert sortino_ratio == Decimal("20.04")
    assert sortino_ratio != Decimal("12.67")


def test_a_backtest_on_1_hour_bars_uses_daily_returns() -> None:
    hourly_curve = [
        EquityPoint(time_utc=point.time_utc - timedelta(hours=hours_before), equity_usd=equity)
        for point in WORKED_CURVE
        for hours_before, equity in ((2, Decimal(9000)), (1, Decimal(11000)), (0, point.equity_usd))
    ]

    metrics = metrics_of(hourly_curve, WORKED_TRADES)

    # Only the last point of each day counts: the same values as with daily bars.
    assert (metrics.annual_volatility_percent, metrics.sharpe_ratio, metrics.sortino_ratio) == (
        Decimal("26.06"),
        Decimal("7.72"),
        Decimal("20.04"),
    )


def test_fewer_than_2_daily_returns_give_no_ratio_metrics() -> None:
    metrics = metrics_of(daily_curve("10100"))

    assert (metrics.annual_volatility_percent, metrics.sharpe_ratio, metrics.sortino_ratio) == (None, None, None)
    assert metrics.missing_reasons["sharpe_ratio"] == "Fewer than 2 daily returns"
    assert metrics.missing_reasons["sortino_ratio"] == "Fewer than 2 daily returns"
    assert metrics.missing_reasons["annual_volatility_percent"] == "Fewer than 2 daily returns"


def test_a_standard_deviation_of_0_gives_no_ratio_metrics() -> None:
    metrics = metrics_of(daily_curve("10000", "10000", "10000"))

    assert metrics.annual_volatility_percent == Decimal("0.00")
    assert (metrics.sharpe_ratio, metrics.sortino_ratio) == (None, None)
    assert metrics.missing_reasons["sharpe_ratio"] == "The standard deviation of the daily returns is 0"
    assert metrics.missing_reasons["sortino_ratio"] == "The standard deviation of the daily returns is 0"


def test_a_range_shorter_than_90_days_gives_no_cagr_and_no_calmar_ratio() -> None:
    metrics = metrics_of(WORKED_CURVE, WORKED_TRADES, RANGE_OF_89_DAYS)

    assert (metrics.cagr_percent, metrics.calmar_ratio) == (None, None)
    assert metrics.missing_reasons["cagr_percent"] == "The range is shorter than 90 days"
    assert metrics.missing_reasons["calmar_ratio"] == "The range is shorter than 90 days"


def test_a_max_drawdown_of_0_gives_no_calmar_ratio() -> None:
    metrics = metrics_of(daily_curve("10100", "10200", "10300"))

    assert metrics.cagr_percent is not None
    assert metrics.calmar_ratio is None
    assert metrics.missing_reasons["calmar_ratio"] == "The max drawdown is 0"


def test_no_round_trip_with_a_loss_gives_no_profit_factor() -> None:
    metrics = metrics_of(WORKED_CURVE, WORKED_TRADES[:2])

    assert metrics.profit_factor is None
    assert metrics.average_loss_usd is None
    assert metrics.missing_reasons["profit_factor"] == "No round trip with a loss"
    assert metrics.missing_reasons["average_loss_usd"] == "No round trip with a loss"
    assert metrics.win_rate_percent == Decimal("100.00")


def test_no_round_trip_gives_no_round_trip_metrics() -> None:
    metrics = metrics_of(WORKED_CURVE, [])

    assert (metrics.win_rate_percent, metrics.profit_factor, metrics.average_win_usd) == (None, None, None)
    assert metrics.missing_reasons["win_rate_percent"] == "No round trips"
    assert metrics.missing_reasons["average_win_percent"] == "No round trips"
    assert metrics.exposure_percent == Decimal("0.00")
    assert metrics.turnover_per_year == Decimal("0.00")
