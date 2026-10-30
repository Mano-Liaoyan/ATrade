"""The 4 indicators that NautilusTrader does not have (docs/architecture/indicator.md section 23.2, #162)."""

import itertools
import math
import statistics

from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.bar_window import BarWindow
from atrade.indicator.wrapped_indicator import make_nautilus_bar

TRADING_DAYS_PER_YEAR = 252


# The class name follows the indicator name and the catalog key `momentum_12_1`.
class Momentum12_1:
    """close(t - skip) / close(t - look_back) - 1. The first value comes at bar `look_back + 1`. `skip` can be 0
    (template S3): the value is then close(t) / close(t - look_back) - 1.
    """

    def __init__(self, look_back: int = 252, skip: int = 21) -> None:
        if look_back < 1:
            message = f"The look_back must be at least 1, not {look_back}."
            raise ValueError(message)
        if not 0 <= skip < look_back:
            message = f"The skip must be from 0 to look_back - 1 ({look_back - 1}), not {skip}."
            raise ValueError(message)
        self.look_back = look_back
        self.skip = skip
        self._window = BarWindow(look_back + 1)

    @property
    def initialized(self) -> bool:
        return self._window.full

    @property
    def value(self) -> float | None:
        bars = self._window.bars
        return None if bars is None else bars[-1 - self.skip].close / bars[0].close - 1

    def handle_bar(self, bar: NautilusBar) -> None:
        self._window.add(bar)

    def update(self, bar: Bar) -> None:
        self._window.add(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._window.clear()


class DistanceTo52WeekHigh:
    """close / the highest high of the last `period` bars, the current bar included."""

    def __init__(self, period: int = 252) -> None:
        self.period = period
        self._window = BarWindow(period)

    @property
    def initialized(self) -> bool:
        return self._window.full

    @property
    def value(self) -> float | None:
        bars = self._window.bars
        return None if bars is None else bars[-1].close / max(bar.high for bar in bars)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._window.add(bar)

    def update(self, bar: Bar) -> None:
        self._window.add(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._window.clear()


class RealizedVolatility:
    """The sample standard deviation of the last `period` log returns of the close, times the square root of
    `bars_per_year`. The first value comes at bar `period + 1`. Daily bars use 252. 1-hour bars use 1764
    (252 days x 7 regular-session bars).
    """

    def __init__(self, period: int = 60, bars_per_year: int = TRADING_DAYS_PER_YEAR) -> None:
        if period < 2:  # noqa: PLR2004 - a sample standard deviation needs 2 values.
            message = f"The period must be at least 2, not {period}."
            raise ValueError(message)
        if bars_per_year < 1:
            message = f"The bars_per_year must be at least 1, not {bars_per_year}."
            raise ValueError(message)
        self.period = period
        self.bars_per_year = bars_per_year
        self._window = BarWindow(period + 1)

    @property
    def initialized(self) -> bool:
        return self._window.full

    @property
    def value(self) -> float | None:
        bars = self._window.bars
        if bars is None:
            return None
        log_returns = [math.log(bar.close / previous.close) for previous, bar in itertools.pairwise(bars)]
        return statistics.stdev(log_returns) * math.sqrt(self.bars_per_year)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._window.add(bar)

    def update(self, bar: Bar) -> None:
        self._window.add(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._window.clear()


class AverageTradingValue:
    """The mean of close x volume of the last `period` bars, in the currency of the instrument."""

    def __init__(self, period: int = 20) -> None:
        self.period = period
        self._window = BarWindow(period)

    @property
    def initialized(self) -> bool:
        return self._window.full

    @property
    def value(self) -> float | None:
        bars = self._window.bars
        return None if bars is None else statistics.fmean(bar.close * bar.volume for bar in bars)

    def handle_bar(self, bar: NautilusBar) -> None:
        self._window.add(bar)

    def update(self, bar: Bar) -> None:
        self._window.add(make_nautilus_bar(bar))

    def reset(self) -> None:
        self._window.clear()
