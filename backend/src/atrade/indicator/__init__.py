"""The public entry of the indicator capability (docs/architecture/indicator.md section 23.3).

Strategy code imports the classes from here and registers them with `register_indicator_for_bars`. A screen gives
each saved `foundation` bar to `update`. Screens and the rule builder read `INDICATOR_CATALOG` and check stored
indicator references with `check_indicator_reference`.
"""

from atrade.indicator.atrade_indicators import (
    AverageTradingValue,
    DistanceTo52WeekHigh,
    Momentum12_1,
    RealizedVolatility,
)
from atrade.indicator.bar_close import BarClose
from atrade.indicator.channels import BollingerBands, DonchianChannel
from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    CatalogIndicator,
    IndicatorDefinition,
    IndicatorParameter,
    ParameterOrder,
    ScreenLookBack,
)
from atrade.indicator.indicator_reference import IndicatorProblem, check_indicator_reference, create_indicator
from atrade.indicator.moving_averages import EMA, MACD, SMA
from atrade.indicator.wilder_averages import ATR, RSI

__all__ = [
    "ATR",
    "EMA",
    "INDICATOR_CATALOG",
    "MACD",
    "RSI",
    "SMA",
    "AverageTradingValue",
    "BarClose",
    "BollingerBands",
    "CatalogIndicator",
    "DistanceTo52WeekHigh",
    "DonchianChannel",
    "IndicatorDefinition",
    "IndicatorParameter",
    "IndicatorProblem",
    "Momentum12_1",
    "ParameterOrder",
    "RealizedVolatility",
    "ScreenLookBack",
    "check_indicator_reference",
    "create_indicator",
]
