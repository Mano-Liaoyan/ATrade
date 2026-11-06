"""Formula expressions: the parser, the values, "no value", and the look-back (indicator.md section 23.10)."""

import math
import pickle
import random
import re
import statistics
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.foundation.bar import Bar
from atrade.indicator import INDICATOR_CATALOG, RSI, SMA, FormulaIndicator, check_expression, count_formula_bars
from atrade.indicator.formula_indicator import FormulaProblem
from tests.indicator.test_atrade_indicators import make_long_test_bars
from tests.indicator.test_wrapped_indicators import (
    IndicatorCase,
    IndicatorWithOutputs,
    read_screen_path_outputs,
    read_strategy_path_outputs,
)


def make_bar(close: float, *, index: int = 0) -> Bar:
    price = Decimal(str(close))
    start_utc = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return Bar(start_utc=start_utc, open=price, high=price, low=price, close=price, volume=Decimal(100))


def calculate(expression: str, closes: list[float]) -> float | None:
    indicator = FormulaIndicator(expression)
    for index, close in enumerate(closes):
        indicator.update(make_bar(close, index=index))
    return indicator.value


@pytest.mark.parametrize(
    ("expression", "closes", "expected"),
    [
        ("close", [1, 2], 2.0),
        ("(close + 1) * 2 - 4 / 2", [3], 6.0),
        ("-close", [3], -3.0),
        ("close ** 2", [3], 9.0),
        ("close ** -1", [4], 0.25),
        ("mean(close, 2)", [1, 2, 4], 3.0),
        ("max(close, 2)", [9, 2, 4], 4.0),
        ("min(close, 2)", [9, 2, 4], 2.0),
        ("sum(close, 2)", [9, 2, 4], 6.0),
        ("std(close, 2)", [9, 2, 4], 1.4142135623730951),
        ("lag(close, 2)", [9, 2, 4], 9.0),
        ("close / lag(close, 1) - 1", [2, 3], 0.5),
        ("abs(close - 5)", [3], 2.0),
        ("log(close)", [1], 0.0),
        ("mean(close / lag(close, 1), 2)", [1, 2, 6], 2.5),
        ("volume / 100", [3], 1.0),
        ("high - low + open", [3], 3.0),
    ],
)
def test_calculates_the_expression(expression: str, closes: list[float], expected: float) -> None:
    assert check_expression(expression) == []
    assert calculate(expression, closes) == pytest.approx(expected)


def test_a_call_of_a_catalog_indicator_gives_the_value_of_its_class() -> None:
    closes = [100 + index % 7 for index in range(40)]
    sma = SMA(10)
    rsi = RSI(14)
    formula = FormulaIndicator("sma(10) + rsi(period=14)")
    for index, close in enumerate(closes):
        bar = make_bar(close, index=index)
        sma.update(bar)
        rsi.update(bar)
        formula.update(bar)
    assert sma.value is not None
    assert rsi.value is not None
    assert formula.value == pytest.approx(sma.value + rsi.value)


def test_a_call_selects_an_output() -> None:
    assert calculate('bollinger_bands(5, output="upper") - bollinger_bands(5, output="lower")', [3] * 5) == 0.0


@pytest.mark.parametrize(
    ("expression", "closes"),
    [
        ("close / (close - close)", [1, 2]),
        ("1 / (close - 3)", [3]),
        ("log(close - close)", [1]),
        ("(close - 5) ** 0.5", [1]),
        ("(close - close) ** -1", [1]),
        ("mean(close, 3)", [1, 2]),
        ("lag(close, 3)", [1, 2, 3]),
        ("rsi(14)", [1, 2]),
        ("realized_volatility(2) + close", [1, 2]),
    ],
)
def test_gives_no_value(expression: str, closes: list[float]) -> None:
    assert check_expression(expression) == []
    assert calculate(expression, closes) is None


def test_infinity_gives_no_value_and_a_later_bar_gives_a_value_again() -> None:
    indicator = FormulaIndicator("1 / (close - 3)")
    indicator.update(make_bar(3, index=0))
    assert indicator.value is None
    assert indicator.initialized is False
    indicator.update(make_bar(4, index=1))
    assert indicator.value == 1.0
    assert indicator.initialized is True


def test_overflow_to_infinity_gives_no_value() -> None:
    assert calculate("(close * 1e308) * 10", [9]) is None


def test_nan_gives_no_value() -> None:
    assert calculate("(close * 1e308 * 10) - (close * 1e308 * 10)", [9]) is None


def test_a_window_with_no_value_gives_no_value_until_the_bar_leaves_the_window() -> None:
    indicator = FormulaIndicator("mean(1 / (close - 3), 2)")
    values: list[float | None] = []
    for index, close in enumerate([4.0, 3.0, 4.0, 4.0]):
        indicator.update(make_bar(close, index=index))
        values.append(indicator.value)
    assert values == [None, None, None, 1.0]


def test_a_zero_price_in_a_catalog_class_gives_no_value() -> None:
    assert calculate("momentum_12_1(1, 0)", [0.0, 2.0]) is None


def test_reset_removes_the_bars() -> None:
    indicator = FormulaIndicator("mean(close, 2)")
    indicator.update(make_bar(1, index=0))
    indicator.update(make_bar(2, index=1))
    indicator.reset()
    assert indicator.value is None
    indicator.update(make_bar(2, index=2))
    assert indicator.value is None


@pytest.mark.parametrize(
    ("expression", "bars"),
    [
        ("close", 1),
        ("1 + 2", 1),
        ("mean(close, 20)", 20),
        ("lag(close, 5)", 6),
        ("mean(lag(close, 5), 20)", 25),
        ("max(close, 3) - lag(close, 9)", 10),
        ("rsi(14)", 112),
        ("mean(rsi(14), 5)", 116),
        ("sma(50) / sma(200)", 200),
        ('macd(output="signal")', 280),
        ("close + momentum_12_1()", 253),
    ],
)
def test_counts_the_look_back_from_the_expression(expression: str, bars: int) -> None:
    assert count_formula_bars(expression) == bars


@pytest.mark.parametrize(
    "expression",
    [
        "close",
        "mean(close, 20)",
        "mean(lag(close / open, 5), 20) + 1",
        "std(mean(close, 3), 4)",
        "mean(rsi(14), 5)",
        'macd(output="signal") - lag(sma(5), 2)',
        "realized_volatility(5) + momentum_12_1(5, 1)",
    ],
)
def test_the_look_back_bars_are_enough_for_a_value(expression: str) -> None:
    bars = count_formula_bars(expression)
    closes = [100.0 + (index * 37 % 11) for index in range(bars)]
    assert calculate(expression, closes) is not None
    assert count_formula_bars(expression) == bars


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("", "must not be empty"),
        ("   ", "must not be empty"),
        ("close +", "syntax error"),
        ("__import__('os')", "Unknown function '__import__'"),
        ("__import__('os').system('true')", "Attribute access is not allowed"),
        ("close.real", "Attribute access is not allowed"),
        ("(1).__class__", "Attribute access is not allowed"),
        ("eval('1')", "Unknown function 'eval'"),
        ("exec('1')", "Unknown function 'exec'"),
        ("open()", "Unknown function 'open'"),
        ("foo", "Unknown name 'foo'"),
        ("rsi", "Unknown name 'rsi'"),
        ("mean", "Unknown name 'mean'"),
        ("'text'", "Text is allowed only"),
        ("True", "Only numbers"),
        ("None", "Only numbers"),
        ("1j", "Only numbers"),
        ("1e999", "must be finite"),
        ("[close]", "List is not allowed"),
        ("close if close else 1", "IfExp is not allowed"),
        ("lambda: 1", "Lambda is not allowed"),
        ("close > 1", "Compare is not allowed"),
        ("close % 2", "operator % is not allowed"),
        ("close // 2", "operator // is not allowed"),
        ("not close", "operator not is not allowed"),
        ("close[0]", "Subscript is not allowed"),
        ("f'{close}'", "JoinedStr is not allowed"),
        ("(x := 1)", "NamedExpr is not allowed"),
        ("close; close", "syntax error"),
        ("close ** 99999999", "exponent must be a number from -10 to 10"),
        ("2 ** 2 ** 2 ** 2", "exponent must be a number from -10 to 10"),
        ("close ** close", "exponent must be a number from -10 to 10"),
        ("mean(close)", "mean needs 2 arguments"),
        ("mean(close, 2, 3)", "mean needs 2 arguments"),
        ("mean(close, window=2)", "mean takes no keyword"),
        ("mean(close, close)", "must be an integer"),
        ("mean(close, 2.5)", "must be an integer"),
        ("mean(close, 0)", "from 1 to 1000"),
        ("mean(close, 1001)", "from 1 to 1000"),
        ("std(close, 1)", "from 2 to 1000"),
        ("lag(close, 0)", "from 1 to 1000"),
        ("abs(close, 1)", "abs needs 1 argument"),
        ("rsi(0)", "must be from 1 to 1000"),
        ("rsi(14, 15)", "at most 1 argument"),
        ("rsi(close)", "must be a number"),
        ("rsi(window=3)", "Unknown parameter"),
        ("rsi(14, period=15)", "more than 1 time"),
        ("macd()", "needs an output"),
        ('macd(output="nothing")', "Unknown output"),
        ("macd(26, 12, 9, output='value')", "must be less than"),
        ("custom_1()", "Unknown function 'custom_1'"),
        ("(" * 240 + "close" + ")" * 240, "too many nested"),
        ("-" * 400 + "close", "too deep"),
        ("1" * 501, "at most 500 characters"),
        ("+".join(["close"] * 30), "too deep"),
    ],
)
def test_refuses_the_expression(expression: str, message: str) -> None:
    problems = check_expression(expression)
    assert len(problems) == 1
    assert problems[0].location == ("expression",)
    assert re.search(message, problems[0].message), problems[0].message


def test_a_syntax_error_at_the_end_of_the_text_names_the_column_after_the_text() -> None:
    assert "Column 8:" in check_expression("close +")[0].message


def test_refuses_an_expression_that_reads_too_many_bars() -> None:
    long_macd = "macd(999, 1000, 1000, output='value')"
    problems = check_expression(
        f"lag({long_macd}, 1000) + lag(lag(lag(lag(lag({long_macd}, 1000), 1000), 1000), 1000), 1000)"
    )
    assert [problem.message for problem in problems] == ["Column 1: An expression reads at most 20000 bars, not 21000."]


def test_refuses_an_expression_that_calculates_too_many_window_values() -> None:
    """The expression of the review of #378: it passed the check, and 3 instruments took 70 seconds."""
    four_windows = f"({'+'.join(['std(close,1000)'] * 4)})"
    expression = "+".join(
        [*[four_windows] * 5, "std(close,1000)", "std(close,1000)", "lag(lag(lag(lag(close,1000),1000),1000),1000)"]
    )

    problems = check_expression(expression)

    assert len(expression) <= 500
    assert [(problem.location, problem.message) for problem in problems] == [
        (
            ("expression",),
            (
                "Column 1: The windows of the expression have 26000 bars, and the expression reads 4001 bars. "
                "Window bars x bars read must be at most 10000000, not 104026000. Use fewer or shorter windows."
            ),
        )
    ]


@pytest.mark.parametrize(
    "expression",
    [
        "std(close, 252) / mean(close, 252)",
        "mean(close, 1000) + mean(close, 500) + mean(close, 252) + mean(close, 200)",
        "std(close, 1000) / mean(close, 1000) * lag(close, 1000)",
        "std(close, 1000) / ema(1000)",
        "macd(999, 1000, 1000, output='value')",
        "realized_volatility(252) / realized_volatility(20)",
    ],
)
def test_accepts_the_long_windows_of_a_normal_expression(expression: str) -> None:
    assert check_expression(expression) == []


def test_a_problem_gives_its_column() -> None:
    assert [problem.message for problem in check_expression("close + foo")] == [
        "Column 9: Unknown name 'foo'. Known names: open, high, low, close, volume."
    ]


def test_the_class_refuses_a_wrong_expression() -> None:
    with pytest.raises(ValueError, match="Unknown function"):
        FormulaIndicator("__import__('os')")


def test_no_catalog_key_is_a_formula_function_or_a_bar_field() -> None:
    assert not set(INDICATOR_CATALOG) & {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "mean",
        "max",
        "min",
        "sum",
        "std",
        "lag",
        "abs",
        "log",
    }


def test_no_catalog_key_uses_the_custom_key_form() -> None:
    assert not [key for key in INDICATOR_CATALOG if key.startswith("custom_")]


@pytest.mark.parametrize(
    ("name", "function"),
    [
        ("mean", statistics.fmean),
        ("sum", math.fsum),
        ("std", statistics.stdev),
        ("max", max),
        ("min", min),
    ],
)
@pytest.mark.parametrize("window", [2, 3, 50])
@pytest.mark.parametrize("spike", [1.0, 1e8])
def test_a_rolling_value_is_equal_to_the_function_of_the_full_window(
    name: str, function: Callable[[Sequence[float]], float], window: int, spike: float
) -> None:
    """A very large value that leaves the window leaves no rounding error in the later values."""
    generator = random.Random(378)
    closes = [round(generator.uniform(90, 110), 2) for _ in range(300)]
    closes[100] *= spike
    indicator = FormulaIndicator(f"{name}(close ** 4, {window})")
    for index, close in enumerate(closes):
        indicator.update(make_bar(close, index=index))
        if index + 1 < window:
            assert indicator.value is None
            continue
        expected = function([value**4 for value in closes[index + 1 - window : index + 1]])
        assert indicator.value == pytest.approx(expected, rel=1e-13, abs=0)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("mean(1 / (close - 2), 2)", [None, None, None, None, 1.0]),
        ("max(1 / (close - 2), 2)", [None, None, None, None, 1.0]),
        ("std(1 / (close - 2), 2)", [None, None, None, None, 0.0]),
    ],
)
def test_a_rolling_value_has_no_value_until_the_no_value_leaves_the_window(
    expression: str, expected: list[float | None]
) -> None:
    indicator = FormulaIndicator(expression)
    values: list[float | None] = []
    for index, close in enumerate([3, 2, 2, 3, 3]):
        indicator.update(make_bar(close, index=index))
        values.append(indicator.value)
    assert values == expected


def test_a_rolling_sum_that_overflows_has_no_value_and_a_later_window_has_a_value() -> None:
    indicator = FormulaIndicator("sum(close * 1e308, 2)")
    values: list[float | None] = []
    for index, close in enumerate([1.5, 1.5, 0.001, 0.001]):
        indicator.update(make_bar(close, index=index))
        values.append(indicator.value)
    assert values[:2] == [None, None]
    assert values[3] == pytest.approx(2e305)


def test_a_long_rolling_standard_deviation_does_not_read_the_window_for_each_bar() -> None:
    bars = [make_bar(100 + index % 7, index=index) for index in range(4000)]
    indicator = FormulaIndicator("std(close, 1000)")
    started = time.perf_counter()
    for bar in bars:
        indicator.update(bar)
    assert indicator.value is not None
    assert time.perf_counter() - started < 2


EXPRESSION_OF_THE_PATH_TEST = "mean(close / lag(close, 3), 10) * rsi(14) + sma(5) / (close - 100)"


def create_formula() -> IndicatorWithOutputs:
    indicator = FormulaIndicator(EXPRESSION_OF_THE_PATH_TEST)
    return indicator, lambda: [indicator.value]


def test_the_screen_path_and_the_strategy_path_give_the_same_values(tmp_path: Path) -> None:
    bars = make_long_test_bars()
    case = IndicatorCase(f"FormulaIndicator({EXPRESSION_OF_THE_PATH_TEST!r})", ["value"], 112, create_formula)

    screen_outputs = read_screen_path_outputs(case.create(), bars)

    assert screen_outputs == read_strategy_path_outputs(case, bars, tmp_path)
    assert screen_outputs[0] == [None]
    assert None not in screen_outputs[-1]


def test_a_formula_problem_keeps_its_column_and_message_through_pickle() -> None:
    # A process pool sends the exception of a screen period back with pickle (screen.md section 24.9).
    problem = pickle.loads(pickle.dumps(FormulaProblem(3, "The expression is not correct.")))

    assert (problem.column, problem.message) == (3, "The expression is not correct.")
