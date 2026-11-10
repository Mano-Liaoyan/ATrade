"""The custom indicator routes and the catalog routes (docs/architecture/indicator.md section 23.10)."""

import json
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest

from atrade.indicator import IndicatorProblem, check_formula, check_indicator_reference
from atrade.market_data.indicator_series import IndicatorProblemResponse

BASE_PATH = "/api/custom-indicators"
JSON_HEADERS = {"content-type": "application/json"}
RATIO_EXPRESSION = "close / sma(50) - 1"
RATIO = {
    "name": "Distance to SMA",
    "expression": RATIO_EXPRESSION,
    "chart_placement": "own",
    "value_description": "The close over SMA(50), minus 1, as a fraction.",
}


async def create(client: httpx.AsyncClient, **fields: Any) -> dict[str, Any]:
    response = await client.post(BASE_PATH, json={**RATIO, **fields})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_create_gives_a_key_outside_the_built_in_keys_and_the_list_and_read_routes_show_it(
    web_client: httpx.AsyncClient,
) -> None:
    created = await create(web_client)
    assert created["key"] == f"custom_{created['custom_indicator_id']}"
    assert created["expression"] == RATIO_EXPRESSION

    assert (await web_client.get(BASE_PATH)).json() == [created]
    assert (await web_client.get(f"{BASE_PATH}/{created['custom_indicator_id']}")).json() == created


@pytest.mark.anyio
async def test_a_second_save_of_the_same_name_at_the_same_time_gives_409(
    web_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = await create(web_client, name="Other")
    await create(web_client)

    async def find_no_problem(*_arguments: object) -> list[IndicatorProblemResponse]:
        """The name check ran before the other save committed, so only the unique index sees the same name."""
        return []

    monkeypatch.setattr("atrade.market_data.custom_indicators.check_custom_indicator", find_no_problem)
    created = await web_client.post(BASE_PATH, json=RATIO)
    changed = await web_client.put(f"{BASE_PATH}/{other['custom_indicator_id']}", json=RATIO)

    for response in (created, changed):
        assert response.status_code == httpx.codes.CONFLICT, response.text
        assert response.json() == {"detail": f"A custom indicator with the name {RATIO['name']!r} exists."}


@pytest.mark.parametrize("path", ["/api/market-data/indicators", "/api/screen-indicators"])
@pytest.mark.anyio
async def test_the_catalog_routes_show_custom_indicators_after_the_built_in_indicators(
    web_client: httpx.AsyncClient, path: str
) -> None:
    created = await create(web_client)
    catalog = (await web_client.get(path)).json()

    assert catalog[-1] == {
        "key": created["key"],
        "name": "Distance to SMA",
        "short_name": "Distance to SMA",
        "chart_placement": "own",
        "parameters": [],
        "outputs": ["value"],
        "value_description": RATIO["value_description"],
        "formula": {"name": "Distance to SMA", "expression": RATIO_EXPRESSION, "chart_placement": "own"},
    }
    assert "formula" not in catalog[0]


@pytest.mark.parametrize(
    ("fields", "location", "message"),
    [
        ({"name": ""}, ["name"], "1 to 60"),
        ({"name": "x" * 61}, ["name"], "1 to 60"),
        ({"name": "RSI(14)"}, ["name"], "parentheses"),
        ({"expression": "__import__('os')"}, ["expression"], "Unknown function"),
        ({"expression": "close.real"}, ["expression"], "Attribute access"),
        ({"expression": "close ** 99999999"}, ["expression"], "exponent"),
        ({"chart_placement": "left"}, ["chart_placement"], "Unknown chart placement"),
        ({"value_description": " "}, ["value_description"], "1 to 1000"),
    ],
)
@pytest.mark.anyio
async def test_create_and_check_give_the_located_problems(
    web_client: httpx.AsyncClient, fields: dict[str, Any], location: list[str], message: str
) -> None:
    response = await web_client.post(BASE_PATH, json={**RATIO, **fields})
    assert response.status_code == 422
    problems = response.json()["problems"]
    assert [problem["location"] for problem in problems] == [location]
    assert message in problems[0]["message"]

    check = await web_client.post(f"{BASE_PATH}/check", json={**RATIO, **fields})
    assert check.status_code == 200
    assert check.json()["problems"] == problems
    assert (await web_client.get(BASE_PATH)).json() == []


@pytest.mark.anyio
async def test_check_gives_the_look_back_of_a_correct_expression(web_client: httpx.AsyncClient) -> None:
    check = await web_client.post(f"{BASE_PATH}/check", json={**RATIO, "expression": "mean(rsi(14), 5)"})
    assert check.json() == {"problems": [], "look_back_bars": 116, "default_look_back_bars": 116}


@pytest.mark.anyio
async def test_a_name_is_unique_without_case(web_client: httpx.AsyncClient) -> None:
    await create(web_client)
    response = await web_client.post(BASE_PATH, json={**RATIO, "name": "distance to sma"})
    assert response.status_code == 422
    assert response.json()["problems"][0]["location"] == ["name"]


@pytest.mark.anyio
async def test_change_keeps_the_key_and_the_own_name_is_allowed(web_client: httpx.AsyncClient) -> None:
    created = await create(web_client)
    path = f"{BASE_PATH}/{created['custom_indicator_id']}"
    response = await web_client.put(path, json={**RATIO, "expression": "close / sma(20)"})
    assert response.status_code == 200
    assert response.json() == {**created, "expression": "close / sma(20)"}


@pytest.mark.anyio
async def test_change_refuses_a_wrong_expression(web_client: httpx.AsyncClient) -> None:
    created = await create(web_client)
    path = f"{BASE_PATH}/{created['custom_indicator_id']}"
    response = await web_client.put(path, json={**RATIO, "expression": "foo"})
    assert response.status_code == 422
    assert (await web_client.get(path)).json() == created


@pytest.mark.anyio
async def test_unknown_id_gives_404(web_client: httpx.AsyncClient) -> None:
    assert (await web_client.get(f"{BASE_PATH}/9")).status_code == 404
    assert (await web_client.put(f"{BASE_PATH}/9", json=RATIO)).status_code == 404
    assert (await web_client.put(f"{BASE_PATH}/9", json={**RATIO, "name": ""})).status_code == 404
    assert (await web_client.delete(f"{BASE_PATH}/9")).status_code == 404


@pytest.mark.anyio
async def test_delete_removes_the_indicator_from_the_catalog_and_the_key_comes_never_again(
    web_client: httpx.AsyncClient,
) -> None:
    created = await create(web_client)
    response = await web_client.delete(f"{BASE_PATH}/{created['custom_indicator_id']}")
    assert response.status_code == 204
    catalog = (await web_client.get("/api/market-data/indicators")).json()
    assert created["key"] not in [item["key"] for item in catalog]
    assert (await create(web_client))["key"] != created["key"]


@pytest.mark.anyio
async def test_the_chart_set_keeps_a_custom_indicator_after_the_delete_and_can_save_it_again(
    web_client: httpx.AsyncClient,
) -> None:
    created = await create(web_client)
    formula = {"name": RATIO["name"], "expression": RATIO_EXPRESSION, "chart_placement": "own"}
    chart_indicator = {
        "indicator": created["key"],
        "parameters": {},
        "hidden": False,
        "lines": [{"output": "value", "color": 1, "style": "solid", "width": 2}],
        "formula": formula,
    }
    chart_set: dict[str, Any] = {
        "panes": [{"indicators": []}, {"indicators": [chart_indicator]}],
        "favorites": [created["key"]],
    }
    assert (await web_client.put("/api/market-data/chart-indicators", json=chart_set)).status_code == 200

    await web_client.delete(f"{BASE_PATH}/{created['custom_indicator_id']}")

    saved = (await web_client.get("/api/market-data/chart-indicators")).json()
    assert saved == chart_set
    assert (await web_client.put("/api/market-data/chart-indicators", json=saved)).status_code == 200


@pytest.mark.anyio
async def test_the_chart_set_refuses_a_custom_indicator_in_the_wrong_pane(web_client: httpx.AsyncClient) -> None:
    formula = {"name": "X", "expression": "close", "chart_placement": "own"}
    chart_indicator = {
        "indicator": "custom_1",
        "parameters": {},
        "hidden": False,
        "lines": [{"output": "value", "color": 1, "style": "solid", "width": 2}],
        "formula": formula,
    }
    chart_set = {"panes": [{"indicators": [chart_indicator]}], "favorites": []}
    response = await web_client.put("/api/market-data/chart-indicators", json=chart_set)
    assert response.status_code == 422
    assert "chart placement" in response.json()["problems"][0]["message"]


@pytest.mark.anyio
async def test_a_validation_error_of_a_text_with_a_lone_surrogate_is_a_422_without_the_input(
    web_client: httpx.AsyncClient,
) -> None:
    content = json.dumps({"name": "A\ud800B", "market": "US"})
    response = await web_client.post("/api/screens", content=content, headers=JSON_HEADERS)
    assert response.status_code == 422, response.text
    assert [(error["type"], error["loc"]) for error in response.json()["detail"]] == [
        ("missing", ["body", "definition"])
    ]
    assert "input" not in response.json()["detail"][0]


@pytest.mark.parametrize("check", [check_formula, check_indicator_reference])
def test_a_field_name_with_a_lone_surrogate_can_be_sent_in_a_location(
    check: Callable[[object], Sequence[IndicatorProblem]],
) -> None:
    problems = check({"\ud800": 1})
    assert problems
    for problem in problems:
        json.dumps(problem.location, ensure_ascii=False).encode("utf-8")


@pytest.mark.parametrize("text", ["A\x00B", "A\ud800B"])
@pytest.mark.parametrize(("field", "message"), [("name", "name"), ("value_description", "value description")])
@pytest.mark.anyio
async def test_a_character_that_postgresql_cannot_store_is_a_problem_of_its_field(
    web_client: httpx.AsyncClient, text: str, field: str, message: str
) -> None:
    content = json.dumps({**RATIO, field: text})
    for method, path in (("POST", BASE_PATH), ("POST", f"{BASE_PATH}/check")):
        response = await web_client.request(method, path, content=content, headers=JSON_HEADERS)
        problems = response.json()["problems"]
        assert [problem["location"] for problem in problems] == [[field]], response.text
        assert message in problems[0]["message"]
    assert (await web_client.get(BASE_PATH)).json() == []


@pytest.mark.anyio
async def test_a_change_with_a_character_that_postgresql_cannot_store_is_refused(
    web_client: httpx.AsyncClient,
) -> None:
    created = await create(web_client)
    path = f"{BASE_PATH}/{created['custom_indicator_id']}"
    response = await web_client.put(path, content=json.dumps({**RATIO, "name": "A\x00B"}), headers=JSON_HEADERS)
    assert response.status_code == 422, response.text
    assert response.json()["problems"][0]["location"] == ["name"]


@pytest.mark.parametrize("text", ["close\x00", "close\ud800"])
@pytest.mark.anyio
async def test_a_character_outside_the_expression_syntax_is_a_problem_of_the_expression(
    web_client: httpx.AsyncClient, text: str
) -> None:
    content = json.dumps({**RATIO, "expression": text})
    response = await web_client.post(BASE_PATH, content=content, headers=JSON_HEADERS)
    assert response.status_code == 422, response.text
    assert response.json()["problems"][0]["location"] == ["expression"]


@pytest.mark.anyio
async def test_a_saved_screen_keeps_its_expression_after_a_change_and_a_delete(web_client: httpx.AsyncClient) -> None:
    created = await create(web_client, expression="close")
    catalog = (await web_client.get("/api/screen-indicators")).json()
    reference: dict[str, Any] = {
        "indicator": created["key"],
        "parameters": {},
        "output": "value",
        "formula": catalog[-1]["formula"],
    }
    body: dict[str, Any] = {
        "name": "Custom order",
        "market": "US",
        "definition": {
            "start": "all_with_daily_bars",
            "filters": [],
            "indicator_conditions": [],
            "order": {"indicator": reference, "direction": "descending"},
        },
    }
    screen = (await web_client.post("/api/screens", json=body)).json()
    path = f"{BASE_PATH}/{created['custom_indicator_id']}"

    assert (await web_client.put(path, json={**RATIO, "expression": "open"})).status_code == 200
    assert (await web_client.delete(path)).status_code == 204

    saved = (await web_client.get(f"/api/screens/{screen['id']}")).json()
    assert saved["definition"]["order"]["indicator"]["formula"]["expression"] == "close"
    assert (await web_client.post(f"/api/screens/{screen['id']}/runs")).status_code == 201


LOOKBACK = {
    "name": "lookback_days",
    "label": "Look-back days",
    "value_type": "int",
    "default": 60,
    "minimum": 5,
    "maximum": 250,
    "description": "The days of the mean.",
}
WITH_PARAMETER = {**RATIO, "expression": "close / mean(close, lookback_days)", "parameters": [LOOKBACK]}


@pytest.mark.anyio
async def test_a_custom_indicator_keeps_its_parameters_and_the_catalog_shows_them(
    web_client: httpx.AsyncClient,
) -> None:
    created = await create(web_client, **WITH_PARAMETER)
    assert created["parameters"] == [LOOKBACK]
    assert (await web_client.get(f"{BASE_PATH}/{created['custom_indicator_id']}")).json() == created

    item = (await web_client.get("/api/market-data/indicators")).json()[-1]
    assert item["parameters"] == [
        {
            "name": "lookback_days",
            "value_type": "int",
            "default": 60,
            "minimum": 5,
            "maximum": 250,
            "is_in_name": True,
            "label": "Look-back days",
            "description": "The days of the mean.",
        }
    ]
    assert item["formula"]["parameters"] == [LOOKBACK]
    assert check_indicator_reference({"indicator": item["key"], "formula": item["formula"]}) == []

    changed = await web_client.put(f"{BASE_PATH}/{created['custom_indicator_id']}", json=RATIO)
    assert changed.json()["parameters"] == []
    assert "parameters" not in (await web_client.get("/api/market-data/indicators")).json()[-1]["formula"]


@pytest.mark.anyio
async def test_check_gives_the_look_back_of_the_maximum_and_of_the_default(web_client: httpx.AsyncClient) -> None:
    check = await web_client.post(f"{BASE_PATH}/check", json=WITH_PARAMETER)

    assert check.json() == {"problems": [], "look_back_bars": 250, "default_look_back_bars": 60}


@pytest.mark.parametrize(
    ("fields", "location", "message"),
    [
        ({"expression": "close / mean(close, days)"}, ["expression"], "Column 21: Unknown name 'days'"),
        ({"expression": "close"}, ["expression"], "does not use the parameter 'lookback_days'"),
        ({"parameters": [{**LOOKBACK, "maximum": 1001}]}, ["expression"], "from 1 to 1000"),
        (
            {
                "expression": " + ".join(["mean(close, lookback_days)"] * 11),
                "parameters": [{**LOOKBACK, "maximum": 1000}],
            },
            ["expression"],
            "Window bars x bars read",
        ),
        ({"parameters": [{**LOOKBACK, "name": "Lookback"}]}, ["parameters", "0", "name"], "lower-case letter"),
        ({"parameters": [{**LOOKBACK, "default": 300}]}, ["parameters", "0", "default"], "from the minimum"),
    ],
)
@pytest.mark.anyio
async def test_a_wrong_parameter_is_a_problem_and_saves_nothing(
    web_client: httpx.AsyncClient, fields: dict[str, Any], location: list[str], message: str
) -> None:
    response = await web_client.post(BASE_PATH, json={**WITH_PARAMETER, **fields})
    assert response.status_code == 422
    problems = response.json()["problems"]
    assert [problem["location"] for problem in problems] == [location]
    assert message in problems[0]["message"]

    check = await web_client.post(f"{BASE_PATH}/check", json={**WITH_PARAMETER, **fields})
    assert check.json() == {"problems": problems, "look_back_bars": None, "default_look_back_bars": None}
    assert (await web_client.get(BASE_PATH)).json() == []
