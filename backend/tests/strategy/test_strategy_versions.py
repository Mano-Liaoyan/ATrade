"""Strategies and strategy versions through the HTTP routes: create, save, list, open, and delete."""

import ast
import hashlib

import httpx
import psycopg
import pytest


@pytest.mark.anyio
async def test_new_strategy_starts_from_the_template_as_version_1(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategies", json={"name": "Moving average"})

    assert response.status_code == 201
    strategy = response.json()
    assert strategy["name"] == "Moving average"
    assert [version["version_number"] for version in strategy["versions"]] == [1]
    version_response = await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")
    version = version_response.json()
    assert version["created_at_utc"] == "2026-01-02T03:04:05Z"
    assert version["code_sha256"] == hashlib.sha256(version["code"].encode()).hexdigest()
    assert "(Strategy):" in version["code"]
    assert "(StrategyConfig):" in version["code"]
    assert "self.request_bars(" in version["code"]
    config_init = find_config_init(version["code"])
    assert [argument.arg for argument in config_init.args.args] == ["self"]
    assert [argument.arg for argument in config_init.args.kwonlyargs][:2] == ["instrument_id", "bar_type"]


@pytest.mark.anyio
async def test_changed_code_makes_the_next_version_in_its_strategy(web_client: httpx.AsyncClient) -> None:
    first_strategy = (await web_client.post("/api/strategies", json={"name": "First"})).json()
    second_strategy = (await web_client.post("/api/strategies", json={"name": "Second"})).json()
    template = (await web_client.get(f"/api/strategies/{first_strategy['id']}/versions/1")).json()["code"]
    code_v2 = template.replace("average_period: int = 20", "average_period: int = 30")
    code_v3 = template.replace("average_period: int = 20", "average_period: int = 40")

    response_v2 = await web_client.post(f"/api/strategies/{first_strategy['id']}/versions", json={"code": code_v2})
    response_v3 = await web_client.post(f"/api/strategies/{first_strategy['id']}/versions", json={"code": code_v3})
    response_other = await web_client.post(f"/api/strategies/{second_strategy['id']}/versions", json={"code": code_v2})

    assert response_v2.status_code == 201
    assert response_v2.json()["version_number"] == 2
    assert response_v3.json()["version_number"] == 3
    assert response_v3.json()["code"] == code_v3
    assert response_other.json()["version_number"] == 2
    strategy = (await web_client.get(f"/api/strategies/{first_strategy['id']}")).json()
    assert [version["version_number"] for version in strategy["versions"]] == [1, 2, 3]


@pytest.mark.anyio
async def test_same_code_as_the_latest_version_makes_no_new_version(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    template = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["code"]

    response = await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": template})

    assert response.status_code == 200
    assert response.json()["version_number"] == 1
    strategy_after = (await web_client.get(f"/api/strategies/{strategy['id']}")).json()
    assert len(strategy_after["versions"]) == 1


@pytest.mark.anyio
async def test_old_version_saved_again_becomes_a_new_version(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    template = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["code"]
    code_v2 = template.replace("average_period: int = 20", "average_period: int = 30")
    await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code_v2})

    response = await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": template})

    assert response.status_code == 201
    assert response.json()["version_number"] == 3
    assert response.json()["code"] == template
    version_1 = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()
    assert version_1["code"] == template


@pytest.mark.anyio
async def test_versions_cannot_be_changed_or_deleted(web_client: httpx.AsyncClient, database_url: str) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    version_path = f"/api/strategies/{strategy['id']}/versions/1"

    put_response = await web_client.put(version_path, json={"code": "x = 1"})
    delete_response = await web_client.delete(version_path)

    assert put_response.status_code == 405
    assert delete_response.status_code == 405
    with psycopg.connect(database_url, autocommit=True) as connection, pytest.raises(psycopg.errors.RaiseException):
        connection.execute("UPDATE strategy_version SET code = 'x = 1'")


@pytest.mark.anyio
async def test_lists_strategies_with_their_latest_version_number(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    await web_client.post("/api/strategies", json={"name": "Breakout"})
    template = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["code"]
    code_v2 = template.replace("average_period: int = 20", "average_period: int = 30")
    await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code_v2})

    response = await web_client.get("/api/strategies")

    assert response.status_code == 200
    assert [(item["name"], item["latest_version_number"]) for item in response.json()] == [
        ("Breakout", 1),
        ("Moving average", 2),
    ]


@pytest.mark.anyio
async def test_refuses_a_second_strategy_with_the_same_name(web_client: httpx.AsyncClient) -> None:
    await web_client.post("/api/strategies", json={"name": "Moving average"})

    response = await web_client.post("/api/strategies", json={"name": "Moving average"})

    assert response.status_code == 409


@pytest.mark.anyio
async def test_refuses_an_empty_strategy_name(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/strategies", json={"name": "   "})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_unknown_strategy_and_version_are_not_found(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    template = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["code"]

    assert (await web_client.get("/api/strategies/999")).status_code == 404
    assert (await web_client.get(f"/api/strategies/{strategy['id']}/versions/9")).status_code == 404
    assert (await web_client.post("/api/strategies/999/versions", json={"code": template})).status_code == 404
    assert (await web_client.delete("/api/strategies/999")).status_code == 404


@pytest.mark.anyio
async def test_deletes_a_strategy_that_no_test_uses(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()

    response = await web_client.delete(f"/api/strategies/{strategy['id']}")

    assert response.status_code == 204
    assert (await web_client.get(f"/api/strategies/{strategy['id']}")).status_code == 404
    assert (await web_client.get("/api/strategies")).json() == []


@pytest.mark.anyio
async def test_refuses_to_delete_a_strategy_that_a_test_uses(web_client: httpx.AsyncClient, database_url: str) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    version_id = strategy["versions"][0]["id"]
    # The backtest and forward test tables come in later tickets. This table has the same foreign key.
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "CREATE TABLE test_strategy_user (strategy_version_id bigint NOT NULL REFERENCES strategy_version (id))"
        )
        connection.execute("INSERT INTO test_strategy_user VALUES (%(version_id)s)", {"version_id": version_id})
    try:
        response = await web_client.delete(f"/api/strategies/{strategy['id']}")
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute("DROP TABLE test_strategy_user")

    assert response.status_code == 409
    assert (await web_client.get(f"/api/strategies/{strategy['id']}")).status_code == 200


def find_config_init(code: str) -> ast.FunctionDef:
    module = ast.parse(code)
    for class_node in module.body:
        if not isinstance(class_node, ast.ClassDef):
            continue
        base_names = [base.id for base in class_node.bases if isinstance(base, ast.Name)]
        if "StrategyConfig" not in base_names:
            continue
        for member in class_node.body:
            if isinstance(member, ast.FunctionDef) and member.name == "__init__":
                return member
    message = "The code has no StrategyConfig subclass with __init__."
    raise AssertionError(message)
