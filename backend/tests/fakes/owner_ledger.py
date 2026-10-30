"""Owner ledger fake: the OwnerLedger of `forward_test` in memory (docs/architecture/paper_trading.md section 11.10).

Tests set `positions`, `cash_usd`, and `split_check_needed` directly, and read `checked_orders` and `fills`.
The fake checks only the sell rules (rules 1 and 3) and the "Split check needed" state. Buy orders always pass.
"""

from decimal import Decimal

from atrade.forward_test import OwnerFill, OwnerOrder, OwnerPosition
from atrade.foundation.instrument import Instrument

SELL_TOO_LARGE_REASON = "The sell order is larger than the owner position."
SPLIT_CHECK_NEEDED_REASON = "The instrument needs a stock split check."


class FakeOwnerLedger:
    def __init__(self, *, cash_usd: Decimal) -> None:
        self.cash_usd = cash_usd
        # (forward test ID, instrument) -> owner position.
        self.positions: dict[tuple[int, Instrument], OwnerPosition] = {}
        self.split_check_needed: set[Instrument] = set()
        self.checked_orders: list[OwnerOrder] = []
        self.fills: list[OwnerFill] = []

    def read_quantity(self, forward_test_id: int, instrument: Instrument) -> Decimal:
        position = self.positions.get((forward_test_id, instrument))
        return Decimal(0) if position is None else position.quantity

    async def check_order(self, order: OwnerOrder) -> str | None:
        self.checked_orders.append(order)
        if order.instrument in self.split_check_needed:
            return SPLIT_CHECK_NEEDED_REASON
        if order.side == "SELL" and order.quantity > self.read_quantity(order.forward_test_id, order.instrument):
            return SELL_TOO_LARGE_REASON
        return None

    async def save_fill(self, fill: OwnerFill) -> None:
        self.fills.append(fill)
        key = (fill.forward_test_id, fill.instrument)
        old = self.positions.get(key, OwnerPosition(fill.instrument, Decimal(0), Decimal(0)))
        if fill.side == "BUY":
            quantity = old.quantity + fill.quantity
            average_price = (old.quantity * old.average_price + fill.quantity * fill.price) / quantity
            self.cash_usd -= fill.quantity * fill.price
        else:
            quantity = old.quantity - fill.quantity
            average_price = old.average_price
            self.cash_usd += fill.quantity * fill.price
        self.positions[key] = OwnerPosition(fill.instrument, quantity, average_price)

    async def read_positions(self, forward_test_id: int) -> list[OwnerPosition]:
        return [
            position
            for (owner_id, _), position in self.positions.items()
            if owner_id == forward_test_id and position.quantity != 0
        ]

    async def read_cash_usd(self, forward_test_id: int) -> Decimal:
        return self.cash_usd
