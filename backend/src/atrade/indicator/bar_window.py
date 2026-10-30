"""The window of the last bars that the indicator classes written by ATrade keep (#162).

Each class holds one `BarWindow` and calculates its value from the window. The strategy path `handle_bar` and the
screen path `update` (through `make_nautilus_bar`) add the same prices (docs/architecture/indicator.md section 23.5).
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model import Bar as NautilusBar


@dataclass(frozen=True)
class WindowBar:
    high: float
    close: float
    volume: float


class BarWindow:
    """The last `bar_count` bars. `bars` is None ("no value") until the window holds `bar_count` bars."""

    def __init__(self, bar_count: int) -> None:
        if bar_count < 1:
            message = f"The indicator needs at least 1 bar, not {bar_count}."
            raise ValueError(message)
        self._bars: deque[WindowBar] = deque(maxlen=bar_count)

    @property
    def full(self) -> bool:
        return len(self._bars) == self._bars.maxlen

    @property
    def bars(self) -> list[WindowBar] | None:
        return list(self._bars) if self.full else None

    def add(self, bar: NautilusBar) -> None:
        self._bars.append(
            WindowBar(high=bar.high.as_double(), close=bar.close.as_double(), volume=bar.volume.as_double())
        )

    def clear(self) -> None:
        self._bars.clear()
