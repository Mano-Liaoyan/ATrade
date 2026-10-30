"""The minimal indicator: the close of the last bar (#160).

It shows the form of an ATrade indicator class (docs/architecture/indicator.md section 23.3). The class does not
subclass a NautilusTrader indicator. `Strategy.register_indicator_for_bars` accepts any object with `handle_bar`
and `initialized`, and NautilusTrader calls `handle_bar` before `on_bar`.
"""

from nautilus_trader.model import Bar


class BarClose:
    """The close of the last bar. The value is None before the first bar."""

    def __init__(self) -> None:
        self.value: float | None = None

    @property
    def initialized(self) -> bool:
        return self.value is not None

    def handle_bar(self, bar: Bar) -> None:
        self.value = bar.close.as_double()

    def reset(self) -> None:
        self.value = None
