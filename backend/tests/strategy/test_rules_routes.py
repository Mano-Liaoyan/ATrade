"""The rule builder routes: the code from the rules, and a version save with rules (strategy.md section 9.6, #172)."""

import httpx
import pytest

from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.strategy.rules_examples import Json, condition, group, indicator, make_full_rules, make_rules, number, price

RSI_RULES = make_rules(group("all_of", condition(indicator("rsi", period=14), "below", number(30))))
WRONG_RULES = make_rules(group("all_of", condition(indicator("vwap"), "above", number(1))))


async def create_strategy(web_client: httpx.AsyncClient) -> int:
    return (await web_client.post("/api/strategies", json={"name": "Rules"})).json()["id"]


async def save(web_client: httpx.AsyncClient, strategy_id: int, body: Json) -> httpx.Response:
    return await web_client.post(f"/api/strategies/{strategy_id}/versions", json=body)


@pytest.mark.anyio
async def test_the_code_route_returns_the_code_of_the_rules(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategy-rules/code", json={"rules": make_full_rules()})

    assert response.status_code == 200
    assert response.json() == {"code": make_rules_code(StrategyRules.model_validate(make_full_rules()))}


@pytest.mark.anyio
async def test_the_code_route_refuses_rules_that_do_not_match_the_format(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategy-rules/code", json={"rules": WRONG_RULES})

    assert response.status_code == 422
    assert "Unknown indicator 'vwap'" in response.text


@pytest.mark.anyio
async def test_a_rules_save_makes_a_rule_builder_version_with_the_code_and_the_rules(
    web_client: httpx.AsyncClient,
) -> None:
    strategy_id = await create_strategy(web_client)

    response = await save(web_client, strategy_id, {"rules": RSI_RULES})

    assert response.status_code == 201
    version = response.json()
    assert version["version_number"] == 2
    assert version["source"] == "rule_builder"
    assert version["code"] == make_rules_code(StrategyRules.model_validate(RSI_RULES))
    saved = (await web_client.get(f"/api/strategies/{strategy_id}/versions/2")).json()
    assert saved["rules"] == StrategyRules.model_validate(RSI_RULES).model_dump(mode="json")


@pytest.mark.anyio
async def test_the_same_code_and_rules_make_no_new_version(web_client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(web_client)
    first = await save(web_client, strategy_id, {"rules": RSI_RULES})

    second = await save(web_client, strategy_id, {"rules": RSI_RULES})

    assert second.status_code == 200
    assert second.json() == first.json()


@pytest.mark.anyio
async def test_the_same_code_with_other_rules_makes_a_new_version(web_client: httpx.AsyncClient) -> None:
    # A template ID changes the rules but not the code (#175 adds the template docstring).
    strategy_id = await create_strategy(web_client)
    await save(web_client, strategy_id, {"rules": RSI_RULES})
    other_rules = {**RSI_RULES, "settings": {**RSI_RULES["settings"], "template_id": "s1"}}

    response = await save(web_client, strategy_id, {"rules": other_rules})

    assert response.status_code == 201
    assert response.json()["version_number"] == 3


@pytest.mark.anyio
async def test_the_code_of_a_rules_version_saved_as_code_makes_no_new_version(web_client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(web_client)
    rules_version = (await save(web_client, strategy_id, {"rules": RSI_RULES})).json()

    response = await save(web_client, strategy_id, {"code": rules_version["code"]})

    assert response.status_code == 200
    assert response.json()["source"] == "rule_builder"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        {"code": "x = 1", "rules": make_rules()},
        {},
        {"rules": WRONG_RULES},
        {"rules": make_rules(group("all_of", condition(price(), "equals", number(1))))},
    ],
    ids=["code and rules", "neither", "unknown indicator", "unknown comparison"],
)
async def test_a_save_refuses_a_wrong_body(web_client: httpx.AsyncClient, body: Json) -> None:
    strategy_id = await create_strategy(web_client)

    response = await save(web_client, strategy_id, body)

    assert response.status_code == 422
    strategy = (await web_client.get(f"/api/strategies/{strategy_id}")).json()
    assert [version["version_number"] for version in strategy["versions"]] == [1]
