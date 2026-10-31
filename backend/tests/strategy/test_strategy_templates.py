"""The start points and the rule templates S1 to S3 (docs/architecture/strategy.md sections 9.6 and 9.9, #175)."""

from typing import get_args

import httpx
import pytest

from atrade.strategy.code_checks import check_strategy_code
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.strategy_templates import BLANK_RULES, STRATEGY_TEMPLATES, StartPoint, StrategyTemplate
from tests.strategy.rules_examples import Json, condition, group, indicator, make_rules, number, price

RULE_TEMPLATES = [template for template in STRATEGY_TEMPLATES if template.kind == "rules"]

S1_ENTRY = group("all_of", condition(price("close"), "above", indicator("sma", period=200)))
S2_ENTRY = group("all_of", condition(price("high"), "at_or_above", indicator("donchian_channel", "upper", period=50)))
S3_ENTRY = group("all_of", condition(indicator("momentum_12_1", look_back=252, skip=0), "above", number(0)))
NINETY_FIVE_PERCENT: Json = {"type": "percent_of_equity", "percent": 95}


def template_rules(template_id: str, entry: Json, exits: Json) -> Json:
    rules = make_rules(entry, exits=exits, position_size=NINETY_FIVE_PERCENT)
    rules["settings"]["template_id"] = template_id
    return StrategyRules.model_validate(rules).model_dump(mode="json")


EXPECTED_RULES = {
    "s1": template_rules("s1", S1_ENTRY, {"exit_when_entry_is_false": True}),
    "s2": template_rules("s2", S2_ENTRY, {"exit_after_bars": 10}),
    "s3": template_rules("s3", S3_ENTRY, {"exit_when_entry_is_false": True}),
}


async def create(web_client: httpx.AsyncClient, body: Json) -> httpx.Response:
    return await web_client.post("/api/strategies", json={"name": "Start", **body})


async def read_version_1(web_client: httpx.AsyncClient, strategy_id: int) -> Json:
    return (await web_client.get(f"/api/strategies/{strategy_id}/versions/1")).json()


@pytest.mark.anyio
async def test_the_template_list_starts_with_s1_to_s3_in_the_order_of_the_spec(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/strategy-templates")

    assert response.status_code == 200
    templates = response.json()
    assert [(template["id"], template["name"]) for template in templates[:3]] == [
        ("s1", "200-day trend"),
        ("s2", "50-day range break"),
        ("s3", "12-month time-series momentum"),
    ]
    s1 = templates[0]
    assert set(s1) == {
        "id",
        "name",
        "kind",
        "entry",
        "exit",
        "defaults",
        "market",
        "bar_period",
        "evidence",
        "sources",
        "differs_from_source",
    }
    assert s1["kind"] == "rules"
    assert s1["entry"] == "Close above SMA"
    assert s1["exit"] == "Entry conditions no longer true"
    assert s1["defaults"] == "SMA 200"
    assert s1["bar_period"] == "1-DAY"
    assert s1["sources"] == [
        {"label": "Brock, Lakonishok & LeBaron 1992", "url": "https://doi.org/10.1111/j.1540-6261.1992.tb04681.x"},
        {"label": "Faber 2007", "url": "https://doi.org/10.3905/jwm.2007.674809"},
    ]
    assert [template["defaults"] for template in templates[1:3]] == [
        "Donchian 50, N = 10",
        "Look back 252 days, skip 0 days",
    ]


def test_the_start_points_are_the_blank_start_points_and_the_templates() -> None:
    assert get_args(StartPoint.__value__) == ("blank_code", "blank_rules", *(t.id for t in STRATEGY_TEMPLATES))


def test_each_template_has_only_rules_of_evidence_grade_a_or_b_for_its_market() -> None:
    for template in STRATEGY_TEMPLATES:
        assert template.evidence.startswith(("A", "B")), template.id
    for template in RULE_TEMPLATES:
        assert "index" in template.evidence, template.id
        assert template.market == "US index ETFs"


@pytest.mark.anyio
async def test_without_a_start_point_version_1_is_the_blank_code(web_client: httpx.AsyncClient) -> None:
    strategy = (await create(web_client, {})).json()

    version = await read_version_1(web_client, strategy["id"])

    assert (version["code"], version["source"], version["rules"]) == (STRATEGY_TEMPLATE, "user", None)


@pytest.mark.anyio
async def test_blank_code_makes_version_1_from_the_blank_code(web_client: httpx.AsyncClient) -> None:
    strategy = (await create(web_client, {"start_from": "blank_code"})).json()

    assert strategy["versions"][0]["source"] == "user"
    assert (await read_version_1(web_client, strategy["id"]))["code"] == STRATEGY_TEMPLATE


@pytest.mark.anyio
async def test_blank_rules_makes_version_1_from_rules_without_conditions(web_client: httpx.AsyncClient) -> None:
    strategy = (await create(web_client, {"start_from": "blank_rules"})).json()

    version = await read_version_1(web_client, strategy["id"])

    assert version["source"] == "rule_builder"
    assert version["rules"]["entry"] == {"type": "group", "match": "all_of", "items": []}
    assert version["rules"]["settings"] == {"position_size": NINETY_FIVE_PERCENT, "template_id": None}
    assert version["code"] == make_rules_code(StrategyRules.model_validate(version["rules"]))


@pytest.mark.anyio
@pytest.mark.parametrize("template_id", ["s1", "s2", "s3"])
async def test_a_template_makes_version_1_from_its_rules(web_client: httpx.AsyncClient, template_id: str) -> None:
    strategy = (await create(web_client, {"start_from": template_id})).json()

    version = await read_version_1(web_client, strategy["id"])

    assert version["source"] == "rule_builder"
    assert version["rules"] == EXPECTED_RULES[template_id]
    assert version["code"] == make_rules_code(StrategyRules.model_validate(EXPECTED_RULES[template_id]))


@pytest.mark.anyio
async def test_an_unknown_start_point_is_refused(web_client: httpx.AsyncClient) -> None:
    response = await create(web_client, {"start_from": "s9"})

    assert response.status_code == 422
    assert (await web_client.get("/api/strategies")).json() == []


@pytest.mark.parametrize("template", RULE_TEMPLATES, ids=lambda template: template.id)
def test_the_code_of_a_template_starts_with_its_docstring(template: StrategyTemplate) -> None:
    code = make_rules_code(StrategyRules.model_validate(EXPECTED_RULES[template.id]))

    docstring = code.split('"""')[1]
    assert code.startswith('"""')
    for part in (
        f"{template.id.upper()} {template.name}",
        "Sources:",
        "https://doi.org/",
        f"Evidence: {template.evidence}",
        "Market: US index ETFs",
        "Bar period: 1-DAY",
        "Differences from the sources:",
    ):
        assert part in docstring, part


@pytest.mark.anyio
@pytest.mark.parametrize("rules", [*EXPECTED_RULES.values(), BLANK_RULES.model_dump(mode="json")])
async def test_the_code_of_each_template_and_of_blank_rules_passes_the_checks(rules: Json) -> None:
    assert await check_strategy_code(make_rules_code(StrategyRules.model_validate(rules))) == []
