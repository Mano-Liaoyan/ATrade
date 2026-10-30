"""Parameter sweeps through the HTTP routes (docs/architecture/backtest.md section 10.11)."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import httpx
import pytest

from tests.app.test_assistant_port import create_port_app
from tests.backtest.real_runner import (
    run_backtest_runner,
    save_test_bars,
    wait_for_final_status,
)
from tests.backtest.test_backtest_routes import make_backtest_request, save_test_strategy_version
from tests.fakes.clock import FixedClock

QUANTITY_GRID = {"name": "trade_quantity_shares", "start": 5, "end": 15, "step": 5}


async def start_sweep(web_client: httpx.AsyncClient, grid: Sequence[Mapping[str, object]]) -> httpx.Response:
    saved = await save_test_strategy_version(web_client)
    return await web_client.post(
        "/api/sweeps", json={**make_backtest_request(saved["strategy_version_id"]), "grid": grid}
    )


@pytest.mark.anyio
async def test_parameters_route_lists_the_parameters_of_the_strategy_version(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)

    response = await web_client.get(f"/api/sweeps/parameters?strategy_version_id={saved['strategy_version_id']}")

    assert response.status_code == 200
    assert response.json() == {"parameters": [{"name": "trade_quantity_shares", "type": "int", "default": 10}]}


@pytest.mark.anyio
async def test_parameters_route_of_a_missing_strategy_version_is_404(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/sweeps/parameters?strategy_version_id=999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_start_queues_one_run_for_each_grid_value_and_hides_them_from_the_backtest_list(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)

    response = await start_sweep(web_client, [QUANTITY_GRID])

    assert response.status_code == 201, response.text
    sweep = response.json()
    assert sweep["run_count"] == 3
    assert sweep["status_counts"] == {"queued": 3}
    assert [run["parameters"] for run in sweep["runs"]] == [
        {"trade_quantity_shares": 5},
        {"trade_quantity_shares": 10},
        {"trade_quantity_shares": 15},
    ]
    assert (await web_client.get("/api/backtests")).json() == []
    sweeps = (await web_client.get("/api/sweeps")).json()
    assert [(item["id"], item["run_count"]) for item in sweeps] == [(sweep["id"], 3)]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "grid",
    [
        [],
        [QUANTITY_GRID, QUANTITY_GRID, QUANTITY_GRID, QUANTITY_GRID],
        [{"name": "missing", "start": 1, "end": 2, "step": 1}],
        [{**QUANTITY_GRID, "step": 0}],
        [{**QUANTITY_GRID, "start": 20}],
        [{**QUANTITY_GRID, "start": 1, "end": 300, "step": 1}],
    ],
)
async def test_start_refuses_a_grid_that_is_not_valid(
    web_client: httpx.AsyncClient, database_url: str, grid: Sequence[Mapping[str, object]]
) -> None:
    save_test_bars(database_url)

    response = await start_sweep(web_client, grid)

    assert response.status_code == 422
    assert (await web_client.get("/api/sweeps")).json() == []


@pytest.mark.anyio
async def test_start_refuses_backtest_fields_that_are_not_valid(web_client: httpx.AsyncClient) -> None:
    response = await start_sweep(web_client, [QUANTITY_GRID])

    assert response.status_code == 422
    assert (await web_client.get("/api/sweeps")).json() == []


@pytest.mark.anyio
async def test_cancel_sets_the_queued_runs_to_cancelled(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    sweep = (await start_sweep(web_client, [QUANTITY_GRID])).json()

    response = await web_client.post(f"/api/sweeps/{sweep['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status_counts"] == {"cancelled": 3}


@pytest.mark.anyio
async def test_read_and_cancel_of_a_missing_sweep_are_404(web_client: httpx.AsyncClient) -> None:
    assert (await web_client.get("/api/sweeps/999")).status_code == 404
    assert (await web_client.post("/api/sweeps/999/cancel")).status_code == 404


@pytest.mark.anyio
async def test_a_run_gives_its_parameters_to_the_strategy_and_counts_as_a_trial(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    grid = [{"name": "trade_quantity_shares", "start": 3, "end": 3, "step": 1}]
    sweep = (await start_sweep(web_client, grid)).json()
    backtest_id = sweep["runs"][0]["backtest_id"]

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert {trade["quantity_shares"] for trade in backtest["trades"]} == {"3"}
    assert backtest["robustness"]["trial_count"] == 1


def test_the_port_8001_app_has_no_sweep_routes(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> None:
    app = create_port_app(database_url, clock, frontend_build_dir)

    paths: dict[str, object] = app.openapi()["paths"]

    assert [path for path in paths if path.startswith("/api/sweeps")] == []
