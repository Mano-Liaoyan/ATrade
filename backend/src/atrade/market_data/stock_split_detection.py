"""Stock split detection of the Databento import (docs/architecture/market_data.md section 8.8.3).

Databento prices are not adjusted. IBKR adjusts its TRADES bars for stock splits. The split ratio is the number of
new shares for 1 old share: after the ex-date, the price is the old price divided by the split ratio.
"""

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

# A change of the close ratio above this part is a step. The IBKR close and the official close can differ by about
# 1% (section 8.8.2), and a bonus issue of 1 new share for 10 shares changes the ratio by 10%.
RATIO_STEP_TOLERANCE = Decimal("0.03")
# A split ratio is a fraction with a small denominator. The search accepts the first fraction this near.
SPLIT_RATIO_TOLERANCE = Fraction(2, 100)
MAX_SPLIT_RATIO_DENOMINATOR = 50
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
    """The fraction with the smallest denominator near the raw ratio, for example 2 for 2.004 and 11/10 for 1.098."""
    exact_ratio = Fraction(raw_ratio)
    for max_denominator in range(1, MAX_SPLIT_RATIO_DENOMINATOR + 1):
        ratio = exact_ratio.limit_denominator(max_denominator)
        if ratio > 0 and abs(ratio / exact_ratio - 1) <= SPLIT_RATIO_TOLERANCE:
            return ratio
    return exact_ratio.limit_denominator(MAX_SPLIT_RATIO_DENOMINATOR)


def find_splits_from_ibkr_closes(
    databento_prices: Sequence[DailyPrices], ibkr_closes: dict[date, Decimal]
) -> list[FoundSplit]:
    """Instruments that still trade. On each day of the overlap, the ratio is the Databento close divided by the IBKR
    close. A constant ratio means no stock split. A step from one day to the next is a stock split on the second day."""
    splits: list[FoundSplit] = []
    previous_ratio: Decimal | None = None
    for prices in databento_prices:
        ibkr_close = ibkr_closes.get(prices.day)
        if ibkr_close is None or ibkr_close <= 0 or prices.close <= 0:
            continue
        ratio = prices.close / ibkr_close
        if previous_ratio is not None and abs(ratio / previous_ratio - 1) > RATIO_STEP_TOLERANCE:
            split_ratio = find_split_ratio(previous_ratio / ratio)
            splits.append(FoundSplit(ex_date=prices.day, split_ratio=to_decimal(split_ratio)))
        previous_ratio = ratio
    return splits


def find_common_ratio(raw_ratio: Decimal) -> Fraction | None:
    exact_ratio = Fraction(raw_ratio)
    for ratio in COMMON_SPLIT_RATIOS:
        if abs(exact_ratio / ratio - 1) <= Fraction(RATIO_STEP_TOLERANCE):
            return ratio
    return None


def find_splits_by_detection_rule(databento_prices: Sequence[DailyPrices]) -> list[FoundSplit]:
    """Instruments that stopped trading. The close of one day divided by the open of the next day is near a common
    split ratio, and the volume changes in the opposite direction of the price."""
    splits: list[FoundSplit] = []
    for prices, next_prices in itertools.pairwise(databento_prices):
        if next_prices.open <= 0:
            continue
        ratio = find_common_ratio(prices.close / next_prices.open)
        if ratio is None:
            continue
        volume_goes_up = next_prices.volume > prices.volume
        if volume_goes_up == (ratio > 1):
            splits.append(FoundSplit(ex_date=next_prices.day, split_ratio=to_decimal(ratio)))
    return splits
