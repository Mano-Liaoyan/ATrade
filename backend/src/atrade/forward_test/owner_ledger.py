"""The owner ledger as the ATrade execution client sees it (docs/architecture/forward_test.md section 12.19).

The real ledger is in `paper_trading` (paper_trading.md sections 11.10 and 11.11, #214 and #215). Until then, this
module is only the interface. The tests give an in-memory fake ledger.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from atrade.foundation.instrument import Instrument
from atrade.ibkr import OrderSide


@dataclass(frozen=True)
class OwnerOrder:
    """An order that a forward test wants to send. The ledger checks it with the order rules of section 11.10."""

    forward_test_id: int
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    # None for a market order.
    limit_price: Decimal | None


@dataclass(frozen=True)
class OwnerFill:
    forward_test_id: int
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    price: Decimal
    time_utc: datetime
    # The IBKR orderRef of the order: the NautilusTrader ClientOrderId, which holds `FT<ID>` (section 12.9).
    order_ref: str


@dataclass(frozen=True)
class OwnerPosition:
    instrument: Instrument
    quantity: Decimal
    average_price: Decimal


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
