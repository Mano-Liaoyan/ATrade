"""The universe mode of the rule builder (docs/architecture/strategy.md section 9.8.6, #201)."""

import httpx
import pytest

from atrade.strategy.code_checks import check_strategy_code
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.strategy.rules_examples import Json, condition, group, indicator, make_universe_rules, number, price


@pytest.mark.anyio
async def test_the_code_route_accepts_universe_settings(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategy-rules/code", json={"rules": make_universe_rules()})

    assert response.status_code == 200, response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "universe",
    [
        {"rank_indicator": indicator("vwap")},
        {"hold_count": 0},
        {"rebalance_period": "daily"},
        {"rank_direction": "sideways"},
    ],
    ids=["unknown rank indicator", "N below 1", "unknown rebalance period", "unknown direction"],
)
async def test_the_code_route_refuses_wrong_universe_settings(web_client: httpx.AsyncClient, universe: Json) -> None:
    response = await web_client.post("/api/strategy-rules/code", json={"rules": make_universe_rules(**universe)})

    assert response.status_code == 422


def test_the_same_universe_rules_give_the_same_code() -> None:
    rules = make_universe_rules(
        group("all_of", condition(price(), "above", indicator("sma", period=20))),
        exits={"stop_loss_percent": 5, "exit_after_bars": 3, "exit_when_entry_is_false": True},
    )

    assert make_rules_code(StrategyRules.model_validate(rules)) == make_rules_code(StrategyRules.model_validate(rules))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "rules",
    [
        make_universe_rules(),
        make_universe_rules(
            group("any_of", condition(price(), "crosses_above", indicator("sma", period=20))),
            exits={
                "stop_loss_percent": 5,
                "take_profit_percent": 10,
                "exit_after_bars": 3,
                "exit_when_entry_is_false": True,
                "exit_group": group("all_of", condition(indicator("rsi"), "above", number(70))),
            },
            rank_indicator=indicator("bollinger_bands", "upper"),
            rank_direction="low_to_high",
        ),
    ],
    ids=["empty filter", "all exit items"],
)
async def test_the_universe_code_passes_the_checks_before_save(rules: Json) -> None:
    assert await check_strategy_code(make_rules_code(StrategyRules.model_validate(rules))) == []
