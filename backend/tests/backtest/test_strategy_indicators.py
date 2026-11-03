"""The strategy indicators of the backtest and forward test details (docs/architecture/indicator.md section 23.9.8)."""

import httpx
import pytest

from tests.backtest.real_runner import save_test_bars
from tests.backtest.test_backtest_routes import TEST_STRATEGY_FILE, make_backtest_request
from tests.forward_test.test_forward_test_routes import FORWARD_TESTS_PATH, make_start_request

CHART_INDICATORS_CODE = """
CHART_INDICATORS = [
    {"indicator": "sma", "parameters": {"period": "trade_quantity_shares"}},
    {"indicator": "rsi", "parameters": {"period": 14}},
]
"""


async def save_version(web_client: httpx.AsyncClient, *, has_chart_indicators: bool) -> int:
    strategy = (await web_client.post("/api/strategies", json={"name": "Bar count"})).json()
    code = TEST_STRATEGY_FILE.read_text() + (CHART_INDICATORS_CODE if has_chart_indicators else "")
    response = await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.anyio
async def test_the_backtest_detail_has_the_chart_indicators_of_the_version_with_the_field_defaults(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    version_id = await save_version(web_client, has_chart_indicators=True)
    backtest = (await web_client.post("/api/backtests", json=make_backtest_request(version_id))).json()

    detail = (await web_client.get(f"/api/backtests/{backtest['id']}")).json()

    assert detail["strategy_indicators"] == [
        {"indicator": "sma", "parameters": {"period": 10}},
        {"indicator": "rsi", "parameters": {"period": 14}},
    ]


@pytest.mark.anyio
async def test_the_backtest_detail_of_a_version_without_chart_indicators_has_an_empty_list(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    version_id = await save_version(web_client, has_chart_indicators=False)
    backtest = (await web_client.post("/api/backtests", json=make_backtest_request(version_id))).json()

    detail = (await web_client.get(f"/api/backtests/{backtest['id']}")).json()

    assert detail["strategy_indicators"] == []


@pytest.mark.anyio
async def test_a_sweep_run_uses_its_parameters_in_the_chart_indicators(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    version_id = await save_version(web_client, has_chart_indicators=True)
    grid = [{"name": "trade_quantity_shares", "start": 5, "end": 15, "step": 5}]
    sweep = (await web_client.post("/api/sweeps", json={**make_backtest_request(version_id), "grid": grid})).json()

    periods = [
        (await web_client.get(f"/api/backtests/{run['backtest_id']}")).json()["strategy_indicators"][0]["parameters"][
            "period"
        ]
        for run in sweep["runs"]
    ]

    assert periods == [5, 10, 15]


@pytest.mark.anyio
async def test_the_forward_test_detail_has_the_chart_indicators_of_the_version(web_client: httpx.AsyncClient) -> None:
    version_id = await save_version(web_client, has_chart_indicators=True)
    forward_test = (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(version_id))).json()

    detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")).json()

    assert detail["forward_test"]["strategy_indicators"] == [
        {"indicator": "sma", "parameters": {"period": 10}},
        {"indicator": "rsi", "parameters": {"period": 14}},
    ]
