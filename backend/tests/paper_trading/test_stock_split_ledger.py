"""The ledger change at a stock split and the evidence rules of the "Split check needed" state
(docs/architecture/paper_trading.md section 11.11). The examples are the 2 examples of the section."""

from decimal import Decimal

import pytest

from atrade.paper_trading import SplitAdjustment, SplitEvidence, calculate_split_adjustments, find_split_evidence
from atrade.paper_trading.owner_ledger_store import BY_HAND, Owner

FORWARD_TEST_A = Owner(kind="forward_test", forward_test_id=1)
FORWARD_TEST_B = Owner(kind="forward_test", forward_test_id=2)
SEVEN_THIRTEENTHS = Decimal(7) / Decimal(13)


def test_a_3_for_2_split_gives_whole_shares_cash_in_lieu_and_the_rest_to_by_hand() -> None:
    # Last close before the ex-date 30.00, so 1 new share is worth 20.00.
    adjustments = calculate_split_adjustments(
        owner_quantities={FORWARD_TEST_A: Decimal(3), FORWARD_TEST_B: Decimal(5)},
        split_ratio=Decimal("1.5"),
        account_quantity_after=Decimal(12),
        last_close_before_ex_date=Decimal(30),
    )

    assert adjustments == [
        SplitAdjustment(owner=FORWARD_TEST_A, quantity_change=Decimal(1), cash_in_lieu=Decimal(10), price=None),
        SplitAdjustment(owner=FORWARD_TEST_B, quantity_change=Decimal(2), cash_in_lieu=Decimal(10), price=None),
        SplitAdjustment(owner=BY_HAND, quantity_change=Decimal(1), cash_in_lieu=Decimal(-20), price=Decimal(20)),
    ]


def test_a_1_for_10_split_gives_cash_in_lieu_to_each_owner_and_1_share_to_by_hand() -> None:
    # Last close before the ex-date 5.00, so 1 new share is worth 50.00. IBKR pays cash in lieu for 0.2 share.
    adjustments = calculate_split_adjustments(
        owner_quantities={FORWARD_TEST_A: Decimal(15), FORWARD_TEST_B: Decimal(7)},
        split_ratio=Decimal("0.1"),
        account_quantity_after=Decimal(2),
        last_close_before_ex_date=Decimal(5),
    )

    assert adjustments == [
        SplitAdjustment(owner=FORWARD_TEST_A, quantity_change=Decimal(-14), cash_in_lieu=Decimal(25), price=None),
        SplitAdjustment(owner=FORWARD_TEST_B, quantity_change=Decimal(-7), cash_in_lieu=Decimal(35), price=None),
        SplitAdjustment(owner=BY_HAND, quantity_change=Decimal(1), cash_in_lieu=Decimal(-50), price=Decimal(50)),
    ]


def test_by_hand_that_holds_shares_gets_its_own_row_and_the_difference_row() -> None:
    adjustments = calculate_split_adjustments(
        owner_quantities={BY_HAND: Decimal(10)},
        split_ratio=Decimal(4),
        account_quantity_after=Decimal(40),
        last_close_before_ex_date=Decimal(400),
    )

    assert adjustments == [
        SplitAdjustment(owner=BY_HAND, quantity_change=Decimal(30), cash_in_lieu=Decimal(0), price=None),
    ]


@pytest.mark.parametrize(
    ("bar_ratio", "quantity_before", "quantity_after", "expected"),
    [
        (Decimal(4), Decimal(10), Decimal(40), SplitEvidence(kind="confirmed", ratio=Decimal(4))),
        (Decimal("0.1"), Decimal(22), Decimal(2), SplitEvidence(kind="confirmed", ratio=Decimal("0.1"))),
        (Decimal("1.5"), Decimal(8), Decimal(12), SplitEvidence(kind="confirmed", ratio=Decimal("1.5"))),
        (Decimal(4), Decimal(10), Decimal(10), SplitEvidence(kind="bar_ratio_only", ratio=Decimal(4))),
        (None, Decimal(10), Decimal(40), SplitEvidence(kind="position_only", ratio=Decimal(4))),
        (Decimal(4), Decimal(10), Decimal(20), SplitEvidence(kind="ratios_differ", ratio=Decimal(4))),
        (Decimal(4), Decimal(100), Decimal(399), SplitEvidence(kind="share_count_differs", ratio=Decimal(4))),
        (SEVEN_THIRTEENTHS, Decimal(13), Decimal(7), SplitEvidence(kind="unusual_ratio", ratio=SEVEN_THIRTEENTHS)),
        (None, Decimal(10), Decimal(10), None),
    ],
)
def test_the_evidence_gives_a_confirmed_split_or_the_reason_of_the_split_check(
    bar_ratio: Decimal | None, quantity_before: Decimal, quantity_after: Decimal, expected: SplitEvidence | None
) -> None:
    evidence = find_split_evidence(bar_ratio=bar_ratio, quantity_before=quantity_before, quantity_after=quantity_after)

    assert evidence == expected
