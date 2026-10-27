"""The comparison of two backtests through the HTTP route: only two backtests of the same strategy (section 9.5)."""

from pathlib import Path

import httpx
import pytest

from tests.backtest.test_backtest_routes import make_backtest_request

TEST_STRATEGY_FILE = Path(__file__).parent / "strategies" / "buy_and_sell_by_bar_count.py"


async def save_strategy(web_client: httpx.AsyncClient, name: str) -> int:
    strategy = (await web_client.post("/api/strategies", json={"name": name})).json()
    return int(strategy["id"])


async def save_version(web_client: httpx.AsyncClient, strategy_id: int, code: str) -> int:
    version = (await web_client.post(f"/api/strategies/{strategy_id}/versions", json={"code": code})).json()
    return int(version["id"])


async def start_backtest(web_client: httpx.AsyncClient, strategy_version_id: int) -> int:
    response = await web_client.post("/api/backtests", json=make_backtest_request(strategy_version_id))
    return int(response.json()["id"])


@pytest.mark.anyio
async def test_compares_two_versions_of_the_same_strategy(web_client: httpx.AsyncClient) -> None:
    strategy_id = await save_strategy(web_client, "Bar count")
    first_code = TEST_STRATEGY_FILE.read_text()
    second_code = first_code + "\n# Version 3\n"
    first_version_id = await save_version(web_client, strategy_id, first_code)
    second_version_id = await save_version(web_client, strategy_id, second_code)
    first_backtest_id = await start_backtest(web_client, first_version_id)
    second_backtest_id = await start_backtest(web_client, second_version_id)

    response = await web_client.get(f"/api/backtests/{first_backtest_id}/comparison/{second_backtest_id}")

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["strategy_id"] == strategy_id
    assert comparison["strategy_name"] == "Bar count"
    assert comparison["first"]["id"] == first_backtest_id
    assert comparison["first"]["version_number"] == 2
    assert comparison["first"]["code"] == first_code
    assert comparison["first"]["equity_curve"] == []
    assert comparison["second"]["id"] == second_backtest_id
    assert comparison["second"]["version_number"] == 3
    assert comparison["second"]["code"] == second_code


@pytest.mark.anyio
async def test_rejects_comparison_of_different_strategies(web_client: httpx.AsyncClient) -> None:
    code = TEST_STRATEGY_FILE.read_text()
    first_version_id = await save_version(web_client, await save_strategy(web_client, "Bar count"), code)
    second_version_id = await save_version(web_client, await save_strategy(web_client, "Other"), code)
    first_backtest_id = await start_backtest(web_client, first_version_id)
    second_backtest_id = await start_backtest(web_client, second_version_id)

    response = await web_client.get(f"/api/backtests/{first_backtest_id}/comparison/{second_backtest_id}")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Only backtests of the same strategy can be compared. These backtests use Bar count and Other."
    }


@pytest.mark.anyio
async def test_rejects_comparison_of_a_backtest_with_itself(web_client: httpx.AsyncClient) -> None:
    strategy_id = await save_strategy(web_client, "Bar count")
    version_id = await save_version(web_client, strategy_id, TEST_STRATEGY_FILE.read_text())
    backtest_id = await start_backtest(web_client, version_id)

    response = await web_client.get(f"/api/backtests/{backtest_id}/comparison/{backtest_id}")

    assert response.status_code == 422
    assert response.json() == {"detail": "Select two different backtests."}


@pytest.mark.anyio
async def test_comparison_with_a_missing_backtest_is_not_found(web_client: httpx.AsyncClient) -> None:
    strategy_id = await save_strategy(web_client, "Bar count")
    version_id = await save_version(web_client, strategy_id, TEST_STRATEGY_FILE.read_text())
    backtest_id = await start_backtest(web_client, version_id)

    response = await web_client.get(f"/api/backtests/{backtest_id}/comparison/999")

    assert response.status_code == 404
