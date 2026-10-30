"""The metrics of the in-sample part and of the out-of-sample part (docs/architecture/backtest.md section 10.9.4).

The expected values are calculated by hand from the definitions of section 10.9.2.
"""

from datetime import UTC, datetime
from decimal import Decimal

from atrade.backtest import calculate_split_metrics
from atrade.foundation.bar import TimeRange
from tests.backtest.test_performance_metrics import daily_curve, trade

PAPER_CAPITAL = Decimal(10000)
TEN_DAYS = TimeRange(start_utc=datetime(2026, 1, 1, tzinfo=UTC), end_utc=datetime(2026, 1, 11, tzinfo=UTC))
# 30 % of the 10 days: the out-of-sample part starts on January 8.
SPLIT_TIME = datetime(2026, 1, 8, tzinfo=UTC)
# Points at 21:00 UTC of January 5 to 10. The first 3 points are in sample.
CURVE = daily_curve("10200", "10098", "10300", "10197", "10400", "10192")
# A win of 98 that ends on January 6, and a loss of -52 that starts on January 7 and ends on January 9.
TRADES = [
    trade(5, "BUY", "10", "100"),
    trade(6, "SELL", "10", "110"),
    trade(7, "BUY", "10", "100"),
    trade(9, "SELL", "10", "95"),
]


def test_in_sample_part_has_the_metrics_of_the_points_and_fills_up_to_the_split_time() -> None:
    in_sample = calculate_split_metrics(
        paper_capital_usd=PAPER_CAPITAL,
        time_range=TEN_DAYS,
        equity_curve=CURVE,
        trades=TRADES,
        split_time_utc=SPLIT_TIME,
    ).in_sample

    assert in_sample.final_equity_usd == Decimal(10300)
    assert in_sample.total_return_percent == Decimal("3.00")
    assert in_sample.max_drawdown_percent == Decimal("1.00")
    assert in_sample.trade_count == 3
    # 7 days: shorter than 90 days.
    assert in_sample.cagr_percent is None
    assert in_sample.calmar_ratio is None
    # Daily returns 2 %, -1 %, 2.00040 %.
    assert in_sample.annual_volatility_percent == Decimal("27.50")
    assert in_sample.sharpe_ratio == Decimal("9.17")
    assert in_sample.sortino_ratio == Decimal("27.50")
    # Only the win ends in the in-sample part.
    assert in_sample.win_rate_percent == Decimal("100.00")
    assert in_sample.profit_factor is None
    assert in_sample.average_win_usd == Decimal("98.00")
    assert in_sample.average_win_percent == Decimal("9.80")
    assert in_sample.average_loss_usd is None
    # A position at the points of January 5 and 7.
    assert in_sample.exposure_percent == Decimal("66.67")
    # Fills of 3100, mean equity 10199.33, 7 / 365.25 years.
    assert in_sample.turnover_per_year == Decimal("15.86")


def test_out_of_sample_part_starts_with_the_last_in_sample_equity_and_the_open_position() -> None:
    out_of_sample = calculate_split_metrics(
        paper_capital_usd=PAPER_CAPITAL,
        time_range=TEN_DAYS,
        equity_curve=CURVE,
        trades=TRADES,
        split_time_utc=SPLIT_TIME,
    ).out_of_sample

    assert out_of_sample.final_equity_usd == Decimal(10192)
    # From 10300.
    assert out_of_sample.total_return_percent == Decimal("-1.05")
    # From the peak 10400 to 10192.
    assert out_of_sample.max_drawdown_percent == Decimal("2.00")
    assert out_of_sample.trade_count == 1
    # Daily returns -1 %, 1.99078 %, -2 %.
    assert out_of_sample.annual_volatility_percent == Decimal("32.96")
    assert out_of_sample.sharpe_ratio == Decimal("-2.57")
    assert out_of_sample.sortino_ratio == Decimal("-4.14")
    # The round trip of January 7 to 9 ends in the out-of-sample part.
    assert out_of_sample.win_rate_percent == Decimal("0.00")
    assert out_of_sample.profit_factor == Decimal("0.00")
    assert out_of_sample.average_win_usd is None
    assert out_of_sample.average_loss_usd == Decimal("-52.00")
    # The position from January 7 is open at the point of January 8.
    assert out_of_sample.exposure_percent == Decimal("33.33")
    # Fills of 950, mean equity 10263, 3 / 365.25 years.
    assert out_of_sample.turnover_per_year == Decimal("11.27")
