"""The fill table of the comparison of a forward test with a backtest of the same period
(docs/architecture/forward_test.md section 12.10). The metrics come from the metric functions of `backtest`.
"""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from atrade.backtest import BacktestTrade, EquityPoint

# The average price of more fills in one bar has many decimal places. IBKR prices have at most 4.
AVERAGE_PRICE_STEP = Decimal("0.0001")

type FillSide = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class FillTotal:
    quantity_shares: Decimal
    # The price of the one fill, or the average price weighted by the quantity.
    price_usd: Decimal


@dataclass(frozen=True)
class FillComparisonRow:
    bar_end_utc: datetime
    side: FillSide
    forward_test: FillTotal | None
    backtest: FillTotal | None
    # The forward test price minus the backtest price. None when one side has no fill.
    price_difference_usd: Decimal | None


def find_bar_end(bar_ends_utc: list[datetime], time_utc: datetime) -> datetime:
    """The last bar end at or before the time. A fill after a bar is the reaction of the strategy to that bar."""
    index = bisect_right(bar_ends_utc, time_utc)
    if index == 0:
        return bar_ends_utc[0] if bar_ends_utc else time_utc
    return bar_ends_utc[index - 1]


def sum_fills(trades: list[BacktestTrade]) -> FillTotal:
    quantity_shares = sum((trade.quantity_shares for trade in trades), Decimal(0))
    if len(trades) == 1:
        return FillTotal(quantity_shares=quantity_shares, price_usd=trades[0].price_usd)
    value_usd = sum((trade.quantity_shares * trade.price_usd for trade in trades), Decimal(0))
    return FillTotal(
        quantity_shares=quantity_shares, price_usd=(value_usd / quantity_shares).quantize(AVERAGE_PRICE_STEP)
    )


def group_fills(
    trades: list[BacktestTrade], bar_ends_utc: list[datetime]
) -> dict[tuple[datetime, FillSide], FillTotal]:
    grouped_trades: dict[tuple[datetime, FillSide], list[BacktestTrade]] = {}
    for trade in trades:
        key = (find_bar_end(bar_ends_utc, trade.time_utc), trade.side)
        grouped_trades.setdefault(key, []).append(trade)
    return {key: sum_fills(group) for key, group in grouped_trades.items()}


def compare_fills(
    *,
    forward_test_fills: list[BacktestTrade],
    backtest_fills: list[BacktestTrade],
    equity_curves: list[list[EquityPoint]],
) -> list[FillComparisonRow]:
    """One row for each bar and side with a fill on at least one side, in time order."""
    bar_ends_utc = sorted({point.time_utc for curve in equity_curves for point in curve})
    forward_test_totals = group_fills(forward_test_fills, bar_ends_utc)
    backtest_totals = group_fills(backtest_fills, bar_ends_utc)
    rows: list[FillComparisonRow] = []
    for bar_end_utc, side in sorted(forward_test_totals.keys() | backtest_totals.keys()):
        forward_test_total = forward_test_totals.get((bar_end_utc, side))
        backtest_total = backtest_totals.get((bar_end_utc, side))
        price_difference_usd = None
        if forward_test_total is not None and backtest_total is not None:
            price_difference_usd = forward_test_total.price_usd - backtest_total.price_usd
        rows.append(
            FillComparisonRow(
                bar_end_utc=bar_end_utc,
                side=side,
                forward_test=forward_test_total,
                backtest=backtest_total,
                price_difference_usd=price_difference_usd,
            )
        )
    return rows
