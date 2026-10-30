"""The metric functions: the equity curve and the metrics of a backtest, from its bars and trades.

Forward tests use the same functions, so that a forward test and a backtest compare with the same metrics.
"""

import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from atrade.foundation.bar import Bar, BarPeriod, TimeRange

PERCENT = Decimal(100)
PERCENT_STEP = Decimal("0.01")
# Section 10.9.1: the annual factor A. The risk-free rate is 0.
ANNUAL_FACTOR = Decimal(252)
DAYS_PER_YEAR = Decimal("365.25")
SECONDS_PER_YEAR = DAYS_PER_YEAR * 24 * 60 * 60
MIN_DAILY_RETURNS = 2
# Section 10.9.3: a shorter range has no CAGR and no Calmar ratio.
MIN_CAGR_DAYS = 90


def round_value(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_STEP)


@dataclass(frozen=True)
class BacktestTrade:
    """One fill of an order. A backtest converts the prices and commissions of an instrument that is not in USD to USD
    at the fill time (docs/architecture/backtest.md section 10.8)."""

    time_utc: datetime
    side: Literal["BUY", "SELL"]
    quantity_shares: Decimal
    price_usd: Decimal
    commission_usd: Decimal


@dataclass(frozen=True)
class EquityPoint:
    """The cash plus the value of the position at the bar close price, at the end of one bar."""

    time_utc: datetime
    equity_usd: Decimal


@dataclass(frozen=True)
class BacktestMetrics:
    """The metrics of a test (docs/architecture/backtest.md section 10.9.2). A metric without a meaning is None
    (section 10.9.3), and `missing_reasons` gives the reason. Percents and money have 2 decimal places, ratios too."""

    final_equity_usd: Decimal
    total_return_percent: Decimal
    max_drawdown_percent: Decimal
    trade_count: int
    cagr_percent: Decimal | None
    annual_volatility_percent: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    calmar_ratio: Decimal | None
    profit_factor: Decimal | None
    average_win_usd: Decimal | None
    average_win_percent: Decimal | None
    average_loss_usd: Decimal | None
    exposure_percent: Decimal | None
    turnover_per_year: Decimal | None
    win_rate_percent: Decimal | None

    @property
    def missing_reasons(self) -> dict[str, str]:
        """The reason of each metric that is None, by its field name. The reasons come from the other values, so a
        saved backtest gives the same reasons as a new calculation."""
        return find_missing_reasons(self)


def calculate_equity_curve(
    *, start_cash: Decimal, bars: list[Bar], bar_period: BarPeriod, trades: list[BacktestTrade]
) -> list[EquityPoint]:
    """Returns one point at the end of each bar. A trade counts in the first point at or after its time.

    `start_cash`, the trade prices, and the bar prices must be in one currency. The points are in that currency.
    """
    sorted_trades = sorted(trades, key=lambda trade: trade.time_utc)
    cash = start_cash
    position_shares = Decimal(0)
    next_trade_index = 0
    equity_curve: list[EquityPoint] = []
    for bar in bars:
        bar_end_utc = bar.start_utc + bar_period.length
        while next_trade_index < len(sorted_trades) and sorted_trades[next_trade_index].time_utc <= bar_end_utc:
            trade = sorted_trades[next_trade_index]
            signed_shares = trade.quantity_shares if trade.side == "BUY" else -trade.quantity_shares
            cash -= signed_shares * trade.price_usd + trade.commission_usd
            position_shares += signed_shares
            next_trade_index += 1
        equity_curve.append(EquityPoint(time_utc=bar_end_utc, equity_usd=cash + position_shares * bar.close))
    return equity_curve


def calculate_daily_returns(*, start_capital_usd: Decimal, equity_curve: list[EquityPoint]) -> list[Decimal]:
    """The change of the last equity point of each trading day from the last point of the trading day before, as a
    fraction (0.02 is 2 %). The first trading day uses `start_capital_usd`. A trading day is a UTC date. A day after
    an equity of 0 has no return, because the change from 0 has no value.
    """
    last_equity_by_day: dict[date, Decimal] = {}
    for point in sorted(equity_curve, key=lambda point: point.time_utc):
        last_equity_by_day[point.time_utc.astimezone(UTC).date()] = point.equity_usd
    daily_returns: list[Decimal] = []
    equity_before_usd = start_capital_usd
    for equity_usd in last_equity_by_day.values():
        if equity_before_usd != 0:
            daily_returns.append(equity_usd / equity_before_usd - 1)
        equity_before_usd = equity_usd
    return daily_returns


@dataclass(frozen=True)
class RoundTrip:
    """The fills from a position of 0 back to a position of 0. `profit_usd` is after commissions. `entry_amount_usd`
    is the amount of the fills on the side of the first fill."""

    start_utc: datetime
    end_utc: datetime
    profit_usd: Decimal
    entry_amount_usd: Decimal


def find_round_trips(trades: list[BacktestTrade]) -> list[RoundTrip]:
    """The round trips that ended. A position that is still open at the last fill is not a round trip."""
    round_trips: list[RoundTrip] = []
    position_shares = Decimal(0)
    cash_usd = Decimal(0)
    entry_amount_usd = Decimal(0)
    entry_side: str | None = None
    start_utc: datetime | None = None
    for trade in sorted(trades, key=lambda trade: trade.time_utc):
        if start_utc is None:
            start_utc = trade.time_utc
            entry_side = trade.side
        amount_usd = trade.quantity_shares * trade.price_usd
        if trade.side == entry_side:
            entry_amount_usd += amount_usd
        cash_usd += (-amount_usd if trade.side == "BUY" else amount_usd) - trade.commission_usd
        position_shares += trade.quantity_shares if trade.side == "BUY" else -trade.quantity_shares
        if position_shares == 0:
            round_trips.append(
                RoundTrip(
                    start_utc=start_utc,
                    end_utc=trade.time_utc,
                    profit_usd=cash_usd,
                    entry_amount_usd=entry_amount_usd,
                )
            )
            cash_usd = Decimal(0)
            entry_amount_usd = Decimal(0)
            start_utc = None
    return round_trips


def calculate_max_drawdown_percent(*, paper_capital_usd: Decimal, equity_curve: list[EquityPoint]) -> Decimal:
    """The largest fall from a peak, as a percent of that peak, not rounded. The paper capital is the first peak."""
    peak_usd = paper_capital_usd
    max_drawdown_percent = Decimal(0)
    for point in equity_curve:
        peak_usd = max(peak_usd, point.equity_usd)
        drawdown_percent = (peak_usd - point.equity_usd) / peak_usd * PERCENT
        max_drawdown_percent = max(max_drawdown_percent, drawdown_percent)
    return max_drawdown_percent


@dataclass(frozen=True)
class RatioMetrics:
    annual_volatility_percent: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None


def calculate_ratio_metrics(daily_returns: list[Decimal]) -> RatioMetrics:
    """The annual volatility, the Sharpe ratio, and the Sortino ratio (Sortino and Price 1994: `n` is all days)."""
    if len(daily_returns) < MIN_DAILY_RETURNS:
        return RatioMetrics()
    standard_deviation = statistics.stdev(daily_returns)
    annual_volatility_percent = round_value(standard_deviation * ANNUAL_FACTOR.sqrt() * PERCENT)
    if standard_deviation == 0:
        return RatioMetrics(annual_volatility_percent=annual_volatility_percent)
    mean_return = statistics.mean(daily_returns)
    downside_deviation = (
        sum((min(Decimal(0), daily_return) ** 2 for daily_return in daily_returns), Decimal(0)) / len(daily_returns)
    ).sqrt()
    return RatioMetrics(
        annual_volatility_percent=annual_volatility_percent,
        sharpe_ratio=round_value(mean_return / standard_deviation * ANNUAL_FACTOR.sqrt()),
        sortino_ratio=(
            None if downside_deviation == 0 else round_value(mean_return / downside_deviation * ANNUAL_FACTOR.sqrt())
        ),
    )


def calculate_cagr_percent(*, paper_capital_usd: Decimal, final_equity_usd: Decimal, years: Decimal) -> Decimal | None:
    if years * DAYS_PER_YEAR < MIN_CAGR_DAYS or final_equity_usd <= 0:
        return None
    return ((final_equity_usd / paper_capital_usd) ** (1 / years) - 1) * PERCENT


@dataclass(frozen=True)
class RoundTripMetrics:
    win_rate_percent: Decimal | None = None
    profit_factor: Decimal | None = None
    average_win_usd: Decimal | None = None
    average_win_percent: Decimal | None = None
    average_loss_usd: Decimal | None = None


def calculate_round_trip_metrics(round_trips: list[RoundTrip]) -> RoundTripMetrics:
    if not round_trips:
        return RoundTripMetrics()
    wins = [round_trip for round_trip in round_trips if round_trip.profit_usd > 0]
    losses = [round_trip for round_trip in round_trips if round_trip.profit_usd < 0]
    total_win_usd = sum((win.profit_usd for win in wins), Decimal(0))
    total_loss_usd = sum((loss.profit_usd for loss in losses), Decimal(0))
    return RoundTripMetrics(
        win_rate_percent=round_value(Decimal(len(wins)) / len(round_trips) * PERCENT),
        profit_factor=None if not losses else round_value(total_win_usd / abs(total_loss_usd)),
        average_win_usd=None if not wins else round_value(total_win_usd / len(wins)),
        average_win_percent=(
            None
            if not wins
            else round_value(statistics.mean(win.profit_usd / win.entry_amount_usd for win in wins) * PERCENT)
        ),
        average_loss_usd=None if not losses else round_value(total_loss_usd / len(losses)),
    )


def find_positions(equity_curve: list[EquityPoint], trades: list[BacktestTrade]) -> list[bool]:
    """For each equity point (sorted by time): True when the position at the bar end is not 0. A trade counts at the
    first point at or after its time, as in `calculate_equity_curve`."""
    sorted_trades = sorted(trades, key=lambda trade: trade.time_utc)
    position_shares = Decimal(0)
    next_trade_index = 0
    positions: list[bool] = []
    for point in sorted(equity_curve, key=lambda point: point.time_utc):
        while next_trade_index < len(sorted_trades) and sorted_trades[next_trade_index].time_utc <= point.time_utc:
            trade = sorted_trades[next_trade_index]
            position_shares += trade.quantity_shares if trade.side == "BUY" else -trade.quantity_shares
            next_trade_index += 1
        positions.append(position_shares != 0)
    return positions


def calculate_exposure_percent(positions: list[bool]) -> Decimal | None:
    """The share of the bars with a position that is not 0 at the bar end. There is one equity point for each bar."""
    if not positions:
        return None
    return round_value(Decimal(sum(positions)) / len(positions) * PERCENT)


def calculate_turnover_per_year(
    equity_curve: list[EquityPoint], trades: list[BacktestTrade], years: Decimal
) -> Decimal | None:
    """The amount of all fills, divided by the mean equity of all equity points, divided by `years`."""
    if not equity_curve or years <= 0:
        return None
    mean_equity_usd = statistics.mean(point.equity_usd for point in equity_curve)
    if mean_equity_usd <= 0:
        return None
    total_amount_usd = sum((trade.quantity_shares * trade.price_usd for trade in trades), Decimal(0))
    return round_value(total_amount_usd / mean_equity_usd / years)


def calculate_metrics(
    *,
    paper_capital_usd: Decimal,
    time_range: TimeRange,
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade],
) -> BacktestMetrics:
    """The metrics of a test from its equity curve (one point at the end of each bar) and its fills.

    `years` is the calendar time from `time_range.start_utc` to `time_range.end_utc`, divided by 365.25 days.
    """
    sorted_curve = sorted(equity_curve, key=lambda point: point.time_utc)
    return calculate_part_metrics(
        MetricPart(
            start_capital_usd=paper_capital_usd,
            time_range=time_range,
            equity_curve=sorted_curve,
            trades=trades,
            round_trips=find_round_trips(trades),
            positions=find_positions(sorted_curve, trades),
        )
    )


@dataclass(frozen=True)
class MetricPart:
    """A part of a test: all of it, or the in-sample or out-of-sample part (section 10.9.4). `equity_curve` is
    sorted by time. `positions` has one value for each equity point (`find_positions` on the full test)."""

    start_capital_usd: Decimal
    time_range: TimeRange
    equity_curve: list[EquityPoint]
    trades: list[BacktestTrade]
    round_trips: list[RoundTrip]
    positions: list[bool]


def calculate_part_metrics(part: MetricPart) -> BacktestMetrics:
    start_capital_usd = part.start_capital_usd
    final_equity_usd = start_capital_usd if not part.equity_curve else part.equity_curve[-1].equity_usd
    total_return_percent = (final_equity_usd - start_capital_usd) / start_capital_usd * PERCENT
    max_drawdown_percent = calculate_max_drawdown_percent(
        paper_capital_usd=start_capital_usd, equity_curve=part.equity_curve
    )
    time_range = part.time_range
    years = Decimal((time_range.end_utc - time_range.start_utc).total_seconds()) / SECONDS_PER_YEAR
    cagr_percent = calculate_cagr_percent(
        paper_capital_usd=start_capital_usd, final_equity_usd=final_equity_usd, years=years
    )
    ratio_metrics = calculate_ratio_metrics(
        calculate_daily_returns(start_capital_usd=start_capital_usd, equity_curve=part.equity_curve)
    )
    round_trip_metrics = calculate_round_trip_metrics(part.round_trips)
    return BacktestMetrics(
        final_equity_usd=final_equity_usd,
        total_return_percent=total_return_percent.quantize(PERCENT_STEP),
        max_drawdown_percent=round_value(max_drawdown_percent),
        trade_count=len(part.trades),
        cagr_percent=None if cagr_percent is None else round_value(cagr_percent),
        annual_volatility_percent=ratio_metrics.annual_volatility_percent,
        sharpe_ratio=ratio_metrics.sharpe_ratio,
        sortino_ratio=ratio_metrics.sortino_ratio,
        calmar_ratio=(
            None
            if cagr_percent is None or max_drawdown_percent == 0
            else round_value(cagr_percent / max_drawdown_percent)
        ),
        profit_factor=round_trip_metrics.profit_factor,
        average_win_usd=round_trip_metrics.average_win_usd,
        average_win_percent=round_trip_metrics.average_win_percent,
        average_loss_usd=round_trip_metrics.average_loss_usd,
        exposure_percent=calculate_exposure_percent(part.positions),
        turnover_per_year=calculate_turnover_per_year(part.equity_curve, part.trades, years),
        win_rate_percent=round_trip_metrics.win_rate_percent,
    )


def find_split_time(time_range: TimeRange, out_of_sample_share: int) -> datetime | None:
    """The start of the out-of-sample part: the last `out_of_sample_share` percent of the calendar time of the range
    (docs/architecture/backtest.md section 10.9.4). The time does not align to a bar end. None when the share is 0."""
    if out_of_sample_share == 0:
        return None
    length = time_range.end_utc - time_range.start_utc
    return time_range.start_utc + length * (100 - out_of_sample_share) / 100


@dataclass(frozen=True)
class SplitMetrics:
    in_sample: BacktestMetrics
    out_of_sample: BacktestMetrics


def calculate_split_metrics(
    *,
    paper_capital_usd: Decimal,
    time_range: TimeRange,
    equity_curve: list[EquityPoint],
    trades: list[BacktestTrade],
    split_time_utc: datetime,
) -> SplitMetrics:
    """The metrics of the in-sample part and of the out-of-sample part (section 10.9.4).

    An equity point or a fill at or before the split time is in sample. A round trip is in the part where it ends.
    The out-of-sample part starts with the equity of the last in-sample point, and with the position that is open
    at the split time. Its range goes from the split time to the end of the test.
    """
    sorted_curve = sorted(equity_curve, key=lambda point: point.time_utc)
    positions = find_positions(sorted_curve, trades)
    round_trips = find_round_trips(trades)
    in_sample_count = sum(point.time_utc <= split_time_utc for point in sorted_curve)
    in_sample = MetricPart(
        start_capital_usd=paper_capital_usd,
        time_range=TimeRange(start_utc=time_range.start_utc, end_utc=split_time_utc),
        equity_curve=sorted_curve[:in_sample_count],
        trades=[trade for trade in trades if trade.time_utc <= split_time_utc],
        round_trips=[round_trip for round_trip in round_trips if round_trip.end_utc <= split_time_utc],
        positions=positions[:in_sample_count],
    )
    out_of_sample = MetricPart(
        start_capital_usd=paper_capital_usd if in_sample_count == 0 else sorted_curve[in_sample_count - 1].equity_usd,
        time_range=TimeRange(start_utc=split_time_utc, end_utc=time_range.end_utc),
        equity_curve=sorted_curve[in_sample_count:],
        trades=[trade for trade in trades if trade.time_utc > split_time_utc],
        round_trips=[round_trip for round_trip in round_trips if round_trip.end_utc > split_time_utc],
        positions=positions[in_sample_count:],
    )
    return SplitMetrics(
        in_sample=calculate_part_metrics(in_sample), out_of_sample=calculate_part_metrics(out_of_sample)
    )


# The metrics of section 10.9.2 and the win rate. Backtests that ended before them have None for all of them.
NEW_METRIC_NAMES = (
    "cagr_percent",
    "annual_volatility_percent",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "profit_factor",
    "average_win_usd",
    "average_win_percent",
    "average_loss_usd",
    "exposure_percent",
    "turnover_per_year",
    "win_rate_percent",
)
NOT_CALCULATED = "The test has no equity points, or it ended before ATrade calculated this metric"
FEWER_THAN_2_DAILY_RETURNS = "Fewer than 2 daily returns"
NO_ROUND_TRIPS = "No round trips"


def find_ratio_reasons(metrics: BacktestMetrics) -> dict[str, str]:
    if metrics.annual_volatility_percent is None:
        return dict.fromkeys(("annual_volatility_percent", "sharpe_ratio", "sortino_ratio"), FEWER_THAN_2_DAILY_RETURNS)
    if metrics.sharpe_ratio is None:
        return dict.fromkeys(("sharpe_ratio", "sortino_ratio"), "The standard deviation of the daily returns is 0")
    if metrics.sortino_ratio is None:
        return {"sortino_ratio": "No daily return with a loss"}
    return {}


def find_cagr_reasons(metrics: BacktestMetrics) -> dict[str, str]:
    if metrics.cagr_percent is None:
        reason = (
            "The final equity is not above 0" if metrics.final_equity_usd <= 0 else "The range is shorter than 90 days"
        )
        return dict.fromkeys(("cagr_percent", "calmar_ratio"), reason)
    if metrics.calmar_ratio is None:
        return {"calmar_ratio": "The max drawdown is 0"}
    return {}


def find_round_trip_reasons(metrics: BacktestMetrics) -> dict[str, str]:
    if metrics.win_rate_percent is None:
        return dict.fromkeys(
            ("win_rate_percent", "profit_factor", "average_win_usd", "average_win_percent", "average_loss_usd"),
            NO_ROUND_TRIPS,
        )
    reasons: dict[str, str] = {}
    if metrics.average_win_usd is None:
        reasons.update(dict.fromkeys(("average_win_usd", "average_win_percent"), "No round trip with a profit"))
    if metrics.profit_factor is None:
        reasons.update(dict.fromkeys(("profit_factor", "average_loss_usd"), "No round trip with a loss"))
    return reasons


def find_missing_reasons(metrics: BacktestMetrics) -> dict[str, str]:
    """The reason of each metric that is None (docs/architecture/backtest.md section 10.9.3), by its field name."""
    if metrics.exposure_percent is None:
        return {name: NOT_CALCULATED for name in NEW_METRIC_NAMES if getattr(metrics, name) is None}
    reasons = {**find_ratio_reasons(metrics), **find_cagr_reasons(metrics), **find_round_trip_reasons(metrics)}
    if metrics.turnover_per_year is None:
        reasons["turnover_per_year"] = "The mean equity is not above 0, or the range has no length"
    return reasons
