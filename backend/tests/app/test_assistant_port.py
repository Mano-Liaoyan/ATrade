"""Port 8001: the app of the assistant service and its allow-list (docs/architecture/assistant.md 25.3.2, 25.3.3).

No real model provider runs. The tests call the port 8001 app the way the assistant service does, with the
conversation header, and make the conversations through the port 8000 routes with the fake assistant service.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from atrade.app.assistant_port import ASSISTANT_PORT, ASSISTANT_SUBNET, CONVERSATION_HEADER, create_assistant_port_app
from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.backtest.real_runner import TEST_STRATEGY_FILE, save_test_bars
from tests.backtest.test_screen_result_list_routes import save_screen_result
from tests.backtest.universe_data import AAA, CCC, make_universe_request, save_universe_test_data
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection
from tests.screen.test_screen_run_routes import create_screen, make_definition

ALLOWED_ROUTES = {
    ("GET", "/api/strategies"),
    ("GET", "/api/strategies/{strategy_id}"),
    ("GET", "/api/strategies/{strategy_id}/versions/{version_number}"),
    ("POST", "/api/strategies"),
    ("POST", "/api/strategies/{strategy_id}/versions"),
    ("POST", "/api/backtests"),
    ("GET", "/api/backtests"),
    ("GET", "/api/backtests/{backtest_id}"),
    ("GET", "/api/backtests/{first_backtest_id}/comparison/{second_backtest_id}"),
    ("GET", "/api/screens"),
    ("GET", "/api/screens/{screen_id}"),
    ("POST", "/api/screens"),
    ("PUT", "/api/screens/{screen_id}"),
    ("POST", "/api/screens/{screen_id}/runs"),
    ("GET", "/api/screen-results/{screen_result_id}"),
}
REPO_ROOT = Path(__file__).resolve().parents[3]


def create_port_app(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> FastAPI:
    return create_assistant_port_app(
        settings=Settings(database_url=database_url, frontend_build_dir=frontend_build_dir),
        clock=clock,
        gateway_connection=FakeGatewayConnection(managed_accounts=["DU1234567"]),
    )


@asynccontextmanager
async def open_port_client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> AsyncGenerator[httpx.AsyncClient]:
    app = create_port_app(database_url, clock, frontend_build_dir)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://web:8001") as client:
        yield client


def backtest_body(strategy_version_id: int, *, start_utc: str = "2026-03-01T00:00:00Z") -> dict[str, object]:
    return {
        "strategy_version_id": strategy_version_id,
        "symbol": "BTEST",
        "exchange": "ARCA",
        "currency": "USD",
        "bar_period": "1-DAY",
        "start_utc": start_utc,
        "end_utc": "2026-04-01T00:00:00Z",
        "paper_capital_usd": "10000",
    }


def test_the_port_8001_app_has_exactly_the_routes_of_the_allow_list(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    app = create_port_app(database_url, clock, frontend_build_dir)

    paths: dict[str, dict[str, object]] = app.openapi()["paths"]
    routes = {(method.upper(), path) for path, operations in paths.items() for method in operations}

    assert routes == ALLOWED_ROUTES


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path", ["/", "/_app/start.js", "/strategies", "/ws/assistant", "/ws/paper-account", "/docs", "/openapi.json"]
)
async def test_the_port_8001_app_has_no_frontend_files_and_no_socket_routes(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, path: str
) -> None:
    async with open_port_client(database_url, clock, frontend_build_dir) as client:
        response = await client.get(path)

    assert response.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/paper-trading/orders"),
        ("GET", "/api/paper-trading/manual-orders"),
        ("POST", "/api/forward-tests"),
        ("GET", "/api/forward-tests"),
        ("PUT", "/api/backtest-limits"),
        ("GET", "/api/backtest-limits"),
        ("POST", "/api/watchlist"),
        ("DELETE", "/api/watchlist"),
        ("DELETE", "/api/strategies/1"),
        ("POST", "/api/strategies/1/versions/2/discard"),
        ("GET", "/api/assistant/conversations"),
        ("POST", "/api/assistant/conversations"),
        ("DELETE", "/api/screens/1"),
        ("POST", "/api/market-data/hk-instrument-list"),
        ("DELETE", "/api/market-data/hk-instrument-list/1"),
        ("POST", "/api/market-data/daily-bars/update"),
        ("POST", "/api/sweeps"),
    ],
)
async def test_the_port_8001_app_refuses_the_routes_that_are_not_in_the_allow_list(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, method: str, path: str
) -> None:
    async with open_port_client(database_url, clock, frontend_build_dir) as client:
        response = await client.request(method, path, headers={CONVERSATION_HEADER: "1"})

    # 404: no route has the path. 405: a route of the allow-list has the path, but not this method.
    assert response.status_code in {httpx.codes.NOT_FOUND, httpx.codes.METHOD_NOT_ALLOWED}


@asynccontextmanager
async def open_both_clients(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> AsyncGenerator[tuple[httpx.AsyncClient, httpx.AsyncClient]]:
    """The browser client of port 8000 (with the fake assistant service) and the client of port 8001."""
    async with (
        open_assistant_client(
            database_url=database_url,
            clock=clock,
            frontend_build_dir=frontend_build_dir,
            assistant_service=FakeAssistantService(),
        ) as browser,
        open_port_client(database_url, clock, frontend_build_dir) as assistant,
    ):
        yield browser, assistant


@pytest.mark.anyio
async def test_a_save_on_port_8001_records_the_source_ai_assistant_and_the_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        strategy_id = await create_strategy(browser, "Moving average")
        conversation_id = await create_conversation(browser, strategy_id)
        code = (await assistant.get(f"/api/strategies/{strategy_id}/versions/1")).json()["code"]

        response = await assistant.post(
            f"/api/strategies/{strategy_id}/versions",
            json={"code": code.replace("average_period: int = 20", "average_period: int = 30")},
            headers={CONVERSATION_HEADER: str(conversation_id)},
        )

    assert response.status_code == httpx.codes.CREATED, response.text
    version = response.json()
    assert (version["version_number"], version["source"], version["conversation_id"]) == (
        2,
        "ai_assistant",
        conversation_id,
    )


@pytest.mark.anyio
async def test_a_save_on_port_8001_without_a_known_conversation_is_refused(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_port_client(database_url, clock, frontend_build_dir) as assistant:
        strategy_id = (await assistant.post("/api/strategies", json={"name": "Moving average"})).json()["id"]
        body = {"code": "x = 1\n"}

        without_header = await assistant.post(f"/api/strategies/{strategy_id}/versions", json=body)
        unknown = await assistant.post(
            f"/api/strategies/{strategy_id}/versions", json=body, headers={CONVERSATION_HEADER: "999"}
        )

    assert without_header.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert unknown.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert unknown.json() == {"detail": "Conversation 999 does not exist."}


@pytest.mark.anyio
async def test_a_save_on_port_8001_accepts_only_code(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        strategy_id = await create_strategy(browser, "Moving average")
        conversation_id = await create_conversation(browser, strategy_id)

        response = await assistant.post(
            f"/api/strategies/{strategy_id}/versions",
            json={"rules": {}},
            headers={CONVERSATION_HEADER: str(conversation_id)},
        )

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["loc"] == ["body", "code"]


@pytest.mark.anyio
async def test_a_backtest_on_port_8001_records_the_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    save_test_bars(database_url)
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        strategy_id = await create_strategy(browser, "Bar count")
        conversation_id = await create_conversation(browser, strategy_id)
        headers = {CONVERSATION_HEADER: str(conversation_id)}
        saved = await assistant.post(
            f"/api/strategies/{strategy_id}/versions", json={"code": TEST_STRATEGY_FILE.read_text()}, headers=headers
        )

        response = await assistant.post("/api/backtests", json=backtest_body(saved.json()["id"]), headers=headers)

        assert response.status_code == httpx.codes.CREATED, response.text
        backtest = (await assistant.get(f"/api/backtests/{response.json()['id']}")).json()
    assert backtest["conversation_id"] == conversation_id


@pytest.mark.anyio
@pytest.mark.parametrize("universe_kind", ["screen", "list"])
async def test_a_multi_instrument_backtest_on_port_8001_records_the_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, universe_kind: str
) -> None:
    """docs/architecture/assistant.md 25.3.3: `POST /api/backtests` takes the universe fields (phase 3)."""
    save_universe_test_data(database_url)
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        strategy_id = await create_strategy(browser, "Bar count")
        conversation_id = await create_conversation(browser, strategy_id)
        headers = {CONVERSATION_HEADER: str(conversation_id)}
        saved = await assistant.post(
            f"/api/strategies/{strategy_id}/versions", json={"code": TEST_STRATEGY_FILE.read_text()}, headers=headers
        )
        if universe_kind == "screen":
            universe: dict[str, object] = {
                "screen_id": await create_screen(browser, make_definition(start="quarter_universe")),
                "rebalance_period": "month",
            }
        else:
            universe = {"screen_result_id": save_screen_result(database_url, [AAA, CCC]), "symbols": ["CCC"]}

        response = await assistant.post(
            "/api/backtests",
            json=make_universe_request(saved.json()["id"], universe_kind=universe_kind, **universe),
            headers=headers,
        )

        assert response.status_code == httpx.codes.CREATED, response.text
        backtest = (await assistant.get(f"/api/backtests/{response.json()['id']}")).json()
    assert (backtest["universe_kind"], backtest["conversation_id"]) == (universe_kind, conversation_id)
    assert backtest["survivorship_bias"] is (universe_kind == "list")


@pytest.mark.anyio
async def test_a_backtest_on_port_8001_without_saved_bars_is_refused(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        strategy_id = await create_strategy(browser, "Bar count")
        conversation_id = await create_conversation(browser, strategy_id)
        version_id = (await browser.get(f"/api/strategies/{strategy_id}")).json()["versions"][0]["id"]

        response = await assistant.post(
            "/api/backtests", json=backtest_body(version_id), headers={CONVERSATION_HEADER: str(conversation_id)}
        )
        backtests = (await assistant.get("/api/backtests")).json()

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json()["detail"].startswith("There are no saved 1 day bars of BTEST / ARCA / USD")
    assert backtests == []


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/api/health", "/api/strategies", "/strategies"])
async def test_port_8000_refuses_each_request_from_another_address_of_the_assistant_subnet(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, path: str
) -> None:
    app = create_web_app(
        settings=Settings(database_url=database_url, frontend_build_dir=frontend_build_dir),
        clock=clock,
        gateway_connection=FakeGatewayConnection(managed_accounts=["DU1234567"]),
    )
    # httpx gives the host and the port of base_url as the ASGI `server` (the local address of the request), and
    # `client` as the ASGI `client` (the peer address).
    async with (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("172.31.250.3", 40000)), base_url="http://172.31.250.4:8000"
        ) as from_assistant,
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("172.18.0.1", 40000)), base_url="http://172.18.0.3:8000"
        ) as from_default_network,
        # Rootless Podman sends a published port to the address of web in the first network by name, which is
        # atrade-assistant-internal, and connects from that same address.
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("172.31.250.4", 40000)), base_url="http://172.31.250.4:8000"
        ) as from_podman_port_forwarder,
    ):
        refused = await from_assistant.get(path)
        answered = await from_default_network.get(path)
        forwarded = await from_podman_port_forwarder.get(path)

    assert refused.status_code == httpx.codes.FORBIDDEN
    assert refused.json() == {"detail": "Port 8000 does not answer requests from the assistant network."}
    assert answered.status_code == httpx.codes.OK
    assert forwarded.status_code == httpx.codes.OK


def test_compose_does_not_publish_port_8001_and_fixes_the_assistant_subnet() -> None:
    compose = (REPO_ROOT / "deploy" / "compose.yaml").read_text()
    published: list[str] = []
    in_ports = False
    for line in compose.splitlines():
        stripped = line.strip()
        if stripped in {"ports:", "expose:"}:
            in_ports = True
        elif in_ports and stripped.startswith("- "):
            published.append(stripped.removeprefix("- ").strip('"'))
        else:
            in_ports = False

    assert published == ["${ATRADE_WEB_BIND_ADDRESS:-127.0.0.1}:${ATRADE_WEB_PORT:-8000}:8000"]
    assert not [entry for entry in published if str(ASSISTANT_PORT) in entry]
    assert f"- subnet: {ASSISTANT_SUBNET}" in compose
