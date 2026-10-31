"""ATR and RSI: Wilder averages (docs/architecture/indicator.md section 23.2).

The NautilusTrader 2.0.0rc7 default of both is Wilder (section 21.1, #160), so the classes do not pass `ma_type`.
"""

from nautilus_trader.indicators import AverageTrueRange, RelativeStrengthIndex
from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.wrapped_indicator import make_nautilus_bar, read_output


class ATR:
    """The Wilder average of the true range. Wraps `AverageTrueRange`."""

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self._atr = AverageTrueRange(period)

    @property
    def initialized(self) -> bool:
        return self._atr.initialized

    @property
    def value(self) -> float | None:
        return read_output(self._atr, self._atr.value)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._atr.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._atr.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._atr.reset()


class RSI:
    """100 - 100 / (1 + average gain / average loss), Wilder averages, from 0 to 100. Wraps
    `RelativeStrengthIndex`.
    """

    def __init__(self, period: int = 14) -> None:
        self.period = period
        self._rsi = RelativeStrengthIndex(period)

    @property
    def initialized(self) -> bool:
        return self._rsi.initialized

    @property
    def value(self) -> float | None:
        return read_output(self._rsi, self._rsi.value)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._rsi.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._rsi.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._rsi.reset()
