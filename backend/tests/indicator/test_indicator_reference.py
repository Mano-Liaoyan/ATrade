"""Stored indicator references (docs/architecture/indicator.md section 23.6, #163)."""

import pytest

from atrade.indicator import MACD, RSI, IndicatorProblem, check_indicator_reference, create_indicator


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
