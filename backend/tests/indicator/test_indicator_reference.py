"""Stored indicator references (docs/architecture/indicator.md section 23.6, #163)."""

import pytest

from atrade.indicator import (
    MACD,
    RSI,
    IndicatorProblem,
    check_indicator_reference,
    create_indicator,
    find_indicator_definition,
)


def test_a_correct_reference_has_no_problems() -> None:
    reference = {"indicator": "rsi", "parameters": {"period": 14}, "output": "value"}

    assert check_indicator_reference(reference) == []


def test_a_missing_parameter_gets_its_default() -> None:
    indicator = create_indicator({"indicator": "macd", "parameters": {"fast_period": 5}, "output": "signal"})

    assert check_indicator_reference({"indicator": "rsi"}) == []
    assert isinstance(create_indicator({"indicator": "rsi"}), RSI)
    assert isinstance(indicator, MACD)
    assert (indicator.fast_period, indicator.slow_period, indicator.signal_period) == (5, 26, 9)


def test_an_unknown_key_is_a_problem() -> None:
    problems = check_indicator_reference({"indicator": "vwap", "parameters": {"period": 14}})

    assert [problem.location for problem in problems] == [("indicator",)]
    assert problems[0].message.startswith("Unknown indicator 'vwap'.")


def test_an_unknown_parameter_is_a_problem() -> None:
    assert check_indicator_reference({"indicator": "sma", "parameters": {"length": 50}}) == [
        IndicatorProblem(("parameters", "length"), "Unknown parameter 'length' of SMA. Known parameters: period.")
    ]


@pytest.mark.parametrize(
    ("parameters", "location", "message"),
    [
        ({"period": 0}, ("parameters", "period"), "The period must be from 1 to 1000, not 0."),
        ({"period": 1001}, ("parameters", "period"), "The period must be from 1 to 1000, not 1001."),
        ({"k": 0.05}, ("parameters", "k"), "The k must be from 0.1 to 10.0, not 0.05."),
        ({"period": 20.5}, ("parameters", "period"), "The period must be an integer, not 20.5."),
        ({"period": True}, ("parameters", "period"), "The period must be an integer, not True."),
        ({"k": "2"}, ("parameters", "k"), "The k must be a number, not '2'."),
    ],
)
def test_a_parameter_out_of_its_range_is_a_problem(
    parameters: dict[str, object], location: tuple[str, ...], message: str
) -> None:
    reference = {"indicator": "bollinger_bands", "parameters": parameters, "output": "upper"}

    assert check_indicator_reference(reference) == [IndicatorProblem(location, message)]


@pytest.mark.parametrize(
    ("reference", "problem"),
    [
        (
            {"indicator": "momentum_12_1", "parameters": {"look_back": 21}},
            IndicatorProblem(("parameters", "skip"), "The skip must be less than the look_back (21), not 21."),
        ),
        (
            {"indicator": "macd", "parameters": {"fast_period": 30}, "output": "value"},
            IndicatorProblem(
                ("parameters", "fast_period"), "The fast_period must be less than the slow_period (26), not 30."
            ),
        ),
    ],
)
def test_a_parameter_order_rule_is_a_problem(reference: dict[str, object], problem: IndicatorProblem) -> None:
    assert check_indicator_reference(reference) == [problem]


@pytest.mark.parametrize("key", ["macd", "bollinger_bands", "donchian_channel"])
def test_a_multi_line_indicator_without_an_output_is_a_problem(key: str) -> None:
    problems = check_indicator_reference({"indicator": key})

    assert [problem.location for problem in problems] == [("output",)]
    assert "needs an output" in problems[0].message


def test_an_unknown_output_is_a_problem() -> None:
    assert check_indicator_reference({"indicator": "donchian_channel", "output": "value"}) == [
        IndicatorProblem(
            ("output",), "Unknown output 'value' of Donchian channel. Known outputs: upper, middle, lower."
        )
    ]


@pytest.mark.parametrize(
    ("reference", "location"),
    [
        (["rsi"], ()),
        ({"indicator": "rsi", "parameters": [14]}, ("parameters",)),
        ({"indicator": "rsi", "outputs": "value"}, ("outputs",)),
    ],
)
def test_a_reference_with_a_wrong_shape_is_a_problem(reference: object, location: tuple[str, ...]) -> None:
    assert [problem.location for problem in check_indicator_reference(reference)] == [location]


def test_create_indicator_refuses_a_reference_with_problems() -> None:
    with pytest.raises(ValueError, match=r"The period must be from 1 to 1000, not 0\."):
        create_indicator({"indicator": "rsi", "parameters": {"period": 0}})


def test_a_chart_reference_has_no_output_and_names_all_outputs() -> None:
    reference = {"indicator": "bollinger_bands", "parameters": {"period": 20}}

    assert check_indicator_reference(reference, has_output=False) == []
    assert check_indicator_reference({**reference, "output": "upper"}, has_output=False) == [
        IndicatorProblem(("output",), "Unknown field 'output'. Known fields: indicator, parameters.")
    ]
    assert create_indicator(reference, has_output=False).initialized is False


FORMULA = {"name": "Ratio", "expression": "close / sma(5)", "chart_placement": "own"}
CUSTOM_REFERENCE = {"indicator": "custom_3", "parameters": {}, "output": "value", "formula": FORMULA}


def test_a_reference_to_a_custom_indicator_holds_its_formula() -> None:
    assert check_indicator_reference(CUSTOM_REFERENCE) == []
    assert create_indicator(CUSTOM_REFERENCE).initialized is False


def test_a_chart_reference_to_a_custom_indicator_has_no_output() -> None:
    reference = {"indicator": "custom_3", "formula": FORMULA}
    assert check_indicator_reference(reference, has_output=False) == []


def test_the_definition_of_a_formula_has_the_look_back_of_the_expression() -> None:
    definition = find_indicator_definition(CUSTOM_REFERENCE)
    assert definition.display_name({}) == "Ratio"
    assert definition.screen_look_back_bars({}) == 5
    assert definition.outputs == ("value",)


@pytest.mark.parametrize(
    ("reference", "location"),
    [
        ({"indicator": "custom_3"}, ("formula",)),
        ({"indicator": "custom_3", "formula": {**FORMULA, "expression": "foo"}}, ("formula", "expression")),
        ({"indicator": "custom_3", "formula": {**FORMULA, "expression": 3}}, ("formula", "expression")),
        ({"indicator": "custom_3", "formula": {**FORMULA, "name": ""}}, ("formula", "name")),
        ({"indicator": "custom_3", "formula": {**FORMULA, "chart_placement": "x"}}, ("formula", "chart_placement")),
        ({"indicator": "custom_3", "formula": {**FORMULA, "extra": 1}}, ("formula", "extra")),
        ({"indicator": "custom_3", "formula": FORMULA, "parameters": {"period": 1}}, ("parameters", "period")),
        ({"indicator": "custom_3", "formula": FORMULA, "output": "upper"}, ("output",)),
        ({"indicator": "sma", "formula": FORMULA}, ("formula",)),
        ({"indicator": "custom_x", "formula": FORMULA}, ("formula",)),
    ],
)
def test_refuses_a_wrong_reference_to_a_custom_indicator(
    reference: dict[str, object], location: tuple[str, ...]
) -> None:
    assert location in [problem.location for problem in check_indicator_reference(reference)]


LOOKBACK = {
    "name": "lookback_days",
    "label": "Look-back days",
    "value_type": "int",
    "default": 60,
    "minimum": 5,
    "maximum": 250,
    "description": "",
}
PARAMETER_FORMULA = {
    "name": "Mean close",
    "expression": "mean(close, lookback_days)",
    "chart_placement": "price",
    "parameters": [LOOKBACK],
}


def make_parameter_reference(values: object = None, **formula: object) -> dict[str, object]:
    reference: dict[str, object] = {"indicator": "custom_3", "formula": {**PARAMETER_FORMULA, **formula}}
    return reference if values is None else {**reference, "parameters": values}


def test_a_custom_indicator_has_the_parameters_of_its_formula() -> None:
    reference = make_parameter_reference({"lookback_days": 20})
    definition = find_indicator_definition(reference)

    assert check_indicator_reference(reference) == []
    assert [(parameter.name, parameter.default, parameter.label) for parameter in definition.parameters] == [
        ("lookback_days", 60, "Look-back days")
    ]
    assert definition.display_name({"lookback_days": 20}) == "Mean close(20)"
    assert definition.screen_look_back_bars({"lookback_days": 20}) == 20
    assert definition.screen_look_back_bars({}) == 60
    assert create_indicator(make_parameter_reference()).parameters == {"lookback_days": 60}  # pyright: ignore[reportAttributeAccessIssue]
    assert create_indicator(reference).parameters == {"lookback_days": 20}  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ("reference", "location", "message"),
    [
        (make_parameter_reference({"lookback_days": 4}), ("parameters", "lookback_days"), "from 5 to 250"),
        (make_parameter_reference({"lookback_days": 20.5}), ("parameters", "lookback_days"), "must be an integer"),
        (make_parameter_reference({"days": 20}), ("parameters", "days"), "Unknown parameter 'days'"),
        (make_parameter_reference(parameters=3), ("formula", "parameters"), "must be a list"),
        (make_parameter_reference(parameters=[3]), ("formula", "parameters", "0"), "must be an object"),
        (make_parameter_reference(parameters=[LOOKBACK] * 2), ("formula", "parameters", "1", "name"), "2 times"),
        (make_parameter_reference(parameters=[LOOKBACK] * 11), ("formula", "parameters"), "at most 10 parameters"),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "extra": 1}]),
            ("formula", "parameters", "0", "extra"),
            "Unknown field 'extra'",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "name": "Days"}]),
            ("formula", "parameters", "0", "name"),
            "lower-case letter",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "name": "close"}]),
            ("formula", "parameters", "0", "name"),
            "is a bar field or a function",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "name": "median"}]),
            ("formula", "parameters", "0", "name"),
            "is a bar field or a function",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "label": ""}]),
            ("formula", "parameters", "0", "label"),
            "1 to 60 characters",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "description": "x" * 201}]),
            ("formula", "parameters", "0", "description"),
            "0 to 200 characters",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "value_type": "text"}]),
            ("formula", "parameters", "0", "value_type"),
            "`int` or `float`",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "default": 60.5}]),
            ("formula", "parameters", "0", "default"),
            "must be an integer",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "maximum": True}]),
            ("formula", "parameters", "0", "maximum"),
            "must be an integer",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "value_type": "float", "maximum": 1e16}]),
            ("formula", "parameters", "0", "maximum"),
            "from -1e15 to 1e15",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "default": 4}]),
            ("formula", "parameters", "0", "default"),
            "from the minimum (5) to the maximum (250)",
        ),
        (
            make_parameter_reference(parameters=[{**LOOKBACK, "maximum": 1001}]),
            ("formula", "expression"),
            "the parameter 'lookback_days' is from 5 to 1001",
        ),
        (make_parameter_reference(expression="close"), ("formula", "expression"), "does not use the parameter"),
        (make_parameter_reference(parameters=[]), ("formula", "expression"), "Unknown name 'lookback_days'"),
    ],
)
def test_a_wrong_parameter_of_a_custom_indicator_is_a_problem(
    reference: dict[str, object], location: tuple[str, ...], message: str
) -> None:
    problems = check_indicator_reference(reference, has_output=False)

    assert [problem.location for problem in problems] == [location]
    assert message in problems[0].message


def test_parameter_values_that_the_expression_cannot_use_together_are_a_problem() -> None:
    fast = {**LOOKBACK, "name": "fast", "default": 12, "maximum": 20}
    slow = {**LOOKBACK, "name": "slow", "default": 26, "minimum": 10}
    reference = make_parameter_reference(expression='macd(fast, slow, output="value")', parameters=[fast, slow])

    assert check_indicator_reference(reference, has_output=False) == []
    problems = check_indicator_reference({**reference, "parameters": {"fast": 20, "slow": 15}}, has_output=False)
    assert [problem.location for problem in problems] == [("parameters",)]
    assert "must be less than" in problems[0].message
