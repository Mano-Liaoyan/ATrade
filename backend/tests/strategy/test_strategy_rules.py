"""The rules format and the code from the rules (docs/architecture/strategy.md sections 9.8.2 and 9.8.3, #172)."""

import ast

import pytest
from pydantic import ValidationError

from atrade.strategy.code_checks import check_strategy_code
from atrade.strategy.rules_code import find_warm_up_bar_count, make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.strategy.rules_examples import (
    COMPARISONS,
    DAYS_PARAMETER,
    PRICES,
    Json,
    condition,
    custom_indicator,
    group,
    indicator,
    make_full_rules,
    make_rules,
    make_universe_rules,
    number,
    parameter_indicator,
    price,
)

ALL_LEFT_SIDES = [price(name) for name in PRICES] + [
    indicator(key)
    for key in (
        "sma",
        "ema",
        "momentum_12_1",
        "distance_to_52_week_high",
        "realized_volatility",
        "atr",
        "average_trading_value",
        "rsi",
        "adr_percent",
    )
]
MULTI_LINE_OUTPUTS = [("macd", output) for output in ("value", "signal", "histogram")] + [
    (key, output) for key in ("bollinger_bands", "donchian_channel") for output in ("upper", "middle", "lower")
]


def check(rules: Json) -> StrategyRules:
    return StrategyRules.model_validate(rules)


@pytest.mark.parametrize("left", ALL_LEFT_SIDES)
def test_each_left_side_is_accepted(left: Json) -> None:
    check(make_rules(group("all_of", condition(left, "above", number(1)))))


@pytest.mark.parametrize(("key", "output"), MULTI_LINE_OUTPUTS)
def test_each_line_of_a_multi_line_indicator_is_accepted(key: str, output: str) -> None:
    check(make_rules(group("all_of", condition(indicator(key, output), "below", number(1)))))


@pytest.mark.parametrize("comparison", COMPARISONS)
def test_each_comparison_is_accepted(comparison: str) -> None:
    check(make_rules(group("all_of", condition(price(), comparison, number(1)))))


@pytest.mark.parametrize("right", [number(30), number(0.5), price("high"), indicator("rsi", period=7)])
def test_each_right_side_is_accepted(right: Json) -> None:
    check(make_rules(group("all_of", condition(price(), "above", right))))


def test_one_nested_group_is_accepted() -> None:
    a, b, c = (condition(price(), "above", number(value)) for value in (1, 2, 3))
    check(make_rules(group("all_of", a, group("any_of", b, c))))


@pytest.mark.parametrize(
    "rules",
    [
        make_rules(group("all_of", group("any_of", group("all_of", condition(price(), "above", number(1)))))),
        make_rules(group("all_of", condition(indicator("vwap"), "above", number(1)))),
        make_rules(group("all_of", condition(price(), "equals", number(1)))),
        make_rules(group("all_of", condition(number(1), "above", price()))),
        make_rules(group("all_of", condition(indicator("macd"), "above", number(1)))),
        make_rules(group("all_of", condition(indicator("rsi", period=0), "above", number(1)))),
        make_rules(group("all_of", condition(price(), "above", number(True)))),
        make_rules(position_size={"type": "fixed_shares", "shares": 0}),
        make_rules(exits={"exit_after_bars": 0}),
        {**make_rules(), "format_version": 2},
        {**make_rules(), "extra": 1},
    ],
    ids=[
        "two nested groups",
        "unknown indicator",
        "unknown comparison",
        "number on the left",
        "multi-line indicator without a line",
        "parameter out of range",
        "boolean number",
        "zero shares",
        "zero bars",
        "unknown format version",
        "unknown field",
    ],
)
def test_rules_that_do_not_match_the_format_are_refused(rules: Json) -> None:
    with pytest.raises(ValidationError):
        check(rules)


def test_the_same_rules_give_the_same_code() -> None:
    first = make_rules_code(check(make_full_rules()))
    second = make_rules_code(check(make_full_rules()))

    assert first == second


@pytest.mark.anyio
@pytest.mark.parametrize("rules", [make_rules(), make_full_rules()], ids=["empty rules", "all condition kinds"])
async def test_the_code_passes_the_checks_before_save(rules: Json) -> None:
    assert await check_strategy_code(make_rules_code(check(rules))) == []


def read_config_fields(code: str) -> dict[str, tuple[str, object]]:
    """The keyword-only fields of the StrategyConfig `__init__`: name -> (annotation, default)."""
    config_class = next(
        node for node in ast.parse(code).body if isinstance(node, ast.ClassDef) and node.name == "RulesConfig"
    )
    init = next(node for node in config_class.body if isinstance(node, ast.FunctionDef))
    fields: dict[str, tuple[str, object]] = {}
    for argument, default in zip(init.args.kwonlyargs, init.args.kw_defaults, strict=True):
        assert argument.annotation is not None
        fields[argument.arg] = (
            ast.unparse(argument.annotation),
            None if default is None else ast.literal_eval(default),
        )
    return fields


def test_each_indicator_parameter_and_threshold_is_a_config_field_with_a_default() -> None:
    rules = make_rules(
        group(
            "all_of",
            condition(indicator("rsi", period=7), "below", number(30)),
            condition(indicator("bollinger_bands", "lower", k=2.5), "at_or_above", number(0.5)),
        )
    )

    fields = read_config_fields(make_rules_code(check(rules)))

    assert fields == {
        "instrument_id": ("InstrumentId", None),
        "bar_type": ("BarType", None),
        "rsi_1_period": ("int", 7),
        "threshold_1": ("int", 30),
        "bollinger_bands_2_period": ("int", 20),
        "bollinger_bands_2_k": ("float", 2.5),
        "threshold_2": ("float", 0.5),
        "position_shares": ("int", 10),
    }


def test_operands_with_the_same_indicator_and_parameters_share_one_indicator() -> None:
    rules = make_rules(
        group(
            "all_of",
            condition(price(), "above", indicator("sma", period=5)),
            condition(indicator("sma", period=5), "above", indicator("sma", period=10)),
        )
    )

    code = make_rules_code(check(rules))

    assert code.count("atrade.indicator.SMA(") == 2


def custom_rules(left: Json | None = None, right: Json | None = None) -> Json:
    return make_rules(group("all_of", condition(left or custom_indicator(), "above", right or number(1))))


def test_the_saved_json_of_rules_without_a_custom_indicator_has_no_formula_field() -> None:
    assert (
        "formula"
        not in check(make_rules(group("all_of", condition(indicator("rsi"), "above", number(1))))).model_dump_json()
    )


def test_a_custom_indicator_keeps_its_formula_in_the_saved_json() -> None:
    dumped = check(custom_rules()).model_dump(mode="json")
    assert dumped["entry"]["items"][0]["left"]["formula"]["expression"] == "close / sma(5)"


@pytest.mark.anyio
async def test_the_code_holds_the_expression_and_needs_no_database_read() -> None:
    code = make_rules_code(check(custom_rules()))
    assert "atrade.indicator.FormulaIndicator('close / sma(5)')" in code
    assert await check_strategy_code(code) == []


@pytest.mark.anyio
async def test_the_universe_code_holds_the_expression() -> None:
    rules = make_universe_rules(rank_indicator=custom_indicator())
    code = make_rules_code(check(rules))
    assert "atrade.indicator.FormulaIndicator('close / sma(5)')" in code
    assert await check_strategy_code(code) == []


def test_the_warm_up_is_the_look_back_of_the_expression() -> None:
    assert find_warm_up_bar_count(check(custom_rules(custom_indicator("mean(rsi(14), 5)")))) == 116


def test_a_text_in_the_expression_cannot_break_the_code() -> None:
    expression = 'macd(output="signal") + 1'
    code = make_rules_code(check(custom_rules(custom_indicator(expression))))
    assert ast.parse(code) is not None
    assert repr(expression) in code


def test_2_expressions_of_one_key_are_2_indicators() -> None:
    rules = custom_rules(custom_indicator("close"), custom_indicator("open"))
    code = make_rules_code(check(rules))
    assert "FormulaIndicator('close')" in code
    assert "FormulaIndicator('open')" in code


def test_a_wrong_formula_is_refused() -> None:
    with pytest.raises(ValidationError, match="Unknown function"):
        check(custom_rules(custom_indicator("__import__('os')")))


@pytest.mark.anyio
async def test_the_code_gives_the_parameters_of_a_custom_indicator_as_configuration_fields() -> None:
    rules = check(custom_rules(parameter_indicator(20), parameter_indicator()))
    code = make_rules_code(rules)

    assert "custom_3_1_days: int = 20" in code
    assert "custom_3_2_days: int = 5" in code
    assert (
        "atrade.indicator.FormulaIndicator('close / mean(close, days)', parameters={\"days\": config.custom_3_1_days})"
    ) in code
    assert await check_strategy_code(code) == []
    assert find_warm_up_bar_count(rules) == 20
    assert find_warm_up_bar_count(rules, {"custom_3_1_days": 30, "custom_3_2_days": 40}) == 40


def test_a_float_parameter_with_a_whole_number_is_a_float_configuration_field() -> None:
    factor = {**DAYS_PARAMETER, "name": "factor", "value_type": "float", "default": 2, "minimum": 1, "maximum": 5}
    operand = parameter_indicator()
    operand["formula"] = {**operand["formula"], "expression": "close * factor", "parameters": [factor]}
    bands = {"type": "indicator", "indicator": "bollinger_bands", "parameters": {"k": 2}, "output": "upper"}

    code = make_rules_code(check(custom_rules(operand, bands)))

    assert "custom_3_1_factor: float = 2.0" in code
    assert "bollinger_bands_2_k: float = 2.0" in code


def test_a_sweep_value_that_the_expression_cannot_use_gives_the_warm_up_of_the_defaults() -> None:
    rules = check(custom_rules(parameter_indicator(20)))

    assert find_warm_up_bar_count(rules, {"custom_3_1_days": 5000}) == 5
