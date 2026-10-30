"""SMA, EMA, and MACD of the closes (docs/architecture/indicator.md section 23.2)."""

from nautilus_trader.indicators import (
    ExponentialMovingAverage,
    MovingAverageConvergenceDivergence,
    SimpleMovingAverage,
)

from atrade.indicator.wrapped_indicator import WrappedIndicator


class SMA(WrappedIndicator):
    """The mean of the last `period` closes. Wraps `SimpleMovingAverage`."""

    def __init__(self, period: int = 50) -> None:
        self._sma = SimpleMovingAverage(period)
        super().__init__(self._sma)
        self.period = period

    @property
    def value(self) -> float | None:
        return self._output(self._sma.value)


class EMA(WrappedIndicator):
    """The exponential average of the closes. Wraps `ExponentialMovingAverage`."""

    def __init__(self, period: int = 20) -> None:
        self._ema = ExponentialMovingAverage(period)
        super().__init__(self._ema)
        self.period = period

    @property
    def value(self) -> float | None:
        return self._output(self._ema.value)


class MACD(WrappedIndicator):
    """`value` is the fast EMA minus the slow EMA. `signal` is the EMA of `value`, and `histogram` is `value`
    minus `signal`. Wraps `MovingAverageConvergenceDivergence` (exponential averages).
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> None:
        self._macd = MovingAverageConvergenceDivergence(fast_period, slow_period, signal_period)
        super().__init__(self._macd)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def value(self) -> float | None:
        return self._output(self._macd.value)

    @property
    def signal(self) -> float | None:
        return self._output(self._macd.signal)

    @property
    def histogram(self) -> float | None:
        return self._output(self._macd.histogram)
