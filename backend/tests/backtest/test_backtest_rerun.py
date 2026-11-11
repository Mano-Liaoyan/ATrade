"""POST /api/backtests/{backtest_id}/rerun: a new backtest of another strategy version on the data of a backtest
(docs/architecture/backtest.md section 10.5)."""

import httpx
import psycopg
import pytest

from tests.backtest.real_runner import save_test_bars
from tests.backtest.test_backtest_routes import TEST_STRATEGY_FILE, make_backtest_request, save_test_strategy_version
from tests.backtest.test_universe_backtest_routes import read_universe_members
from tests.backtest.universe_data import make_universe_request, save_universe_test_data

REQUEST_FIELDS = (
    "universe_kind",
    "symbol",
    "exchange",
    "currency",
    "universe_top_n",
    "universe_screen",
    "universe_rebalance_period",
    "bar_period",
    "start_utc",
    "end_utc",
    "paper_capital_usd",
    "out_of_sample_share",
    "split_time_utc",
    "source_order",
)


async def save_next_version(web_client: httpx.AsyncClient, strategy_id: int) -> int:
    code = TEST_STRATEGY_FILE.read_text() + "\n# Changed.\n"
    response = await web_client.post(f"/api/strategies/{strategy_id}/versions", json={"code": code})
    return int(response.json()["id"])


@pytest.mark.anyio
async def test_rerun_copies_the_request_with_the_new_strategy_version(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "out_of_sample_share": 20}
    first = (await web_client.post("/api/backtests", json=request)).json()
    next_version_id = await save_next_version(web_client, saved["strategy_id"])

    response = await web_client.post(
        f"/api/backtests/{first['id']}/rerun", json={"strategy_version_id": next_version_id}
    )

    assert response.status_code == 201
    rerun = response.json()
    assert rerun["id"] != first["id"]
    assert rerun["strategy_version_id"] == next_version_id
    assert rerun["status"] == "queued"
    assert {field: rerun[field] for field in REQUEST_FIELDS} == {field: first[field] for field in REQUEST_FIELDS}


@pytest.mark.anyio
async def test_rerun_of_a_rule_backtest_copies_the_members_of_each_period(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)
    first = (
        await web_client.post(
            "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="rule", top_n=2)
        )
    ).json()
    # A later change of the universe data does not change the members of the rerun.
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("DELETE FROM us_universe_member")
    next_version_id = await save_next_version(web_client, saved["strategy_id"])

    response = await web_client.post(
        f"/api/backtests/{first['id']}/rerun", json={"strategy_version_id": next_version_id}
    )

    assert response.status_code == 201
    assert read_universe_members(database_url, response.json()["id"]) == read_universe_members(
        database_url, first["id"]
    )


@pytest.mark.anyio
async def test_rerun_of_a_missing_backtest_is_not_found(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests/999/rerun", json={"strategy_version_id": saved["strategy_version_id"]}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Backtest not found."}


@pytest.mark.anyio
async def test_refuses_a_strategy_version_of_another_strategy(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    first = (await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))).json()
    other_strategy = (await web_client.post("/api/strategies", json={"name": "Other"})).json()
    other_version_id = await save_next_version(web_client, other_strategy["id"])

    response = await web_client.post(
        f"/api/backtests/{first['id']}/rerun", json={"strategy_version_id": other_version_id}
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": f"Strategy version {other_version_id} is not a version of the strategy of backtest #{first['id']}."
    }
    assert len((await web_client.get("/api/backtests")).json()) == 1


@pytest.mark.anyio
async def test_refuses_a_missing_strategy_version(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    first = (await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))).json()

    response = await web_client.post(f"/api/backtests/{first['id']}/rerun", json={"strategy_version_id": 999})

    assert response.status_code == 422
    assert response.json() == {"detail": "Strategy version 999 does not exist."}


@pytest.mark.anyio
async def test_refuses_a_sweep_run(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    first = (await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))).json()
    with psycopg.connect(database_url, autocommit=True) as connection:
        sweep = connection.execute(
            """
            INSERT INTO parameter_sweep (strategy_version_id, grid, created_at_utc)
            VALUES (%(version_id)s, '{}', now()) RETURNING id
            """,
            {"version_id": saved["strategy_version_id"]},
        ).fetchone()
        assert sweep is not None
        connection.execute(
            "UPDATE backtest SET sweep_id = %(sweep_id)s WHERE id = %(backtest_id)s",
            {"sweep_id": sweep[0], "backtest_id": first["id"]},
        )

    response = await web_client.post(
        f"/api/backtests/{first['id']}/rerun", json={"strategy_version_id": saved["strategy_version_id"]}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": f"Backtest #{first['id']} is a run of sweep #{sweep[0]}. Start a sweep."}
