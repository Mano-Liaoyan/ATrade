"""Forward test start, stop, and list through the HTTP routes (docs/architecture.md sections 12.1-12.4).

The Web process writes only the desired state. The worker (test_forward_test_worker.py) writes the actual state.
"""

from pathlib import Path
from typing import Any

import httpx
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

TEST_STRATEGY_FILE = Path(__file__).parents[1] / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
FORWARD_TESTS_PATH = "/api/forward-tests"

type JsonObject = dict[str, Any]


async def save_test_strategy_version(web_client: httpx.AsyncClient) -> int:
    # A new strategy has version 1 from the template. The test strategy becomes version 2.
    strategy = (await web_client.post("/api/strategies", json={"name": "Bar count"})).json()
    code = TEST_STRATEGY_FILE.read_text()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    return version["id"]


def make_start_request(strategy_version_id: int, *, symbol: str = "AAPL") -> JsonObject:
    return {
        "strategy_version_id": strategy_version_id,
        "symbol": symbol,
        "exchange": "NASDAQ",
        "currency": "USD",
        "bar_period": "1-MINUTE",
    }


@pytest.mark.anyio
async def test_starts_a_forward_test_with_the_lowest_free_client_id(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert response.status_code == 201
    forward_test = response.json()
    assert forward_test["strategy_version_id"] == strategy_version_id
    assert forward_test["strategy_name"] == "Bar count"
    assert forward_test["version_number"] == 2
    assert forward_test["symbol"] == "AAPL"
    assert forward_test["bar_period"] == "1-MINUTE"
    assert forward_test["desired_state"] == "running"
    assert forward_test["status"] == "starting"
    assert forward_test["client_id"] == 10
    assert forward_test["start_balance_usd"] is None
    assert forward_test["created_at_utc"] == "2026-01-02T03:04:05Z"


@pytest.mark.anyio
async def test_lists_forward_tests_newest_first(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AAPL"))
    await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="MSFT"))

    response = await web_client.get(FORWARD_TESTS_PATH)

    assert response.status_code == 200
    assert [(item["symbol"], item["client_id"]) for item in response.json()] == [("MSFT", 11), ("AAPL", 10)]


@pytest.mark.anyio
async def test_refuses_start_when_no_client_id_is_free(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    # The default client ID range 10-13 allows 4 forward tests at the same time.
    for symbol in ["AAPL", "MSFT", "AMZN", "ABNB"]:
        await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol=symbol))

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AMD"))

    assert response.status_code == 409
    assert response.json() == {"detail": "limit of running forward tests reached", "forward_test_id": None}


@pytest.mark.anyio
async def test_refuses_a_second_forward_test_on_the_same_instrument(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    first = (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))).json()

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Forward test {first['id']} (Bar count v2) already runs on AAPL / NASDAQ.",
        "forward_test_id": first["id"],
    }


@pytest.mark.anyio
async def test_refuses_start_of_a_missing_strategy_version(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(999))

    assert response.status_code == 422
    assert response.json() == {"detail": "Strategy version 999 does not exist."}


@pytest.mark.anyio
async def test_refuses_a_bar_period_that_ib_live_bars_do_not_support(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    request = {**make_start_request(strategy_version_id), "bar_period": "7-MINUTE"}

    response = await web_client.post(FORWARD_TESTS_PATH, json=request)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_stop_writes_only_the_desired_state(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    forward_test = (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))).json()

    response = await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")

    assert response.status_code == 202
    [listed] = (await web_client.get(FORWARD_TESTS_PATH)).json()
    assert listed["desired_state"] == "stopped"
    # The worker writes the actual state and frees the client ID after the orders are cancelled.
    assert listed["status"] == "starting"
    assert listed["client_id"] == 10


@pytest.mark.anyio
async def test_stop_of_a_missing_forward_test_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post(f"{FORWARD_TESTS_PATH}/999/stop")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_uses_the_client_id_range_of_the_settings(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    settings = Settings(
        database_url=database_url,
        frontend_build_dir=frontend_build_dir,
        forward_test_client_id_first=21,
        forward_test_client_id_last=21,
    )
    app = create_web_app(settings=settings, clock=clock, gateway_connection=FakeGatewayConnection(managed_accounts=[]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        strategy_version_id = await save_test_strategy_version(client)
        first = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AAPL"))
        second = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="MSFT"))

    assert first.json()["client_id"] == 21
    assert second.status_code == 409


@pytest.mark.anyio
async def test_the_end_time_is_optional_and_must_be_later_than_now(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    past = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-02T03:04:05Z"}
    without_time_zone = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-03T00:00:00"}
    later = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-03T09:30:00+08:00"}

    past_response = await web_client.post(FORWARD_TESTS_PATH, json=past)
    without_time_zone_response = await web_client.post(FORWARD_TESTS_PATH, json=without_time_zone)
    later_response = await web_client.post(FORWARD_TESTS_PATH, json=later)

    assert (past_response.status_code, past_response.json()["detail"]) == (422, "The end time must be later than now.")
    assert without_time_zone_response.status_code == 422
    assert later_response.status_code == 201
    # The database stores UTC (section 12.1).
    assert later_response.json()["end_time_utc"] == "2026-01-03T01:30:00Z"
    assert (later_response.json()["crash_count"], later_response.json()["interruptions"]) == (0, [])
