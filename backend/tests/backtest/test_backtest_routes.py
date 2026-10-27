"""Backtest requests through the HTTP routes: the checks of the request, the queue, and the strategy delete rule."""

from pathlib import Path

import httpx
import pytest

TEST_STRATEGY_FILE = Path(__file__).parent / "strategies" / "buy_and_sell_by_bar_count.py"


async def save_test_strategy_version(web_client: httpx.AsyncClient) -> dict[str, int]:
    strategy = (await web_client.post("/api/strategies", json={"name": "Bar count"})).json()
    code = TEST_STRATEGY_FILE.read_text()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    return {"strategy_id": strategy["id"], "strategy_version_id": version["id"]}


def make_backtest_request(strategy_version_id: int) -> dict[str, object]:
    return {
        "strategy_version_id": strategy_version_id,
        "symbol": "BTEST",
        "exchange": "ARCA",
        "currency": "USD",
        "bar_period": "1-DAY",
        "start_utc": "2026-03-01T00:00:00Z",
        "end_utc": "2026-04-01T00:00:00Z",
        "paper_capital_usd": "10000",
    }


@pytest.mark.anyio
async def test_rejects_backtest_without_paper_capital(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    request = make_backtest_request(saved["strategy_version_id"])
    del request["paper_capital_usd"]

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_rejects_backtest_with_paper_capital_of_zero(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "paper_capital_usd": "0"}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_rejects_backtest_of_a_missing_strategy_version(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post("/api/backtests", json=make_backtest_request(999))

    assert response.status_code == 422
    assert response.json() == {"detail": "Strategy version 999 does not exist."}


@pytest.mark.anyio
async def test_rejects_backtest_of_an_instrument_that_is_not_in_usd(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "currency": "HKD"}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert response.json() == {"detail": "A backtest supports only USD instruments. The instrument currency is HKD."}


@pytest.mark.anyio
async def test_rejects_backtest_with_a_time_range_that_ends_before_it_starts(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "end_utc": "2026-02-01T00:00:00Z"}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert response.json() == {"detail": "The time range must end after it starts."}


@pytest.mark.anyio
async def test_new_backtest_waits_in_the_queue(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))

    assert response.status_code == 201
    backtest = response.json()
    assert backtest["status"] == "queued"
    assert backtest["strategy_name"] == "Bar count"
    assert backtest["version_number"] == 2
    assert backtest["paper_capital_usd"] == "10000"
    assert backtest["created_at_utc"] == "2026-01-02T03:04:05Z"
    assert backtest["metrics"] is None
    listed = (await web_client.get("/api/backtests")).json()
    assert [item["id"] for item in listed] == [backtest["id"]]
    detail = (await web_client.get(f"/api/backtests/{backtest['id']}")).json()
    assert detail["equity_curve"] == []
    assert detail["trades"] == []


@pytest.mark.anyio
async def test_missing_backtest_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/backtests/999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_strategy_that_a_backtest_uses_cannot_be_deleted(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))

    response = await web_client.delete(f"/api/strategies/{saved['strategy_id']}")

    assert response.status_code == 409
