"""The public entry of the indicator capability (docs/architecture/indicator.md section 23.3).

Strategy code imports the classes from here and registers them with `register_indicator_for_bars`. A screen makes a
NautilusTrader bar of each saved `foundation` bar with `make_nautilus_bar` and gives it to `handle_bar`. Screens and
the rule builder read `INDICATOR_CATALOG` and check stored indicator references with `check_indicator_reference`.
"""

from atrade.indicator.atrade_indicators import (
    ADRPercent,
    AverageTradingValue,
    DistanceTo52WeekHigh,
    Momentum12_1,
    RealizedVolatility,
)
from atrade.indicator.bar_close import BarClose
from atrade.indicator.channels import BollingerBands, DonchianChannel
from atrade.indicator.formula_indicator import (
    MAX_EXPRESSION_LENGTH,
    FormulaIndicator,
    check_expression,
    count_formula_bars,
)
from atrade.indicator.formula_reference import (
    CUSTOM_KEY_PREFIX,
    check_chart_placement,
    check_formula,
    check_name,
    has_unstorable_character,
    is_custom_key,
)
from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    CatalogIndicator,
    IndicatorDefinition,
    IndicatorParameter,
)
from atrade.indicator.indicator_problems import IndicatorProblem
from atrade.indicator.indicator_reference import (
    check_indicator_reference,
    create_indicator,
    find_indicator_definition,
)
from atrade.indicator.moving_averages import EMA, MACD, SMA
from atrade.indicator.wilder_averages import ATR, RSI
from atrade.indicator.wrapped_indicator import make_nautilus_bar

__all__ = [
    "ATR",
    "CUSTOM_KEY_PREFIX",
    "EMA",
    "INDICATOR_CATALOG",
    "MACD",
    "MAX_EXPRESSION_LENGTH",
    "RSI",
    "SMA",
    "ADRPercent",
    "AverageTradingValue",
    "BarClose",
    "BollingerBands",
    "CatalogIndicator",
    "DistanceTo52WeekHigh",
    "DonchianChannel",
    "FormulaIndicator",
    "IndicatorDefinition",
    "IndicatorParameter",
    "IndicatorProblem",
    "Momentum12_1",
    "RealizedVolatility",
    "check_chart_placement",
    "check_expression",
    "check_formula",
    "check_indicator_reference",
    "check_name",
    "count_formula_bars",
    "create_indicator",
    "find_indicator_definition",
    "has_unstorable_character",
    "is_custom_key",
    "make_nautilus_bar",
]
