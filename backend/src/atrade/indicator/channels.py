"""Bollinger Bands and the Donchian channel: 3 lines `upper`, `middle`, `lower` (docs/architecture/indicator.md
section 23.2).
"""

from nautilus_trader.indicators import BollingerBands as NautilusBollingerBands
from nautilus_trader.indicators import DonchianChannel as NautilusDonchianChannel
from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.wrapped_indicator import make_nautilus_bar, read_output


class BollingerBands:
    """`middle` is the mean of the last `period` closes. `upper` and `lower` are `middle` plus and minus `k`
    population standard deviations of the same closes. Wraps the NautilusTrader `BollingerBands`.
    """

    def __init__(self, period: int = 20, k: float = 2.0) -> None:
        self.period = period
        self.k = k
        self._bands = NautilusBollingerBands(period, k)

    @property
    def initialized(self) -> bool:
        return self._bands.initialized

    @property
    def upper(self) -> float | None:
        return read_output(self._bands, self._bands.upper)

    @property
    def middle(self) -> float | None:
        return read_output(self._bands, self._bands.middle)

    @property
    def lower(self) -> float | None:
        return read_output(self._bands, self._bands.lower)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._bands.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._bands.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._bands.reset()


class DonchianChannel:
    """`upper` is the highest high and `lower` is the lowest low of the last `period` bars. `middle` is their mean.
    Wraps the NautilusTrader `DonchianChannel`.
    """

    def __init__(self, period: int = 20) -> None:
        self.period = period
        self._channel = NautilusDonchianChannel(period)

    @property
    def initialized(self) -> bool:
        return self._channel.initialized

    @property
    def upper(self) -> float | None:
        return read_output(self._channel, self._channel.upper)

    @property
    def middle(self) -> float | None:
        return read_output(self._channel, self._channel.middle)

    @property
    def lower(self) -> float | None:
        return read_output(self._channel, self._channel.lower)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._channel.handle_bar(bar)

    def update(self, bar: Bar) -> None:
        self._channel.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._channel.reset()
