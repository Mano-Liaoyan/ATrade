"""The catalog of the first indicator set (docs/architecture/indicator.md sections 23.3 and 23.4, #163).

Screens and the rule builder use the same catalog. It gives for each indicator the key that they store, the name
that the UI shows, the parameters, the outputs, and the number of daily bars that a screen reads.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

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
    parameters: tuple[IndicatorParameter, ...]
    outputs: tuple[str, ...]
    indicator_class: Callable[..., CatalogIndicator]
    look_back: ScreenLookBack
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

INDICATOR_DEFINITIONS = (
    IndicatorDefinition("sma", "SMA", (make_period_parameter(default=50),), VALUE, SMA, PERIOD_BARS),
    IndicatorDefinition("ema", "EMA", (make_period_parameter(),), VALUE, EMA, RECURSIVE_PERIOD_BARS),
    IndicatorDefinition(
        "momentum_12_1",
        "12-1 momentum",
        (
            make_period_parameter("look_back", 252),
            IndicatorParameter("skip", int, 21, 0, MAXIMUM_PERIOD - 1),
        ),
        VALUE,
        Momentum12_1,
        ScreenLookBack(("look_back",), extra_bars=1),
        (ParameterOrder("skip", "look_back"),),
    ),
    IndicatorDefinition(
        "distance_to_52_week_high",
        "Distance to 52-week high",
        (make_period_parameter(default=252),),
        VALUE,
        DistanceTo52WeekHigh,
        PERIOD_BARS,
    ),
    IndicatorDefinition(
        "realized_volatility",
        "Realized volatility",
        (
            make_period_parameter(default=60, minimum=2),
            IndicatorParameter("bars_per_year", int, TRADING_DAYS_PER_YEAR, 1, 10_000, is_in_name=False),
        ),
        VALUE,
        RealizedVolatility,
        ScreenLookBack(("period",), extra_bars=1),
    ),
    IndicatorDefinition("atr", "ATR", (make_period_parameter(default=14),), VALUE, ATR, RECURSIVE_PERIOD_BARS),
    IndicatorDefinition(
        "average_trading_value",
        "Average trading value",
        (make_period_parameter(),),
        VALUE,
        AverageTradingValue,
        PERIOD_BARS,
    ),
    IndicatorDefinition("rsi", "RSI", (make_period_parameter(default=14),), VALUE, RSI, RECURSIVE_PERIOD_BARS),
    IndicatorDefinition(
        "macd",
        "MACD",
        (
            make_period_parameter("fast_period", 12),
            make_period_parameter("slow_period", 26, 2),
            make_period_parameter("signal_period", 9),
        ),
        ("value", "signal", "histogram"),
        MACD,
        # The signal line is an EMA of the MACD line, so its period adds to the slow period.
        ScreenLookBack(("slow_period", "signal_period"), factor=RECURSIVE_LOOK_BACK_FACTOR),
        (ParameterOrder("fast_period", "slow_period"),),
    ),
    IndicatorDefinition(
        "bollinger_bands",
        "Bollinger Bands",
        (make_period_parameter(), IndicatorParameter("k", float, 2.0, 0.1, 10.0)),
        THREE_LINES,
        BollingerBands,
        PERIOD_BARS,
    ),
    IndicatorDefinition(
        "donchian_channel", "Donchian channel", (make_period_parameter(),), THREE_LINES, DonchianChannel, PERIOD_BARS
    ),
)

INDICATOR_CATALOG: Mapping[str, IndicatorDefinition] = {
    definition.key: definition for definition in INDICATOR_DEFINITIONS
}
