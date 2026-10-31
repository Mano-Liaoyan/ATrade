"""The ledger change at a stock split and the evidence rules of the "Split check needed" state
(docs/architecture/paper_trading.md sections 11.11 and 11.13). No database and no IBKR.

- Each owner gets the whole part of old shares times the split ratio and keeps its total cost. The part below 1 share
  is cash in lieu at the last close before the ex-date divided by the split ratio.
- The difference between the IBKR position and the sum of the new owner positions goes to "By hand" as one more row,
  with the share price as `price`: it is like a buy of the shares, so its average cost includes them. The cash in
  lieu of IBKR is the part below 1 share of the account position times the split ratio (ATrade does not read it).
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from atrade.paper_trading.owner_ledger_store import BY_HAND, Owner

# 2 ratios agree when they differ by this part or less: the step tolerance of evidence A
# (docs/architecture/market_data.md section 8.14).
RATIO_TOLERANCE = Fraction(3, 100)
# A usual split ratio: a whole number, 1 divided by a whole number, or a fraction like 3/2 or 11/10.
MAX_USUAL_NUMERATOR = 20
MAX_USUAL_DENOMINATOR = 10
# A ratio from decimal text has a small denominator.
MAX_RATIO_DENOMINATOR = 1000

type SplitCheckEvidence = Literal[
    "bar_ratio_only", "position_only", "ratios_differ", "share_count_differs", "unusual_ratio"
]


@dataclass(frozen=True)
class SplitAdjustment:
    """One `split_adjustment` row. `cash_in_lieu` is in the currency of the instrument. `price` is set only on the
    difference row of "By hand"."""

    owner: Owner
    quantity_change: Decimal
    cash_in_lieu: Decimal
    price: Decimal | None


@dataclass(frozen=True)
class SplitEvidence:
    kind: Literal["confirmed"] | SplitCheckEvidence
    ratio: Decimal


def find_whole_and_part(quantity: Decimal) -> tuple[Decimal, Decimal]:
    whole = Decimal(math.floor(quantity))
    return whole, quantity - whole


def calculate_split_adjustments(
    *,
    owner_quantities: dict[Owner, Decimal],
    split_ratio: Decimal,
    account_quantity_after: Decimal,
    last_close_before_ex_date: Decimal,
) -> list[SplitAdjustment]:
    """The rows of section 11.11 for the owners that hold the instrument, in the order of `owner_quantities`."""
    share_price = last_close_before_ex_date / split_ratio
    adjustments: list[SplitAdjustment] = []
    new_quantity_sum = Decimal(0)
    part_sum = Decimal(0)
    for owner, quantity in owner_quantities.items():
        new_quantity, part = find_whole_and_part(quantity * split_ratio)
        new_quantity_sum += new_quantity
        part_sum += part
        adjustments.append(
            SplitAdjustment(
                owner=owner,
                quantity_change=new_quantity - quantity,
                cash_in_lieu=part * share_price,
                price=None,
            )
        )
    _, account_part = find_whole_and_part(sum(owner_quantities.values(), Decimal(0)) * split_ratio)
    difference = account_quantity_after - new_quantity_sum
    cash_difference = (account_part - part_sum) * share_price
    if difference != 0 or cash_difference != 0:
        adjustments.append(
            SplitAdjustment(owner=BY_HAND, quantity_change=difference, cash_in_lieu=cash_difference, price=share_price)
        )
    return adjustments


def to_fraction(ratio: Decimal) -> Fraction:
    return Fraction(ratio).limit_denominator(MAX_RATIO_DENOMINATOR)


def is_usual_ratio(ratio: Decimal) -> bool:
    fraction = to_fraction(ratio)
    return (
        fraction.numerator == 1
        or fraction.denominator == 1
        or (fraction.numerator <= MAX_USUAL_NUMERATOR and fraction.denominator <= MAX_USUAL_DENOMINATOR)
    )


def find_split_evidence(
    *, bar_ratio: Decimal | None, quantity_before: Decimal, quantity_after: Decimal
) -> SplitEvidence | None:
    """Compares evidence A (`bar_ratio`, None when the bars show no stock split) with evidence B (the IBKR position
    `quantity_after` divided by the sum of the owner positions `quantity_before`). None: no stock split.

    `quantity_before` must be above 0. An instrument that no owner holds has no evidence B.
    """
    if bar_ratio is None:
        if quantity_after == quantity_before:
            return None
        position_ratio = Fraction(quantity_after) / Fraction(quantity_before)
        return SplitEvidence(
            kind="position_only", ratio=Decimal(position_ratio.numerator) / Decimal(position_ratio.denominator)
        )
    if quantity_after == quantity_before:
        return SplitEvidence(kind="bar_ratio_only", ratio=bar_ratio)
    if not is_usual_ratio(bar_ratio):
        return SplitEvidence(kind="unusual_ratio", ratio=bar_ratio)
    if quantity_after == math.floor(quantity_before * bar_ratio):
        return SplitEvidence(kind="confirmed", ratio=bar_ratio)
    position_ratio = Fraction(quantity_after) / Fraction(quantity_before)
    if abs(position_ratio / to_fraction(bar_ratio) - 1) <= RATIO_TOLERANCE:
        return SplitEvidence(kind="share_count_differs", ratio=bar_ratio)
    return SplitEvidence(kind="ratios_differ", ratio=bar_ratio)
