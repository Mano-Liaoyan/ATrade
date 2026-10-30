"""The 4 indicator classes that ATrade writes (docs/architecture/indicator.md sections 23.2, 23.3, 23.4, and 23.5,
#162).
"""

import math
import random
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import atrade.indicator
from atrade.foundation.bar import Bar
from atrade.indicator import AverageTradingValue, DistanceTo52WeekHigh, Momentum12_1, RealizedVolatility
from tests.indicator.test_wrapped_indicators import (
    IndicatorCase,
    IndicatorWithOutputs,
    read_screen_path_outputs,
    read_strategy_path_outputs,
)

FIRST_BAR_UTC = datetime(2026, 1, 1, tzinfo=UTC)
# More bars than the longest default warm-up (12-1 momentum: 253 bars).
BAR_COUNT = 300

type AtradeIndicator = Momentum12_1 | DistanceTo52WeekHigh | RealizedVolatility | AverageTradingValue
INDICATOR_CLASSES: dict[str, Callable[..., AtradeIndicator]] = {
    "Momentum12_1": Momentum12_1,
    "DistanceTo52WeekHigh": DistanceTo52WeekHigh,
    "RealizedVolatility": RealizedVolatility,
    "AverageTradingValue": AverageTradingValue,
}


def make_case(name: str, warm_up_bars: int, parameters: dict[str, int] | None = None) -> IndicatorCase:
    """A case of one ATrade indicator with the output `value`."""
    values = parameters or {}

    def create() -> IndicatorWithOutputs:
        indicator = INDICATOR_CLASSES[name](**values)
        return indicator, lambda: [indicator.value]

    arguments = ", ".join(f"{key}={value}" for key, value in values.items())
    return IndicatorCase(f"{name}({arguments})", ["value"], warm_up_bars, create)


CASES = [
    # Look-back 252 needs 253 closes.
    make_case("Momentum12_1", 253),
    make_case("Momentum12_1", 253, {"look_back": 252, "skip": 0}),
    make_case("Momentum12_1", 11, {"look_back": 10, "skip": 2}),
    make_case("DistanceTo52WeekHigh", 252),
    # 60 log returns need 61 closes.
    make_case("RealizedVolatility", 61),
    make_case("RealizedVolatility", 253, {"period": 252}),
    make_case("AverageTradingValue", 20),
]
CASE_IDS = [case.constructor_code for case in CASES]


def make_long_test_bars() -> list[Bar]:
    """Fixed random daily bars with 2-decimal prices: each close is the previous close times exp(N(0, 0.02))."""
    generator = random.Random(162)
    bars: list[Bar] = []
    previous_close = Decimal("100.00")
    for index in range(BAR_COUNT):
        close = Decimal(str(round(float(previous_close) * math.exp(generator.gauss(0, 0.02)), 2)))
        bars.append(
            Bar(
                start_utc=FIRST_BAR_UTC + timedelta(days=index),
                open=previous_close,
                high=max(previous_close, close) + Decimal(str(round(generator.uniform(0, 1), 2))),
                low=min(previous_close, close) - Decimal(str(round(generator.uniform(0, 1), 2))),
                close=close,
                volume=Decimal(generator.randint(1000, 5000)),
            )
        )
        previous_close = close
    return bars


def make_bars(prices: list[tuple[int, int, int]]) -> list[Bar]:
    """Daily bars from (high, close, volume) values. The low is the close minus 1."""
    return [
        Bar(
            start_utc=FIRST_BAR_UTC + timedelta(days=index),
            open=Decimal(close),
            high=Decimal(high),
            low=Decimal(close - 1),
            close=Decimal(close),
            volume=Decimal(volume),
        )
        for index, (high, close, volume) in enumerate(prices)
    ]


def read_values(name: str, parameters: dict[str, int], bars: list[Bar]) -> list[float | None]:
    return [output[0] for output in read_screen_path_outputs(make_case(name, 1, parameters).create(), bars)]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_the_screen_path_and_the_strategy_path_give_the_same_outputs(case: IndicatorCase, tmp_path: Path) -> None:
    bars = make_long_test_bars()

    screen_outputs = read_screen_path_outputs(case.create(), bars)
    strategy_outputs = read_strategy_path_outputs(case, bars, tmp_path)

    assert len(strategy_outputs) == BAR_COUNT
    assert screen_outputs == strategy_outputs
    assert screen_outputs[0] == [None]
    assert None not in screen_outputs[-1]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_the_outputs_are_no_value_before_the_warm_up_end_not_zero(case: IndicatorCase) -> None:
    bars = make_long_test_bars()
    indicator, read_outputs = case.create()

    outputs = read_screen_path_outputs((indicator, read_outputs), bars)

    assert outputs[: case.warm_up_bars - 1] == [[None]] * (case.warm_up_bars - 1)
    assert None not in outputs[case.warm_up_bars - 1]
    assert 0.0 not in outputs[case.warm_up_bars - 1]
    # `reset` removes all received bars.
    for bar in bars:
        indicator.update(bar)
    assert indicator.initialized
    indicator.reset()
    assert not indicator.initialized
    assert read_outputs() == [None]


def test_momentum_divides_the_close_skip_bars_ago_by_the_close_look_back_bars_ago() -> None:
    bars = make_bars([(101, 100, 1), (111, 110, 1), (122, 121, 1), (121, 120, 1), (133, 132, 1)])

    values = read_values("Momentum12_1", {"look_back": 3, "skip": 1}, bars)

    # Bar 4: 121 / 100 - 1. Bar 5: 120 / 110 - 1.
    assert values == [None, None, None, pytest.approx(0.21, rel=1e-12), pytest.approx(1 / 11, rel=1e-12)]


def test_momentum_with_skip_0_divides_the_last_close_by_the_close_252_bars_before() -> None:
    bars = make_long_test_bars()

    values = read_values("Momentum12_1", {"look_back": 252, "skip": 0}, bars)

    assert values[:252] == [None] * 252
    expected = [float(bar.close) / float(bars[index - 252].close) - 1 for index, bar in enumerate(bars)][252:]
    assert values[252:] == pytest.approx(expected, rel=1e-12)


def test_momentum_defaults_are_look_back_252_and_skip_21() -> None:
    momentum = atrade.indicator.Momentum12_1()

    assert (momentum.look_back, momentum.skip) == (252, 21)


@pytest.mark.parametrize("parameters", [{"skip": -1}, {"look_back": 10, "skip": 10}, {"look_back": 0, "skip": 0}])
def test_momentum_refuses_a_skip_outside_0_to_look_back(parameters: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="skip"):
        atrade.indicator.Momentum12_1(**parameters)


def test_the_distance_to_the_52_week_high_divides_the_close_by_the_highest_high() -> None:
    bars = make_bars([(110, 100, 1), (105, 104, 1), (103, 99, 1), (102, 102, 1)])

    values = read_values("DistanceTo52WeekHigh", {"period": 3}, bars)

    # Bar 3: 99 / max(110, 105, 103). Bar 4: 102 / max(105, 103, 102).
    assert values == [None, None, pytest.approx(0.9, rel=1e-12), pytest.approx(102 / 105, rel=1e-12)]


def test_the_realized_volatility_is_the_sample_deviation_of_the_log_returns_times_the_root_of_252() -> None:
    bars = make_bars([(101, 100, 1), (111, 110, 1), (100, 99, 1)])

    values = read_values("RealizedVolatility", {"period": 2}, bars)

    # ln(110 / 100) = 0.0953102, ln(99 / 110) = -0.1053605. Sample deviation 0.1418956, times sqrt(252).
    assert values == [None, None, pytest.approx(2.2525230, rel=1e-6)]


def test_the_realized_volatility_of_1_hour_bars_uses_the_bars_of_one_year() -> None:
    bars = make_bars([(101, 100, 1), (111, 110, 1), (100, 99, 1)])

    values = read_values("RealizedVolatility", {"period": 2, "bars_per_year": 1764}, bars)

    # The same deviation times sqrt(252 x 7).
    assert values[-1] == pytest.approx(0.1418956 * math.sqrt(1764), rel=1e-6)


def test_the_average_trading_value_is_the_mean_of_close_times_volume() -> None:
    bars = make_bars([(101, 100, 1000), (51, 50, 3000), (21, 20, 2500)])

    values = read_values("AverageTradingValue", {"period": 2}, bars)

    # Bar 2: (100000 + 150000) / 2. Bar 3: (150000 + 50000) / 2.
    assert values == [None, 125000.0, 100000.0]


@pytest.mark.parametrize(
    ("name", "defaults"),
    [
        ("DistanceTo52WeekHigh", {"period": 252}),
        ("RealizedVolatility", {"period": 60, "bars_per_year": 252}),
        ("AverageTradingValue", {"period": 20}),
    ],
)
def test_the_defaults_of_the_indicators(name: str, defaults: dict[str, int]) -> None:
    indicator = getattr(atrade.indicator, name)()

    assert {parameter: getattr(indicator, parameter) for parameter in defaults} == defaults
