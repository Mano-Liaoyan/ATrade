"""The catalog of the first indicator set (docs/architecture/indicator.md sections 23.3 and 23.4, #163).

Screens and the rule builder use the same catalog. It gives for each indicator the key that they store, the name
that the UI shows, the parameters, the outputs, the meaning and the unit of the value, and the number of daily bars
that a screen reads.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.atrade_indicators import (
    TRADING_DAYS_PER_YEAR,
    AverageTradingValue,
    DistanceTo52WeekHigh,
    Momentum12_1,
    RealizedVolatility,
)
from atrade.indicator.channels import BollingerBands, DonchianChannel
from atrade.indicator.moving_averages import EMA, MACD, SMA
from atrade.indicator.wilder_averages import ATR, RSI

type ParameterValue = int | float
type ParameterValues = Mapping[str, ParameterValue]
# `price`: the indicator draws on the price pane of a bar chart. `own`: it draws in an own pane (section 23.9.2).
type ChartPlacement = Literal["price", "own"]

# A recursive average (EMA, RSI, ATR, MACD) depends a little on its first bar. With 8 x its longest period of bars,
# each difference that #160 measured is less than 0.005 (docs/architecture.md section 21.1).
RECURSIVE_LOOK_BACK_FACTOR = 8
MAXIMUM_PERIOD = 1000


class CatalogIndicator(Protocol):
    """The parts of section 23.3 that each catalog class has. The outputs are attributes with the output names."""

    @property
    def initialized(self) -> bool: ...

    def handle_bar(self, bar: NautilusBar) -> None: ...

    def update(self, bar: Bar) -> None: ...

    def reset(self) -> None: ...


@dataclass(frozen=True)
class IndicatorParameter:
    """A constructor parameter. `value_type` is `int` or `float`. The allowed range includes both ends."""

    name: str
    value_type: type[int | float]
    default: ParameterValue
    minimum: ParameterValue
    maximum: ParameterValue
    is_in_name: bool = True


@dataclass(frozen=True)
class ParameterOrder:
    """The value of the parameter `smaller` must be less than the value of the parameter `larger`."""

    smaller: str
    larger: str


@dataclass(frozen=True)
class ScreenLookBack:
    """The daily bars that a screen reads: `factor` x the sum of the named parameters, plus `extra_bars`."""

    parameter_names: tuple[str, ...]
    factor: int = 1
    extra_bars: int = 0


@dataclass(frozen=True)
class IndicatorDefinition:
    key: str
    name: str
    # The name in the legend of a bar chart, for example `BB` (section 23.9.2).
    short_name: str
    chart_placement: ChartPlacement
    parameters: tuple[IndicatorParameter, ...]
    outputs: tuple[str, ...]
    indicator_class: Callable[..., CatalogIndicator]
    look_back: ScreenLookBack
    # The meaning, the range, and the unit of the value. The AI assistant reads it to write a condition (#373).
    value_description: str
    orders: tuple[ParameterOrder, ...] = ()

    def with_defaults(self, parameters: ParameterValues) -> dict[str, ParameterValue]:
        return {parameter.name: parameters.get(parameter.name, parameter.default) for parameter in self.parameters}

    def display_name(self, parameters: ParameterValues) -> str:
        """The name that the UI shows, for example `RSI(14)`. Missing parameters show their defaults."""
        values = self.with_defaults(parameters)
        shown = [format_parameter(values[parameter.name]) for parameter in self.parameters if parameter.is_in_name]
        return f"{self.name}({', '.join(shown)})"

    def screen_look_back_bars(self, parameters: ParameterValues) -> int:
        """The number of daily bars that a screen reads for this indicator (section 23.4)."""
        values = self.with_defaults(parameters)
        period_sum = sum(int(values[name]) for name in self.look_back.parameter_names)
        return self.look_back.factor * period_sum + self.look_back.extra_bars


def format_parameter(value: ParameterValue) -> str:
    return str(value) if isinstance(value, int) else f"{value:g}"


def make_period_parameter(
    name: str = "period", default: int = 20, minimum: int = 1, *, is_in_name: bool = True
) -> IndicatorParameter:
    return IndicatorParameter(name, int, default, minimum, MAXIMUM_PERIOD, is_in_name=is_in_name)


VALUE = ("value",)
THREE_LINES = ("upper", "middle", "lower")
PERIOD_BARS = ScreenLookBack(("period",))
RECURSIVE_PERIOD_BARS = ScreenLookBack(("period",), factor=RECURSIVE_LOOK_BACK_FACTOR)
PRICE_UNIT = "In the currency of the instrument, per share. It is not a percent."

INDICATOR_DEFINITIONS = (
    IndicatorDefinition(
        "sma",
        "SMA",
        "SMA",
        "price",
        (make_period_parameter(default=50),),
        VALUE,
        SMA,
        PERIOD_BARS,
        f"The mean close of the last `period` bars. {PRICE_UNIT}",
    ),
    IndicatorDefinition(
        "ema",
        "EMA",
        "EMA",
        "price",
        (make_period_parameter(),),
        VALUE,
        EMA,
        RECURSIVE_PERIOD_BARS,
        f"The exponential average of the close with the period `period`. {PRICE_UNIT}",
    ),
    IndicatorDefinition(
        "momentum_12_1",
        "12-1 momentum",
        "MOM 12-1",
        "own",
        (
            make_period_parameter("look_back", 252),
            IndicatorParameter("skip", int, 21, 0, MAXIMUM_PERIOD - 1),
        ),
        VALUE,
        Momentum12_1,
        ScreenLookBack(("look_back",), extra_bars=1),
        "The return close(t - skip) / close(t - look_back) - 1, as a fraction: 0.2 is +20%. Both parameters are counts "
        "of bars, and a screen uses daily bars. The defaults give the 12-month return without the last month. With "
        "skip 0 and look_back 21, 63, or 126, the value is the 1, 3, or 6 month return. Use a `rank` condition to get "
        "a ranking of it.",
        (ParameterOrder("skip", "look_back"),),
    ),
    IndicatorDefinition(
        "distance_to_52_week_high",
        "Distance to 52-week high",
        "52W HIGH",
        "own",
        (make_period_parameter(default=252),),
        VALUE,
        DistanceTo52WeekHigh,
        PERIOD_BARS,
        "close / the highest high of the last `period` bars, from 0 to 1. 1 is at the high. It is a ratio, not a "
        'percent: "within 15% of the high" is `>= 0.85`, not `<= 15`.',
    ),
    IndicatorDefinition(
        "realized_volatility",
        "Realized volatility",
        "RV",
        "own",
        (
            make_period_parameter(default=60, minimum=2),
            IndicatorParameter("bars_per_year", int, TRADING_DAYS_PER_YEAR, 1, 10_000, is_in_name=False),
        ),
        VALUE,
        RealizedVolatility,
        ScreenLookBack(("period",), extra_bars=1),
        "The annualized standard deviation of the last `period` log returns of the close, as a fraction: 0.3 is 30% a "
        "year. `bars_per_year` annualizes it. Daily bars use 252.",
    ),
    IndicatorDefinition(
        "atr",
        "ATR",
        "ATR",
        "own",
        (make_period_parameter(default=14),),
        VALUE,
        ATR,
        RECURSIVE_PERIOD_BARS,
        f"The Wilder average of the true range. {PRICE_UNIT}",
    ),
    IndicatorDefinition(
        "average_trading_value",
        "Average trading value",
        "ATV",
        "own",
        (make_period_parameter(),),
        VALUE,
        AverageTradingValue,
        PERIOD_BARS,
        "The mean of close x volume of the last `period` bars, in the currency of the instrument. 5000000 is 5 million "
        "of that currency for each bar.",
    ),
    IndicatorDefinition(
        "rsi",
        "RSI",
        "RSI",
        "own",
        (make_period_parameter(default=14),),
        VALUE,
        RSI,
        RECURSIVE_PERIOD_BARS,
        "The Wilder relative strength index, from 0 to 100. The usual levels are 30 and 70.",
    ),
    IndicatorDefinition(
        "macd",
        "MACD",
        "MACD",
        "own",
        (
            make_period_parameter("fast_period", 12),
            make_period_parameter("slow_period", 26, 2),
            make_period_parameter("signal_period", 9),
        ),
        ("value", "signal", "histogram"),
        MACD,
        # The signal line is an EMA of the MACD line, so its period adds to the slow period.
        ScreenLookBack(("slow_period", "signal_period"), factor=RECURSIVE_LOOK_BACK_FACTOR),
        "`value` is the fast EMA minus the slow EMA of the close. `signal` is the EMA of `value`. `histogram` is "
        f"`value` minus `signal`. {PRICE_UNIT}",
        (ParameterOrder("fast_period", "slow_period"),),
    ),
    IndicatorDefinition(
        "bollinger_bands",
        "Bollinger Bands",
        "BB",
        "price",
        (make_period_parameter(), IndicatorParameter("k", float, 2.0, 0.1, 10.0)),
        THREE_LINES,
        BollingerBands,
        PERIOD_BARS,
        "`middle` is the mean close of the last `period` bars. `upper` and `lower` are `middle` plus and minus `k` "
        f"standard deviations of the close. {PRICE_UNIT}",
    ),
    IndicatorDefinition(
        "donchian_channel",
        "Donchian channel",
        "DC",
        "price",
        (make_period_parameter(),),
        THREE_LINES,
        DonchianChannel,
        PERIOD_BARS,
        "`upper` is the highest high and `lower` is the lowest low of the last `period` bars. `middle` is their mean. "
        f"{PRICE_UNIT}",
    ),
)

INDICATOR_CATALOG: Mapping[str, IndicatorDefinition] = {
    definition.key: definition for definition in INDICATOR_DEFINITIONS
}
