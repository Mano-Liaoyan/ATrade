"""Chart indicators in the strategy code (docs/architecture/strategy.md sections 9.2, 9.3, and 9.8.3, #334).

`CHART_INDICATORS` names the indicators of the bar chart of a backtest or a forward test of the version
(docs/architecture/indicator.md section 23.9.8). The checks before save refuse a wrong `CHART_INDICATORS`, and
`list_chart_indicators` reads it without running the code.
"""

import ast

import httpx
import pytest

from atrade.strategy import StrategyVersion, list_chart_indicators, list_version_chart_indicators
from atrade.strategy.code_checks import CodeProblem, check_strategy_code
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.strategy_templates import STRATEGY_TEMPLATES
from tests.strategy.rules_examples import condition, group, indicator, make_rules, make_universe_rules, price

CODE_HEAD = """from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy


class ChartConfig(StrategyConfig):
    def __init__(
        self,
        *,
        average_period: int = 30,
        band_width: float = 2.5,
        is_short: bool = False,
        name: str = "a",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.average_period = average_period
        self.band_width = band_width
        self.is_short = is_short
        self.name = name


class ChartStrategy(Strategy):
    pass


"""
# CHART_INDICATORS starts at this line of the code.
CHART_LINE = CODE_HEAD.count("\n") + 1


def make_code(chart_indicators: str) -> str:
    return CODE_HEAD + chart_indicators + "\n"


async def check_chart(chart_indicators: str) -> list[CodeProblem]:
    return await check_strategy_code(make_code(chart_indicators))


@pytest.mark.anyio
async def test_correct_chart_indicators_pass_the_checks() -> None:
    chart_indicators = """CHART_INDICATORS = [
    {"indicator": "sma", "parameters": {"period": "average_period"}},
    {"indicator": "bollinger_bands", "parameters": {"period": 20, "k": "band_width"}},
    {"indicator": "rsi", "parameters": {}},
]"""

    assert await check_chart(chart_indicators) == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("chart_indicators", "line", "message"),
    [
        (
            'CHART_INDICATORS = {"indicator": "sma"}',
            CHART_LINE,
            "CHART_INDICATORS must be a list literal of dict literals.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {}},\n    "sma",\n]',
            CHART_LINE + 2,
            "CHART_INDICATORS item 2 must be a dict literal with the keys 'indicator' and 'parameters'.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": 5, "parameters": {}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: the indicator must be a string literal.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": dict(period=20)},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: the parameters must be a dict literal with string keys.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "output": "value"},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: Unknown field 'output'. Known fields: indicator, parameters.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": 10 + 10}},\n]',
            CHART_LINE + 1,
            (
                "CHART_INDICATORS item 1: a parameter value must be an int or float literal or the name of a "
                "configuration field."
            ),
        ),
        (
            'CHART_INDICATORS = [{"indicator": "vwap", "parameters": {}}]',
            CHART_LINE,
            (
                "CHART_INDICATORS item 1: Unknown indicator 'vwap'. Known indicators: sma, ema, momentum_12_1, "
                "distance_to_52_week_high, realized_volatility, atr, average_trading_value, rsi, macd, "
                "bollinger_bands, donchian_channel, adr_percent."
            ),
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"length": 20}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: Unknown parameter 'length' of SMA. Known parameters: period.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": 0}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: The period must be from 1 to 1000, not 0.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "macd", "parameters": {"fast_period": 30}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: The fast_period must be less than the slow_period (26), not 30.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": "slow_period"}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: 'slow_period' is not a configuration field with an int or float default.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": "name"}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: 'name' is not a configuration field with an int or float default.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": "is_short"}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: 'is_short' is not a configuration field with an int or float default.",
        ),
        (
            'CHART_INDICATORS = [\n    {"indicator": "sma", "parameters": {"period": "band_width"}},\n]',
            CHART_LINE + 1,
            "CHART_INDICATORS item 1: The period must be an integer, not 2.5.",
        ),
    ],
)
async def test_wrong_chart_indicators_block_the_save_with_a_line(
    chart_indicators: str, line: int, message: str
) -> None:
    assert await check_chart(chart_indicators) == [CodeProblem(line=line, message=message)]


@pytest.mark.anyio
async def test_the_save_route_refuses_wrong_chart_indicators(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Chart"})).json()
    code = make_code('CHART_INDICATORS = [{"indicator": "vwap", "parameters": {}}]')

    response = await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})

    assert response.status_code == 422
    assert response.json()["problems"][0]["line"] == CHART_LINE


def test_list_chart_indicators_keeps_the_numbers_and_replaces_field_names_with_defaults() -> None:
    code = make_code(
        """CHART_INDICATORS = [
    {"indicator": "sma", "parameters": {"period": "average_period"}},
    {"indicator": "bollinger_bands", "parameters": {"period": 20, "k": "band_width"}},
    {"indicator": "rsi", "parameters": {}},
]"""
    )

    assert list_chart_indicators(code, {}) == [
        {"indicator": "sma", "parameters": {"period": 30}},
        {"indicator": "bollinger_bands", "parameters": {"period": 20, "k": 2.5}},
        {"indicator": "rsi", "parameters": {}},
    ]


def test_list_chart_indicators_uses_the_parameters_of_a_sweep_run() -> None:
    code = make_code('CHART_INDICATORS = [{"indicator": "sma", "parameters": {"period": "average_period"}}]')

    assert list_chart_indicators(code, {"average_period": 55, "band_width": 3.0}) == [
        {"indicator": "sma", "parameters": {"period": 55}},
    ]


def test_list_chart_indicators_is_empty_without_chart_indicators() -> None:
    assert list_chart_indicators(CODE_HEAD, {}) == []


def test_list_chart_indicators_is_empty_for_code_with_a_syntax_error() -> None:
    assert list_chart_indicators("def broken(:\n", {}) == []


def test_list_version_chart_indicators_reads_the_code_of_the_version() -> None:
    code = make_code('CHART_INDICATORS = [{"indicator": "sma", "parameters": {"period": "average_period"}}]')
    version = StrategyVersion(id=1, strategy_id=1, strategy_name="Chart", version_number=1, code=code)

    assert list_version_chart_indicators(version, {"average_period": 55}) == [
        {"indicator": "sma", "parameters": {"period": 55}},
    ]


def test_list_version_chart_indicators_is_empty_without_a_version() -> None:
    assert list_version_chart_indicators(None, {}) == []


def test_list_chart_indicators_leaves_out_an_item_that_a_sweep_run_makes_wrong() -> None:
    code = make_code(
        """CHART_INDICATORS = [
    {"indicator": "sma", "parameters": {"period": "average_period"}},
    {"indicator": "rsi", "parameters": {"period": 14}},
]"""
    )

    assert list_chart_indicators(code, {"average_period": 0}) == [{"indicator": "rsi", "parameters": {"period": 14}}]


START_CODES = {
    "blank_code": STRATEGY_TEMPLATE,
    **{
        template.id: template.code if template.rules is None else make_rules_code(template.rules)
        for template in STRATEGY_TEMPLATES
    },
}


@pytest.mark.anyio
@pytest.mark.parametrize("start_from", START_CODES)
async def test_each_start_point_and_template_has_chart_indicators_that_pass_the_checks(start_from: str) -> None:
    code = START_CODES[start_from]
    assert code is not None

    assert await check_strategy_code(code) == []
    assert list_chart_indicators(code, {}) != []


def test_the_blank_code_shows_its_moving_average() -> None:
    assert list_chart_indicators(STRATEGY_TEMPLATE, {"average_period": 40}) == [
        {"indicator": "sma", "parameters": {"period": 40}},
    ]


def read_chart_indicators_literal(code: str) -> object:
    for node in ast.parse(code).body:
        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "CHART_INDICATORS":
            return ast.literal_eval(node.value)
    return None


def test_the_rules_code_names_each_indicator_object_once_in_the_order_of_first_use() -> None:
    entry = group(
        "all_of",
        condition(indicator("rsi", period=14), "below", indicator("sma", period=20)),
        condition(price("close"), "above", indicator("sma", period=20)),
        condition(indicator("macd", "signal", fast_period=12), "above", indicator("macd", "value", fast_period=12)),
    )
    rules = make_rules(entry, exits={"exit_group": group("any_of", condition(price(), "below", indicator("rsi")))})

    code = make_rules_code(StrategyRules.model_validate(rules))

    assert read_chart_indicators_literal(code) == [
        {"indicator": "rsi", "parameters": {"period": "rsi_1_period"}},
        {"indicator": "sma", "parameters": {"period": "sma_2_period"}},
        {
            "indicator": "macd",
            "parameters": {
                "fast_period": "macd_3_fast_period",
                "slow_period": "macd_3_slow_period",
                "signal_period": "macd_3_signal_period",
            },
        },
    ]
    assert list_chart_indicators(code, {"sma_2_period": 50})[1] == {"indicator": "sma", "parameters": {"period": 50}}


def test_rules_without_indicators_have_empty_chart_indicators() -> None:
    code = make_rules_code(StrategyRules.model_validate(make_rules()))

    assert read_chart_indicators_literal(code) == []


@pytest.mark.anyio
async def test_the_universe_code_has_chart_indicators_that_pass_the_checks() -> None:
    code = make_rules_code(StrategyRules.model_validate(make_universe_rules()))

    assert await check_strategy_code(code) == []
    assert list_chart_indicators(code, {}) == [
        {"indicator": "momentum_12_1", "parameters": {"look_back": 252, "skip": 21}},
    ]
