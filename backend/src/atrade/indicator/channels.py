"""Bollinger Bands and the Donchian channel: 3 lines `upper`, `middle`, `lower` (docs/architecture/indicator.md
section 23.2).
"""

from nautilus_trader.indicators import BollingerBands as NautilusBollingerBands
from nautilus_trader.indicators import DonchianChannel as NautilusDonchianChannel

from atrade.indicator.wrapped_indicator import NautilusIndicator, WrappedIndicator


class ThreeLineIndicator(WrappedIndicator):
    def __init__(self, indicator: NautilusBollingerBands | NautilusDonchianChannel) -> None:
        indicator_with_protocol: NautilusIndicator = indicator
        super().__init__(indicator_with_protocol)
        self._lines = indicator

    @property
    def upper(self) -> float | None:
        return self._output(self._lines.upper)

    @property
    def middle(self) -> float | None:
        return self._output(self._lines.middle)

    @property
    def lower(self) -> float | None:
        return self._output(self._lines.lower)


class BollingerBands(ThreeLineIndicator):
    """`middle` is the mean of the last `period` closes. `upper` and `lower` are `middle` plus and minus `k`
    population standard deviations of the same closes. Wraps the NautilusTrader `BollingerBands`.
    """

    def __init__(self, period: int = 20, k: float = 2.0) -> None:
        super().__init__(NautilusBollingerBands(period, k))
        self.period = period
        self.k = k


class DonchianChannel(ThreeLineIndicator):
    """`upper` is the highest high and `lower` is the lowest low of the last `period` bars. `middle` is their mean.
    Wraps the NautilusTrader `DonchianChannel`.
    """

    def __init__(self, period: int = 20) -> None:
        super().__init__(NautilusDonchianChannel(period))
        self.period = period
