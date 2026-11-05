"""The indicator catalog (docs/architecture/indicator.md sections 23.3 and 23.4, #163)."""

import pytest

import atrade.indicator
from atrade.indicator import (
    ATR,
    EMA,
    INDICATOR_CATALOG,
    MACD,
    RSI,
    SMA,
    ADRPercent,
    AverageTradingValue,
    BollingerBands,
    CatalogIndicator,
    DistanceTo52WeekHigh,
    DonchianChannel,
    Momentum12_1,
    RealizedVolatility,
)
from tests.indicator.test_atrade_indicators import make_long_test_bars

CATALOG_KEYS = [
    "sma",
    "ema",
    "momentum_12_1",
    "distance_to_52_week_high",
    "realized_volatility",
    "atr",
    "average_trading_value",
    "rsi",
    "macd",
    "bollinger_bands",
    "donchian_channel",
    "adr_percent",
]


def read_outputs(indicator: CatalogIndicator) -> list[float | None]:
    match indicator:
        case MACD():
            return [indicator.value, indicator.signal, indicator.histogram]
        case BollingerBands() | DonchianChannel():
            return [indicator.upper, indicator.middle, indicator.lower]
        case (
            SMA()
            | EMA()
            | ATR()
            | RSI()
            | Momentum12_1()
            | DistanceTo52WeekHigh()
            | RealizedVolatility()
            | AverageTradingValue()
            | ADRPercent()
        ):
            return [indicator.value]
        case _:
            message = f"No output reader for {indicator!r}."
            raise AssertionError(message)


def test_the_catalog_has_the_12_keys_of_section_23_6() -> None:
    assert list(INDICATOR_CATALOG) == CATALOG_KEYS


@pytest.mark.parametrize(
    ("key", "parameters", "look_back_bars"),
    [
        ("sma", {"period": 200}, 200),
        ("average_trading_value", {"period": 60}, 60),
        ("bollinger_bands", {"period": 30}, 30),
        ("donchian_channel", {"period": 55}, 55),
        ("adr_percent", {"period": 30}, 30),
        ("distance_to_52_week_high", {}, 252),
        ("momentum_12_1", {"look_back": 126}, 127),
        ("realized_volatility", {"period": 252}, 253),
        # EMA, RSI, ATR, MACD: 8 x the longest recursive period (docs/architecture.md section 21.1).
        ("ema", {"period": 50}, 400),
        ("rsi", {"period": 14}, 112),
        ("atr", {"period": 14}, 112),
        ("macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}, 280),
    ],
)
def test_the_screen_look_back_follows_section_23_4(
    key: str, parameters: dict[str, int | float], look_back_bars: int
) -> None:
    assert INDICATOR_CATALOG[key].screen_look_back_bars(parameters) == look_back_bars


@pytest.mark.parametrize(
    ("key", "parameters", "name"),
    [
        ("sma", {}, "SMA(50)"),
        ("rsi", {"period": 7}, "RSI(7)"),
        ("macd", {}, "MACD(12, 26, 9)"),
        ("bollinger_bands", {}, "Bollinger Bands(20, 2)"),
        ("bollinger_bands", {"k": 2.5}, "Bollinger Bands(20, 2.5)"),
        ("momentum_12_1", {"skip": 0}, "12-1 momentum(252, 0)"),
        ("realized_volatility", {}, "Realized volatility(60)"),
        ("distance_to_52_week_high", {}, "Distance to 52-week high(252)"),
        ("adr_percent", {}, "ADR%(20)"),
    ],
)
def test_the_ui_name_shows_the_parameters(key: str, parameters: dict[str, int | float], name: str) -> None:
    assert INDICATOR_CATALOG[key].display_name(parameters) == name


@pytest.mark.parametrize("key", CATALOG_KEYS)
def test_the_default_class_has_a_value_after_the_screen_look_back_bars(key: str) -> None:
    definition = INDICATOR_CATALOG[key]
    look_back_bars = definition.screen_look_back_bars({})
    bars = make_long_test_bars()[-look_back_bars:]
    indicator = atrade.indicator.create_indicator({"indicator": key, "output": definition.outputs[0]})

    for bar in bars:
        indicator.update(bar)

    outputs = read_outputs(indicator)
    assert len(bars) == look_back_bars
    assert len(outputs) == len(definition.outputs)
    assert all(output is not None for output in outputs)


@pytest.mark.parametrize("key", CATALOG_KEYS)
def test_each_parameter_range_end_makes_a_class(key: str) -> None:
    definition = INDICATOR_CATALOG[key]
    for parameter in definition.parameters:
        for end in (parameter.minimum, parameter.maximum):
            reference = {"indicator": key, "parameters": {parameter.name: end}, "output": definition.outputs[0]}
            if atrade.indicator.check_indicator_reference(reference):
                continue  # A range end can break a rule between 2 parameters, for example skip < look_back.
            atrade.indicator.create_indicator(reference)


@pytest.mark.parametrize("key", CATALOG_KEYS)
def test_each_indicator_says_what_its_value_means(key: str) -> None:
    assert INDICATOR_CATALOG[key].value_description.strip()


def test_the_distance_to_the_high_says_its_range_and_how_to_write_a_condition() -> None:
    description = INDICATOR_CATALOG["distance_to_52_week_high"].value_description

    assert "from 0 to 1" in description
    assert "`>= 0.85`" in description


def test_the_momentum_says_how_its_parameters_give_other_return_periods() -> None:
    description = INDICATOR_CATALOG["momentum_12_1"].value_description

    assert "skip 0 and look_back 21, 63, or 126" in description
    assert "fraction" in description
    assert "`rank`" in description


def test_the_realized_volatility_says_that_it_is_an_annualized_fraction() -> None:
    description = INDICATOR_CATALOG["realized_volatility"].value_description

    assert "annualized" in description
    assert "fraction" in description
