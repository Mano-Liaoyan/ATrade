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
    in_name: bool = True


@dataclass(frozen=True)
class ParameterOrder:
    """The value of the parameter `smaller` must be less than the value of the parameter `larger`."""

    smaller: str
    larger: str


@dataclass(frozen=True)
class IndicatorDefinition:
    key: str
    name: str
    parameters: tuple[IndicatorParameter, ...]
    outputs: tuple[str, ...]
    indicator_class: Callable[..., CatalogIndicator]
    look_back: Callable[[ParameterValues], int]
    orders: tuple[ParameterOrder, ...] = ()

    def with_defaults(self, parameters: ParameterValues) -> dict[str, ParameterValue]:
        return {parameter.name: parameters.get(parameter.name, parameter.default) for parameter in self.parameters}

    def display_name(self, parameters: ParameterValues) -> str:
        """The name that the UI shows, for example `RSI(14)`. Missing parameters show their defaults."""
        values = self.with_defaults(parameters)
        shown = [format_parameter(values[parameter.name]) for parameter in self.parameters if parameter.in_name]
        return f"{self.name}({', '.join(shown)})"

    def screen_look_back_bars(self, parameters: ParameterValues) -> int:
        """The number of daily bars that a screen reads for this indicator (section 23.4)."""
        return self.look_back(self.with_defaults(parameters))


def format_parameter(value: ParameterValue) -> str:
    return str(value) if isinstance(value, int) else f"{value:g}"


def period(name: str = "period", default: int = 20, minimum: int = 1, *, in_name: bool = True) -> IndicatorParameter:
    return IndicatorParameter(name, int, default, minimum, MAXIMUM_PERIOD, in_name=in_name)


def bars_of(name: str, extra: int = 0) -> Callable[[ParameterValues], int]:
    return lambda values: int(values[name]) + extra


def recursive_bars_of(*names: str) -> Callable[[ParameterValues], int]:
    return lambda values: RECURSIVE_LOOK_BACK_FACTOR * sum(int(values[name]) for name in names)


VALUE = ("value",)
THREE_LINES = ("upper", "middle", "lower")

INDICATOR_DEFINITIONS = (
    IndicatorDefinition("sma", "SMA", (period(default=50),), VALUE, SMA, bars_of("period")),
    IndicatorDefinition("ema", "EMA", (period(),), VALUE, EMA, recursive_bars_of("period")),
    IndicatorDefinition(
        "momentum_12_1",
        "12-1 momentum",
        (period("look_back", 252), IndicatorParameter("skip", int, 21, 0, MAXIMUM_PERIOD - 1)),
        VALUE,
        Momentum12_1,
        bars_of("look_back", 1),
        (ParameterOrder("skip", "look_back"),),
    ),
    IndicatorDefinition(
        "distance_to_52_week_high",
        "Distance to 52-week high",
        (period(default=252),),
        VALUE,
        DistanceTo52WeekHigh,
        bars_of("period"),
    ),
    IndicatorDefinition(
        "realized_volatility",
        "Realized volatility",
        (
            period(default=60, minimum=2),
            IndicatorParameter("bars_per_year", int, TRADING_DAYS_PER_YEAR, 1, 10_000, in_name=False),
        ),
        VALUE,
        RealizedVolatility,
        bars_of("period", 1),
    ),
    IndicatorDefinition("atr", "ATR", (period(default=14),), VALUE, ATR, recursive_bars_of("period")),
    IndicatorDefinition(
        "average_trading_value", "Average trading value", (period(),), VALUE, AverageTradingValue, bars_of("period")
    ),
    IndicatorDefinition("rsi", "RSI", (period(default=14),), VALUE, RSI, recursive_bars_of("period")),
    IndicatorDefinition(
        "macd",
        "MACD",
        (period("fast_period", 12), period("slow_period", 26, 2), period("signal_period", 9)),
        ("value", "signal", "histogram"),
        MACD,
        # The signal line is an EMA of the MACD line, so its period adds to the slow period.
        recursive_bars_of("slow_period", "signal_period"),
        (ParameterOrder("fast_period", "slow_period"),),
    ),
    IndicatorDefinition(
        "bollinger_bands",
        "Bollinger Bands",
        (period(), IndicatorParameter("k", float, 2.0, 0.1, 10.0)),
        THREE_LINES,
        BollingerBands,
        bars_of("period"),
    ),
    IndicatorDefinition(
        "donchian_channel", "Donchian channel", (period(),), THREE_LINES, DonchianChannel, bars_of("period")
    ),
)

INDICATOR_CATALOG: Mapping[str, IndicatorDefinition] = {
    definition.key: definition for definition in INDICATOR_DEFINITIONS
}
