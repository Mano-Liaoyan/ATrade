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
from atrade.indicator import (
    INDICATOR_CATALOG,
    RSI,
    SMA,
    FormulaIndicator,
    check_expression,
    count_formula_bars,
    make_nautilus_bar,
)
from atrade.indicator.formula_indicator import FormulaProblem
from atrade.indicator.indicator_catalog import IndicatorParameter
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
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
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
        sma.handle_bar(make_nautilus_bar(bar))
        rsi.handle_bar(make_nautilus_bar(bar))
        formula.handle_bar(make_nautilus_bar(bar))
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
    indicator.handle_bar(make_nautilus_bar(make_bar(3, index=0)))
    assert indicator.value is None
    assert indicator.initialized is False
    indicator.handle_bar(make_nautilus_bar(make_bar(4, index=1)))
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
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
        values.append(indicator.value)
    assert values == [None, None, None, 1.0]


def test_a_zero_price_in_a_catalog_class_gives_no_value() -> None:
    assert calculate("momentum_12_1(1, 0)", [0.0, 2.0]) is None


def test_reset_removes_the_bars() -> None:
    indicator = FormulaIndicator("mean(close, 2)")
    indicator.handle_bar(make_nautilus_bar(make_bar(1, index=0)))
    indicator.handle_bar(make_nautilus_bar(make_bar(2, index=1)))
    indicator.reset()
    assert indicator.value is None
    indicator.handle_bar(make_nautilus_bar(make_bar(2, index=2)))
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
        ("close; close", "must give a name to a value"),
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
        ("1" * 1001, "at most 1000 characters"),
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
        "quantile",
        "median",
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
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
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
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
        values.append(indicator.value)
    assert values == expected


def test_a_rolling_sum_that_overflows_has_no_value_and_a_later_window_has_a_value() -> None:
    indicator = FormulaIndicator("sum(close * 1e308, 2)")
    values: list[float | None] = []
    for index, close in enumerate([1.5, 1.5, 0.001, 0.001]):
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
        values.append(indicator.value)
    assert values[:2] == [None, None]
    assert values[3] == pytest.approx(2e305)


def test_a_long_rolling_standard_deviation_does_not_read_the_window_for_each_bar() -> None:
    bars = [make_bar(100 + index % 7, index=index) for index in range(4000)]
    indicator = FormulaIndicator("std(close, 1000)")
    started = time.perf_counter()
    for bar in bars:
        indicator.handle_bar(make_nautilus_bar(bar))
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
    problem = pickle.loads(pickle.dumps(FormulaProblem(3, "The expression is not correct.", 2)))

    assert (problem.column, problem.message, problem.line) == (3, "The expression is not correct.", 2)


def calculate_with(expression: str, parameters: dict[str, int | float], closes: list[float]) -> float | None:
    indicator = FormulaIndicator(expression, parameters)
    for index, close in enumerate(closes):
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
    return indicator.value


CLOSES = [100.0 + (index * 37 % 11) for index in range(400)]
WIDTH = "lag(std(close, 20) / mean(close, 20), 1)"
RELATIVE_WIDTH = f"({WIDTH} - mean({WIDTH}, 60)) / ({WIDTH} + mean({WIDTH}, 60))"


@pytest.mark.parametrize(
    ("expression", "parameters", "fixed"),
    [
        ("mean(close, days)", {"days": 20}, "mean(close, 20)"),
        ("lag(close, days) * factor", {"days": 3, "factor": 1.5}, "lag(close, 3) * 1.5"),
        ("sma(period=days) + rsi(days)", {"days": 14}, "sma(period=14) + rsi(14)"),
        (
            'bollinger_bands(days, k, output="upper")',
            {"days": 10, "k": 2.5},
            'bollinger_bands(10, 2.5, output="upper")',
        ),
        ("quantile(close, days, part)", {"days": 9, "part": 0.25}, "quantile(close, 9, 0.25)"),
        (RELATIVE_WIDTH.replace("60", "lookback_days"), {"lookback_days": 20}, RELATIVE_WIDTH.replace("60", "20")),
    ],
)
def test_a_parameter_gives_the_value_of_the_same_number(
    expression: str, parameters: dict[str, int | float], fixed: str
) -> None:
    value = calculate_with(expression, parameters, CLOSES)

    assert value is not None
    assert value == calculate(fixed, CLOSES)
    assert count_formula_bars(expression, tuple(parameters.items())) == count_formula_bars(fixed)


def test_reset_keeps_the_parameter_values() -> None:
    indicator = FormulaIndicator("mean(close, days)", {"days": 2})
    indicator.reset()
    for index, close in enumerate([1.0, 2.0, 4.0]):
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))

    assert indicator.value == 3.0


@pytest.mark.parametrize(
    ("closes", "quantile", "expected"),
    [
        ([9, 1, 5, 3, 7], 0.5, 5.0),
        ([9, 1, 5, 3, 7], 0, 1.0),
        ([9, 1, 5, 3, 7], 1, 9.0),
        ([9, 1, 5, 3, 7], 0.25, 3.0),
        ([9, 1, 5, 3, 7], 0.9, 8.2),
        ([4, 4, 4, 4, 4], 0.3, 4.0),
    ],
)
def test_quantile_interpolates_between_the_2_nearest_values(
    closes: list[float], quantile: float, expected: float
) -> None:
    assert calculate(f"quantile(close, 5, {quantile})", closes) == pytest.approx(expected)


def test_quantile_follows_the_window() -> None:
    closes = [float(index * 37 % 101) for index in range(300)]
    indicator = FormulaIndicator("quantile(close, 7, 0.35)")
    for index, close in enumerate(closes):
        indicator.handle_bar(make_nautilus_bar(make_bar(close, index=index)))
        if index >= 6:
            window = sorted(closes[index - 6 : index + 1])
            position = 0.35 * 6
            below, above = window[int(position)], window[int(position) + 1]
            assert indicator.value == pytest.approx(below + (above - below) * (position - int(position)))


@pytest.mark.parametrize("window", [1, 4, 5])
def test_median_is_the_quantile_of_one_half(window: int) -> None:
    closes = [9.0, 1.0, 5.0, 3.0, 7.0, 2.0]

    median = calculate(f"median(close, {window})", closes)

    assert median == calculate(f"quantile(close, {window}, 0.5)", closes)
    assert median == statistics.median(closes[-window:])


def test_variables_give_the_value_of_the_expression_without_them() -> None:
    with_variables = f"""
        width = {WIDTH}
        usual = mean(width, 60)
        (width - usual) / (width + usual)
    """.replace("        ", "")

    assert check_expression(with_variables) == []
    assert calculate(with_variables, CLOSES) == calculate(RELATIVE_WIDTH, CLOSES)
    assert calculate("a = close * 2; b = a + 1; b - a", [3.0]) == 1.0


def test_a_variable_counts_its_windows_1_time() -> None:
    # 11 uses of 1 window of 1000 bars. Without the variable, the 11 windows are over the limit.
    uses = " + ".join(["long"] * 11)

    assert check_expression(f"long = mean(close, 1000)\n{uses}") == []
    assert check_expression(uses.replace("long", "mean(close, 1000)")) != []
    assert count_formula_bars("a = lag(close, 5); mean(a, 20)") == 25


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("a = close", "last line must be the value"),
        ("a = close; close", "does not use the variable 'a'"),
        ("a = a + 1; a", "Unknown name 'a'"),
        ("a = close; a = open; a", "The name 'a' is in use"),
        ("close = open; close", "The name 'close' is in use"),
        ("a = b = close; a + b", "1 name to 1 value"),
        ("a, b = close, open; a", "1 name to 1 value"),
        ("a += close; a", "must give a name to a value"),
        ("import os; close", "must give a name to a value"),
        ("a = close\nb", "Line 2, column 1: Unknown name 'b'"),
        ("quantile(close, 5)", "quantile needs 3 arguments"),
        ("quantile(close, 5, 1.5)", "quantile must be a number from 0 to 1"),
        ("quantile(close, 5, close)", "quantile must be a number from 0 to 1"),
        ("median(close, 5, 0.5)", "median needs 2 arguments"),
        ("median(close, 0)", "from 1 to 1000"),
    ],
)
def test_refuses_the_variables_and_the_quantile(expression: str, message: str) -> None:
    problems = check_expression(expression)

    assert len(problems) == 1
    assert message in problems[0].message, problems[0].message


def make_parameter(
    name: str, minimum: float, default: float, maximum: float, value_type: type[int | float] = int
) -> IndicatorParameter:
    return IndicatorParameter(name, value_type, default, minimum, maximum)


@pytest.mark.parametrize(
    ("expression", "parameter", "message"),
    [
        ("mean(close, days)", None, "Column 13: Unknown name 'days'"),
        ("close", make_parameter("days", 5, 60, 250), "does not use the parameter 'days'"),
        (
            "mean(close, days)",
            make_parameter("days", 5.0, 60.0, 250.0, float),
            "the parameter 'days' is not an integer",
        ),
        ("mean(close, days)", make_parameter("days", 0, 60, 250), "from 1 to 1000, but the parameter 'days' is from 0"),
        (
            "mean(close, days)",
            make_parameter("days", 5, 60, 1001),
            "from 1 to 1000, but the parameter 'days' is from 5",
        ),
        ("std(close, days)", make_parameter("days", 1, 60, 250), "from 2 to 1000"),
        ("rsi(days)", make_parameter("days", 1, 14, 2000), "period must be from 1 to 1000"),
        ("rsi(days)", make_parameter("days", 1.0, 14.0, 20.0, float), "period must be an integer"),
        ("quantile(close, 5, days)", make_parameter("days", 0, 1, 2), "quantile must be from 0 to 1"),
        ("close ** days", make_parameter("days", 1, 2, 3), "exponent must be a number"),
        ("days = close; days", make_parameter("days", 1, 2, 3), "The name 'days' is in use"),
        ('macd(days, 26, output="value")', make_parameter("days", 5, 12, 30), "must be less than"),
        # 10 windows at the maximum are over the calculation limit. The default is under it.
        (" + ".join(["mean(close, days)"] * 11), make_parameter("days", 5, 60, 1000), "Window bars x bars read"),
    ],
)
def test_refuses_the_use_of_a_parameter(expression: str, parameter: IndicatorParameter | None, message: str) -> None:
    problems = check_expression(expression, () if parameter is None else (parameter,))

    assert len(problems) == 1
    assert message in problems[0].message, problems[0].message


def test_accepts_a_parameter_in_each_place_of_a_number() -> None:
    parameters = (
        make_parameter("days", 5, 60, 250),
        make_parameter("factor", 0.1, 2.0, 10.0, float),
        make_parameter("part", 0.0, 0.5, 1.0, float),
    )
    expression = 'quantile(lag(close, days), days, part) * factor + bollinger_bands(days, factor, output="upper")'

    assert check_expression(expression, parameters) == []


@pytest.mark.parametrize("value", [True, "20", None, float("nan"), float("inf"), 10**400])
def test_the_class_refuses_a_parameter_value_that_is_not_a_number(value: object) -> None:
    with pytest.raises(ValueError, match="The parameter 'days' must be a number"):
        FormulaIndicator("mean(close, days)", {"days": value})  # pyright: ignore[reportArgumentType]


def test_the_class_refuses_a_parameter_value_that_the_expression_cannot_use() -> None:
    with pytest.raises(ValueError, match="from 1 to 1000"):
        FormulaIndicator("mean(close, days)", {"days": 0})
    with pytest.raises(ValueError, match="does not use the parameter 'other'"):
        FormulaIndicator("mean(close, days)", {"days": 5, "other": 1})
