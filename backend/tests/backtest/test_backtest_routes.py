"""Backtest requests through the HTTP routes: the checks of the request, the queue, and the strategy delete rule."""

from pathlib import Path

import httpx
import pytest

from tests.backtest.real_runner import save_test_bars

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
async def test_rejects_backtest_with_a_time_range_that_ends_before_it_starts(web_client: httpx.AsyncClient) -> None:
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "end_utc": "2026-02-01T00:00:00Z"}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert response.json() == {"detail": "The time range must end after it starts."}


@pytest.mark.anyio
async def test_rejects_backtest_without_saved_bars_in_the_time_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    # The test bars are from 2026-03-02 to 2026-03-21. The exchange is not the exchange of the saved bars.
    request = {**make_backtest_request(saved["strategy_version_id"]), "exchange": "100"}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "There are no saved 1 day bars of BTEST / 100 / USD from 2026-03-01 00:00 UTC to 2026-04-01 00:00 UTC."
        " ATrade saves bars when a bar chart loads them from IBKR and when a forward test receives them."
        " IBKR has bars only for the regular trading hours: a period when the market was closed has no bars."
        " Open the bar chart of the instrument with this bar period to load the bars, or select a period with"
        " trading hours."
    }
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_rejects_backtest_with_a_time_range_before_the_saved_bars(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    request = {
        **make_backtest_request(saved["strategy_version_id"]),
        "start_utc": "2026-02-01T00:00:00Z",
        "end_utc": "2026-03-02T00:00:00Z",
    }

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_accepts_backtest_with_saved_bars_in_only_a_part_of_the_time_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    # Only the last test bar (2026-03-21) is in the range. One saved bar is enough (docs/architecture/backtest.md 10.1).
    request = {
        **make_backtest_request(saved["strategy_version_id"]),
        "start_utc": "2026-03-21T00:00:00Z",
        "end_utc": "2026-06-01T00:00:00Z",
    }

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 201


@pytest.mark.anyio
async def test_new_backtest_waits_in_the_queue(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
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
async def test_strategy_that_a_backtest_uses_cannot_be_deleted(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))

    response = await web_client.delete(f"/api/strategies/{saved['strategy_id']}")

    assert response.status_code == 409
