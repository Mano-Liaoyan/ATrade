"""ATR and RSI: Wilder averages (docs/architecture/indicator.md section 23.2).

The NautilusTrader 2.0.0rc7 default of `AverageTrueRange` and `RelativeStrengthIndex` is the Wilder average
(docs/architecture.md section 21.1, #160), so the classes do not pass `ma_type`. The tests compare the values with
Wilder averages calculated by hand.
"""

from nautilus_trader.indicators import AverageTrueRange, RelativeStrengthIndex

from atrade.indicator.wrapped_indicator import WrappedIndicator


class ATR(WrappedIndicator):
    """The Wilder average of the true range. Wraps `AverageTrueRange`."""

    def __init__(self, period: int = 14) -> None:
        self._atr = AverageTrueRange(period)
        super().__init__(self._atr)
        self.period = period

    @property
    def value(self) -> float | None:
        return self._output(self._atr.value)


class RSI(WrappedIndicator):
    """100 - 100 / (1 + average gain / average loss), Wilder averages, from 0 to 100. Wraps
    `RelativeStrengthIndex`.
    """

    def __init__(self, period: int = 14) -> None:
        self._rsi = RelativeStrengthIndex(period)
        super().__init__(self._rsi)
        self.period = period

    @property
    def value(self) -> float | None:
        return self._output(self._rsi.value)
