"""The common part of the indicator classes that wrap a NautilusTrader 2.0 indicator (#161).

The strategy path is `handle_bar` (NautilusTrader calls it for a registered indicator). The screen path is `update`:
it makes a NautilusTrader bar from the `foundation` bar and calls `handle_bar`. Both paths give the wrapped indicator
the same prices, so they give the same values (docs/architecture/indicator.md section 23.5).
"""

from typing import Protocol

from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, Price, Quantity

from atrade.foundation.bar import Bar

NANOSECONDS_PER_SECOND = 1_000_000_000
# The wrapped indicators read only the prices and the volume of a bar. The bar type is a fixed placeholder.
SCREEN_BAR_TYPE = BarType.from_str("SCREEN.ATRADE-1-DAY-LAST-EXTERNAL")


class NautilusIndicator(Protocol):
    @property
    def initialized(self) -> bool: ...

    def handle_bar(self, bar: NautilusBar) -> None: ...

    def reset(self) -> None: ...


def to_nautilus_bar(bar: Bar) -> NautilusBar:
    timestamp_ns = int(bar.start_utc.timestamp()) * NANOSECONDS_PER_SECOND
    return NautilusBar(
        SCREEN_BAR_TYPE,
        Price.from_decimal(bar.open),
        Price.from_decimal(bar.high),
        Price.from_decimal(bar.low),
        Price.from_decimal(bar.close),
        Quantity.from_decimal(bar.volume),
        timestamp_ns,
        timestamp_ns,
    )


class WrappedIndicator:
    """An output is "no value" (None) while `initialized` is False, never the NautilusTrader default 0.0."""

    def __init__(self, indicator: NautilusIndicator) -> None:
        self._indicator = indicator

    @property
    def initialized(self) -> bool:
        return self._indicator.initialized

    def handle_bar(self, bar: NautilusBar) -> None:
        self._indicator.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        """The screen path: the same update as `handle_bar` for one saved bar."""
        self.handle_bar(to_nautilus_bar(bar))

    def reset(self) -> None:
        self._indicator.reset()

    def _output(self, value: float) -> float | None:
        return value if self.initialized else None
