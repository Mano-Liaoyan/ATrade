"""The common part of the indicator classes that ATrade writes (#162).

Each class keeps a window of the last bars and calculates its value from the window. The strategy path is
`handle_bar`. The screen path `update` makes a NautilusTrader bar from the `foundation` bar and calls `handle_bar`,
so both paths read the same prices (docs/architecture/indicator.md section 23.5).
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.wrapped_indicator import make_nautilus_bar


@dataclass(frozen=True)
class WindowBar:
    high: float
    close: float
    volume: float


class BarWindowIndicator:
    """The value is "no value" (None) until the window holds `bar_count` bars."""

    def __init__(self, bar_count: int) -> None:
        if bar_count < 1:
            message = f"The indicator needs at least 1 bar, not {bar_count}."
            raise ValueError(message)
        self._window: deque[WindowBar] = deque(maxlen=bar_count)

    @property
    def initialized(self) -> bool:
        return len(self._window) == self._window.maxlen

    @property
    def value(self) -> float | None:
        return self._calculate(list(self._window)) if self.initialized else None

    def handle_bar(self, bar: NautilusBar) -> None:
        self._window.append(
            WindowBar(high=bar.high.as_double(), close=bar.close.as_double(), volume=bar.volume.as_double())
        )

    def update(self, bar: Bar) -> None:
        """The screen path: the same update as `handle_bar` for one saved bar."""
        self.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._window.clear()

    def _calculate(self, bars: list[WindowBar]) -> float:
        raise NotImplementedError
