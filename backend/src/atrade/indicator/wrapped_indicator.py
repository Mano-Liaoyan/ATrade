"""The common functions of the indicator classes that wrap a NautilusTrader 2.0 indicator (#161).

The screen path `update` makes a NautilusTrader bar with `make_nautilus_bar` and gives it to the wrapped indicator,
as the strategy path `handle_bar` does (docs/architecture/indicator.md section 23.5).
"""

from decimal import Decimal
from typing import Protocol

from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, Price, Quantity

from atrade.foundation.bar import Bar

NANOSECONDS_PER_SECOND = 1_000_000_000
# The wrapped indicators read only the prices and the volume of a bar. The bar type is a fixed placeholder.
SCREEN_BAR_TYPE = BarType.from_str("SCREEN.ATRADE-1-DAY-LAST-EXTERNAL")
# A stock split adjustment can give a price with more decimals than NautilusTrader accepts (for example 100 / 1.5).
# All values of a bar get the same 9 decimals.
NAUTILUS_DECIMALS = Decimal("1e-9")


class NautilusIndicator(Protocol):
    @property
    def initialized(self) -> bool: ...


def make_nautilus_bar(bar: Bar) -> NautilusBar:
    timestamp_ns = int(bar.start_utc.timestamp()) * NANOSECONDS_PER_SECOND
    return NautilusBar(
        SCREEN_BAR_TYPE,
        Price.from_decimal(bar.open.quantize(NAUTILUS_DECIMALS)),
        Price.from_decimal(bar.high.quantize(NAUTILUS_DECIMALS)),
        Price.from_decimal(bar.low.quantize(NAUTILUS_DECIMALS)),
        Price.from_decimal(bar.close.quantize(NAUTILUS_DECIMALS)),
        Quantity.from_decimal(bar.volume.quantize(NAUTILUS_DECIMALS)),
        timestamp_ns,
        timestamp_ns,
    )


def read_output(indicator: NautilusIndicator, value: float) -> float | None:
    """Gives "no value" (None) while the indicator is not initialized, never the NautilusTrader default 0.0."""
    return value if indicator.initialized else None
