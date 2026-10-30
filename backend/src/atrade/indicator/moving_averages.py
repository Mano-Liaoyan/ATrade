"""SMA, EMA, and MACD of the closes (docs/architecture/indicator.md section 23.2)."""

from nautilus_trader.indicators import (
    ExponentialMovingAverage,
    MovingAverageConvergenceDivergence,
    SimpleMovingAverage,
)
from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.wrapped_indicator import make_nautilus_bar, read_output


class SMA:
    """The mean of the last `period` closes. Wraps `SimpleMovingAverage`."""

    def __init__(self, period: int = 50) -> None:
        self.period = period
        self._sma = SimpleMovingAverage(period)

    @property
    def initialized(self) -> bool:
        return self._sma.initialized

    @property
    def value(self) -> float | None:
        return read_output(self._sma, self._sma.value)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._sma.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._sma.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._sma.reset()


class EMA:
    """The exponential average of the closes. Wraps `ExponentialMovingAverage`."""

    def __init__(self, period: int = 20) -> None:
        self.period = period
        self._ema = ExponentialMovingAverage(period)

    @property
    def initialized(self) -> bool:
        return self._ema.initialized

    @property
    def value(self) -> float | None:
        return read_output(self._ema, self._ema.value)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._ema.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._ema.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._ema.reset()


class MACD:
    """`value` is the fast EMA minus the slow EMA. `signal` is the EMA of `value`, and `histogram` is `value`
    minus `signal`. Wraps `MovingAverageConvergenceDivergence` (exponential averages).
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self._macd = MovingAverageConvergenceDivergence(fast_period, slow_period, signal_period)

    @property
    def initialized(self) -> bool:
        return self._macd.initialized

    @property
    def value(self) -> float | None:
        return read_output(self._macd, self._macd.value)

    @property
    def signal(self) -> float | None:
        return read_output(self._macd, self._macd.signal)

    @property
    def histogram(self) -> float | None:
        return read_output(self._macd, self._macd.histogram)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._macd.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._macd.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._macd.reset()
