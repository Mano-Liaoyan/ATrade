"""foundation/order_ref: the format rule of the IBKR orderRef that tells the source of an order (section 12.9)."""

import pytest

from atrade.foundation.order_ref import (
    MANUAL_ORDER_REF,
    OrderSource,
    format_forward_test_order_tag,
    read_order_source,
)


def test_formats_the_forward_test_tag_with_the_forward_test_id() -> None:
    assert format_forward_test_order_tag(42) == "FT42"


@pytest.mark.parametrize(
    ("order_ref", "expected_source"),
    [
        # NautilusTrader writes the ClientOrderId into orderRef. The strategy tag is one part of it.
        ("O-20260102-030405-001-FT42-1", OrderSource(kind="forward_test", forward_test_id=42)),
        ("FT7", OrderSource(kind="forward_test", forward_test_id=7)),
        (MANUAL_ORDER_REF, OrderSource(kind="by_hand", forward_test_id=None)),
        ("", OrderSource(kind="by_hand", forward_test_id=None)),
        ("O-20260102-030405-001-FTX-1", OrderSource(kind="by_hand", forward_test_id=None)),
        ("SOFT42", OrderSource(kind="by_hand", forward_test_id=None)),
    ],
)
def test_reads_the_order_source_from_the_order_ref(order_ref: str, expected_source: OrderSource) -> None:
    assert read_order_source(order_ref) == expected_source
