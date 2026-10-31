"""The owner ledger as the ATrade execution client sees it (docs/architecture/forward_test.md section 12.19).

The real ledger is `ForwardTestLedger` of `paper_trading` (paper_trading.md section 11.10). The tests can give an
in-memory fake ledger.
"""

from decimal import Decimal
from typing import Protocol

from atrade.paper_trading import OwnerFill, OwnerOrder, OwnerPosition

__all__ = ["OwnerFill", "OwnerLedger", "OwnerOrder", "OwnerPosition"]


class OwnerLedger(Protocol):
    async def check_order(self, order: OwnerOrder) -> str | None:
        """Returns the reason when the order fails a rule, or when the instrument is in the "Split check needed"
        state. Returns None when the order can go to IBKR."""
        ...

    async def save_fill(self, fill: OwnerFill) -> None: ...

    async def read_positions(self, forward_test_id: int) -> list[OwnerPosition]:
        """The owner positions of the forward test that are not 0."""
        ...

    async def read_cash_usd(self, forward_test_id: int) -> Decimal: ...
