"""The metric functions: the equity curve and the metrics of a backtest, from its bars and trades.

Forward tests use the same functions, so that a forward test and a backtest compare with the same metrics.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from atrade.foundation.bar import Bar, BarPeriod

PERCENT = Decimal(100)
PERCENT_STEP = Decimal("0.01")


@dataclass(frozen=True)
class BacktestTrade:
    """One fill of an order. Prices and commissions are in USD, because a backtest trades only USD instruments."""

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
    final_equity_usd: Decimal
    total_return_percent: Decimal
    max_drawdown_percent: Decimal
    trade_count: int


def calculate_equity_curve(
    *, paper_capital_usd: Decimal, bars: list[Bar], bar_period: BarPeriod, trades: list[BacktestTrade]
) -> list[EquityPoint]:
    """Returns one point at the end of each bar. A trade counts in the first point at or after its time."""
    sorted_trades = sorted(trades, key=lambda trade: trade.time_utc)
    cash_usd = paper_capital_usd
    position_shares = Decimal(0)
    next_trade_index = 0
    equity_curve: list[EquityPoint] = []
    for bar in bars:
        bar_end_utc = bar.start_utc + bar_period.length
        while next_trade_index < len(sorted_trades) and sorted_trades[next_trade_index].time_utc <= bar_end_utc:
            trade = sorted_trades[next_trade_index]
            signed_shares = trade.quantity_shares if trade.side == "BUY" else -trade.quantity_shares
            cash_usd -= signed_shares * trade.price_usd + trade.commission_usd
            position_shares += signed_shares
            next_trade_index += 1
        equity_curve.append(EquityPoint(time_utc=bar_end_utc, equity_usd=cash_usd + position_shares * bar.close))
    return equity_curve


def calculate_max_drawdown_percent(*, paper_capital_usd: Decimal, equity_curve: list[EquityPoint]) -> Decimal:
    """The largest fall from a peak, as a percent of that peak. The paper capital is the first peak."""
    peak_usd = paper_capital_usd
    max_drawdown_percent = Decimal(0)
    for point in equity_curve:
        peak_usd = max(peak_usd, point.equity_usd)
        drawdown_percent = (peak_usd - point.equity_usd) / peak_usd * PERCENT
        max_drawdown_percent = max(max_drawdown_percent, drawdown_percent)
    return max_drawdown_percent.quantize(PERCENT_STEP)


def calculate_metrics(
    *, paper_capital_usd: Decimal, equity_curve: list[EquityPoint], trade_count: int
) -> BacktestMetrics:
    final_equity_usd = paper_capital_usd if not equity_curve else equity_curve[-1].equity_usd
    total_return_percent = (final_equity_usd - paper_capital_usd) / paper_capital_usd * PERCENT
    return BacktestMetrics(
        final_equity_usd=final_equity_usd,
        total_return_percent=total_return_percent.quantize(PERCENT_STEP),
        max_drawdown_percent=calculate_max_drawdown_percent(
            paper_capital_usd=paper_capital_usd, equity_curve=equity_curve
        ),
        trade_count=trade_count,
    )
