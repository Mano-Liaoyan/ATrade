"""The 4 indicators that NautilusTrader does not have (docs/architecture/indicator.md section 23.2, #162)."""

import itertools
import math
import statistics

from atrade.indicator.bar_window import BarWindowIndicator, WindowBar

TRADING_DAYS_PER_YEAR = 252


# The class name follows the indicator name and the catalog key `momentum_12_1`.
class Momentum12_1(BarWindowIndicator):
    """close(t - skip) / close(t - look_back) - 1. The first value comes at bar `look_back + 1`. `skip` can be 0
    (template S3): the value is then close(t) / close(t - look_back) - 1.
    """

    def __init__(self, look_back: int = 252, skip: int = 21) -> None:
        if not 0 <= skip < look_back:
            message = f"The skip must be from 0 to look_back - 1 ({look_back - 1}), not {skip}."
            raise ValueError(message)
        super().__init__(look_back + 1)
        self.look_back = look_back
        self.skip = skip

    def _calculate(self, bars: list[WindowBar]) -> float:
        return bars[-1 - self.skip].close / bars[0].close - 1


class DistanceTo52WeekHigh(BarWindowIndicator):
    """close / the highest high of the last `period` bars, the current bar included."""

    def __init__(self, period: int = 252) -> None:
        super().__init__(period)
        self.period = period

    def _calculate(self, bars: list[WindowBar]) -> float:
        return bars[-1].close / max(bar.high for bar in bars)


class RealizedVolatility(BarWindowIndicator):
    """The sample standard deviation of the last `period` log returns of the close, times the square root of
    `bars_per_year`. The first value comes at bar `period + 1`. Daily bars use 252. 1-hour bars use 1764
    (252 days x 7 regular-session bars).
    """

    def __init__(self, period: int = 60, bars_per_year: int = TRADING_DAYS_PER_YEAR) -> None:
        if period < 2:  # noqa: PLR2004 - a sample standard deviation needs 2 values.
            message = f"The period must be at least 2, not {period}."
            raise ValueError(message)
        super().__init__(period + 1)
        self.period = period
        self.bars_per_year = bars_per_year

    def _calculate(self, bars: list[WindowBar]) -> float:
        log_returns = [math.log(bar.close / previous.close) for previous, bar in itertools.pairwise(bars)]
        return statistics.stdev(log_returns) * math.sqrt(self.bars_per_year)


class AverageTradingValue(BarWindowIndicator):
    """The mean of close x volume of the last `period` bars, in the currency of the instrument."""

    def __init__(self, period: int = 20) -> None:
        super().__init__(period)
        self.period = period

    def _calculate(self, bars: list[WindowBar]) -> float:
        return statistics.fmean(bar.close * bar.volume for bar in bars)
