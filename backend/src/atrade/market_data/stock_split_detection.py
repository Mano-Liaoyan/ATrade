"""Stock split detection of the Databento import (docs/architecture/market_data.md section 8.8.3).

Databento prices are not adjusted. IBKR adjusts its TRADES bars for stock splits. The split ratio is the number of
new shares for 1 old share: after the ex-date, the price is the old price divided by the split ratio.
"""

import itertools
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

from atrade.market_data.us_trading_days import find_previous_trading_day

# A change of the close ratio above this part is a step. The IBKR close and the official close can differ by about
# 1% (section 8.8.2), and a bonus issue of 1 new share for 10 shares changes the ratio by 10%.
RATIO_STEP_TOLERANCE = Decimal("0.03")
# A split ratio is a fraction with a small denominator. The search accepts the first fraction this near.
SPLIT_RATIO_TOLERANCE = Fraction(2, 100)
MAX_SPLIT_RATIO_DENOMINATOR = 50
# A step of the close ratio compares the median ratio of up to this count of days before the step with the median
# ratio of up to this count of days from the step on.
STEP_WINDOW_DAYS = 10
# The split ratios of a step, above 1, besides the whole numbers. Their inverses are reverse splits.
STEP_SPLIT_FRACTIONS = tuple(Fraction(ratio) for ratio in ("3/2", "4/3", "5/4", "5/2", "5/3"))
STEP_SPLIT_RATIO_TOLERANCE = Fraction(4, 100)
# Before and after a stock split, the close ratio is flat: at least this part of the ratios of each window is within
# RATIO_STEP_TOLERANCE of the median of the window. The ratio of closes with much noise, or of 2 different stocks with
# the same symbol, is not flat.
FLAT_WINDOW_PART = Decimal("0.8")
# The Databento evidence of a stock split: the close of the day before the ex-date divided by the open of the ex-date
# is near the split ratio. The price can move on the ex-date, so the tolerance is 20%, but at most half of the
# distance from the split ratio to 1 (in log), so a 5-for-4 split needs a gap nearer to 5/4 than to 1.
PRICE_GAP_TOLERANCE = math.log(1.2)
# The detection rule accepts only these split ratios, so a large price gap of a normal day is not a stock split.
COMMON_SPLIT_RATIOS = tuple(
    Fraction(ratio) for ratio in ("3/2", "2", "3", "4", "5", "10", "1/2", "1/3", "1/4", "1/5", "1/10", "1/20")
)


@dataclass(frozen=True)
class DailyPrices:
    day: date
    open: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class FoundSplit:
    ex_date: date
    split_ratio: Decimal


def to_decimal(ratio: Fraction) -> Decimal:
    return Decimal(ratio.numerator) / Decimal(ratio.denominator)


def find_split_ratio(raw_ratio: Decimal) -> Fraction:
    """The fraction with the smallest denominator near the raw ratio, for example 2 for 2.004 and 11/10 for 1.098.
    Below 1, the inverse of the split ratio of the inverse, for example 1/150 for 0.00667 (a reverse split). Thus
    the result is never 0."""
    if raw_ratio < 1:
        return 1 / find_split_ratio(1 / raw_ratio)
    exact_ratio = Fraction(raw_ratio)
    for max_denominator in range(1, MAX_SPLIT_RATIO_DENOMINATOR + 1):
        ratio = exact_ratio.limit_denominator(max_denominator)
        if ratio > 0 and abs(ratio / exact_ratio - 1) <= SPLIT_RATIO_TOLERANCE:
            return ratio
    return exact_ratio.limit_denominator(MAX_SPLIT_RATIO_DENOMINATOR)


def find_step_split_ratio(raw_ratio: Decimal) -> Fraction | None:
    """The split ratio of a lasting step of the close ratio: a whole number n or 1/n (n at least 2), or one of
    STEP_SPLIT_FRACTIONS or its inverse, within STEP_SPLIT_RATIO_TOLERANCE. None for another step, for example a
    difference of the closes of a stock with few trades."""
    ratio_above_1 = Fraction(raw_ratio) if raw_ratio >= 1 else 1 / Fraction(raw_ratio)
    candidates = [Fraction(round(ratio_above_1)), *STEP_SPLIT_FRACTIONS]
    for candidate in candidates:
        if candidate > 1 and abs(ratio_above_1 / candidate - 1) <= STEP_SPLIT_RATIO_TOLERANCE:
            return candidate if raw_ratio >= 1 else 1 / candidate
    return None


def is_flat(ratios: Sequence[Decimal]) -> bool:
    median = statistics.median(ratios)
    near_count = sum(1 for ratio in ratios if abs(ratio / median - 1) <= RATIO_STEP_TOLERANCE)
    return near_count >= FLAT_WINDOW_PART * len(ratios)


def find_splits_from_ibkr_closes(
    databento_prices: Sequence[DailyPrices], ibkr_closes: dict[date, Decimal]
) -> list[FoundSplit]:
    """Instruments that still trade. On each day of the overlap, the ratio is the Databento close divided by the IBKR
    close. A constant ratio means no stock split. A stock split is a lasting step: the median ratio of the days before
    the step divided by the median ratio of the days from the step on is a split ratio (`find_step_split_ratio`), and the ratio is flat before and after the step (`is_flat`). The
    two closes of a stock with few trades can differ by some percent on many days. Such differences change the
    medians only a little, so they are not a stock split."""
    days: list[date] = []
    ratios: list[Decimal] = []
    for prices in databento_prices:
        ibkr_close = ibkr_closes.get(prices.day)
        if ibkr_close is None or ibkr_close <= 0 or prices.close <= 0:
            continue
        days.append(prices.day)
        ratios.append(prices.close / ibkr_close)

    def find_change(index: int) -> float:
        return abs(math.log(ratios[index - 1] / ratios[index]))

    splits: list[FoundSplit] = []
    next_index = 1
    for index in range(1, len(ratios)):
        if index < next_index or abs(ratios[index] / ratios[index - 1] - 1) <= RATIO_STEP_TOLERANCE:
            continue
        # The step is the largest change of the days around it. A small difference of the closes some days before a
        # stock split is not the step: its windows hold both levels.
        nearby = range(max(1, index - STEP_WINDOW_DAYS + 1), min(index + STEP_WINDOW_DAYS, len(ratios)))
        if max(nearby, key=find_change) != index:
            continue
        ratios_before = ratios[max(0, index - STEP_WINDOW_DAYS) : index]
        ratios_after = ratios[index : index + STEP_WINDOW_DAYS]
        if not (is_flat(ratios_before) and is_flat(ratios_after)):
            continue
        split_ratio = find_step_split_ratio(statistics.median(ratios_before) / statistics.median(ratios_after))
        if split_ratio is None:
            continue
        splits.append(FoundSplit(ex_date=days[index], split_ratio=to_decimal(split_ratio)))
        # The days after the step hold the new ratio. They are not a second step.
        next_index = index + STEP_WINDOW_DAYS
    return splits


def has_price_gap(databento_prices: Sequence[DailyPrices], split: FoundSplit) -> bool:
    """True when the Databento prices, before any adjustment of this stock split, show the gap of the stock split on
    its ex-date. An IBKR close ratio step without this gap is not proven: the IBKR data can have an error."""
    index = next((index for index, prices in enumerate(databento_prices) if prices.day == split.ex_date), None)
    if index is None or index == 0:
        return False
    close_before = databento_prices[index - 1].close
    open_on_ex_date = databento_prices[index].open
    if close_before <= 0 or open_on_ex_date <= 0:
        return False
    split_distance = abs(math.log(split.split_ratio))
    gap_distance = abs(math.log(close_before / open_on_ex_date / split.split_ratio))
    return gap_distance <= min(PRICE_GAP_TOLERANCE, split_distance / 2)


def find_common_ratio(raw_ratio: Decimal) -> Fraction | None:
    exact_ratio = Fraction(raw_ratio)
    for ratio in COMMON_SPLIT_RATIOS:
        if abs(exact_ratio / ratio - 1) <= Fraction(RATIO_STEP_TOLERANCE):
            return ratio
    return None


def find_splits_by_detection_rule(
    databento_prices: Sequence[DailyPrices], *, skip_missing_days: bool = False
) -> list[FoundSplit]:
    """Instruments that stopped trading. The close of one day divided by the open of the next day is near a common
    split ratio, and the volume changes in the opposite direction of the price.

    `skip_missing_days`: for stored prices, which have no days with price 0 (section 8.8.2). A pair of days with a
    weekday between them is not compared. The calendar does not know all holidays, so the rule also does not compare
    the 2 days around a holiday in the week."""
    splits: list[FoundSplit] = []
    for prices, next_prices in itertools.pairwise(databento_prices):
        if next_prices.open <= 0:
            continue
        if skip_missing_days and find_previous_trading_day(next_prices.day) != prices.day:
            continue
        ratio = find_common_ratio(prices.close / next_prices.open)
        if ratio is None:
            continue
        volume_goes_up = next_prices.volume > prices.volume
        if volume_goes_up == (ratio > 1):
            splits.append(FoundSplit(ex_date=next_prices.day, split_ratio=to_decimal(ratio)))
    return splits
