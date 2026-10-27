"""The format rule of the IBKR orderRef, which tells the source of an order (docs/architecture.md section 12.9).

A forward test sets the NautilusTrader `order_id_tag` to `FT<forward test ID>`. The IB execution client writes the
ClientOrderId, for example `O-20260102-030405-001-FT42-1`, into orderRef. `forward_test` writes the tag.
`paper_trading` reads it. Orders that ATrade sends by hand have the orderRef `MANUAL_ORDER_REF`.
"""

import re
from dataclasses import dataclass
from typing import Literal

FORWARD_TEST_TAG_PREFIX = "FT"
MANUAL_ORDER_REF = "ATRADE-BY-HAND"
ORDER_REF_PART_SEPARATOR = "-"
FORWARD_TEST_TAG_PATTERN = re.compile(rf"{FORWARD_TEST_TAG_PREFIX}(\d+)")


@dataclass(frozen=True)
class OrderSource:
    kind: Literal["by_hand", "forward_test"]
    forward_test_id: int | None


def format_forward_test_order_tag(forward_test_id: int) -> str:
    return f"{FORWARD_TEST_TAG_PREFIX}{forward_test_id}"


def read_order_source(order_ref: str) -> OrderSource:
    """An orderRef with a part `FT<digits>` comes from that forward test. All other orders are orders by hand."""
    for part in order_ref.split(ORDER_REF_PART_SEPARATOR):
        match = FORWARD_TEST_TAG_PATTERN.fullmatch(part)
        if match is not None:
            return OrderSource(kind="forward_test", forward_test_id=int(match.group(1)))
    return OrderSource(kind="by_hand", forward_test_id=None)
