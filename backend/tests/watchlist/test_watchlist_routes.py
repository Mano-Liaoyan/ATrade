"""Watchlist HTTP routes: add, delete, and list instruments. Real PostgreSQL and the IBKR fake."""

from pathlib import Path

import httpx
import pytest

from atrade.app import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

WATCHLIST_PATH = "/api/watchlist"
TENCENT = {"symbol": "700", "exchange": "SEHK", "currency": "HKD"}
APPLE = {"symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD"}
ADDED_AT_UTC = "2026-01-02T03:04:05Z"


def create_watchlist_client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> httpx.AsyncClient:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def create_connected_fake() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    return gateway_connection


@pytest.mark.anyio
async def test_lists_added_instruments_in_the_order_of_adding(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        tencent_response = await client.post(WATCHLIST_PATH, json=TENCENT)
        apple_response = await client.post(WATCHLIST_PATH, json=APPLE)
        list_response = await client.get(WATCHLIST_PATH)

    assert tencent_response.status_code == 201
    assert apple_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json() == {
        "instruments": [
            {"id": tencent_response.json()["id"], **TENCENT, "added_at_utc": ADDED_AT_UTC},
            {"id": apple_response.json()["id"], **APPLE, "added_at_utc": ADDED_AT_UTC},
        ]
    }


@pytest.mark.anyio
async def test_keeps_the_watchlist_after_a_restart_of_the_web_app(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        await client.post(WATCHLIST_PATH, json=TENCENT)

    # A new app with a new Gateway connection reads the same database, like the Web process after a restart.
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        list_response = await client.get(WATCHLIST_PATH)

    assert [instrument["symbol"] for instrument in list_response.json()["instruments"]] == ["700"]


@pytest.mark.anyio
async def test_deletes_an_instrument_from_the_watchlist(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        tencent_id = (await client.post(WATCHLIST_PATH, json=TENCENT)).json()["id"]
        await client.post(WATCHLIST_PATH, json=APPLE)
        delete_response = await client.delete(f"{WATCHLIST_PATH}/{tencent_id}")
        list_response = await client.get(WATCHLIST_PATH)

    assert delete_response.status_code == 204
    assert [instrument["symbol"] for instrument in list_response.json()["instruments"]] == ["AAPL"]


@pytest.mark.anyio
async def test_reports_a_delete_of_an_instrument_that_is_not_in_the_watchlist(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        delete_response = await client.delete(f"{WATCHLIST_PATH}/12345")

    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "This instrument is not in the watchlist."}


@pytest.mark.anyio
async def test_refuses_to_add_the_same_instrument_twice(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        await client.post(WATCHLIST_PATH, json=TENCENT)
        second_response = await client.post(WATCHLIST_PATH, json=TENCENT)
        list_response = await client.get(WATCHLIST_PATH)

    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "This instrument is already in the watchlist."}
    assert len(list_response.json()["instruments"]) == 1


@pytest.mark.anyio
async def test_refuses_an_instrument_that_ibkr_does_not_know(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    unknown_instrument = {"symbol": "700", "exchange": "NASDAQ", "currency": "USD"}
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        add_response = await client.post(WATCHLIST_PATH, json=unknown_instrument)
        list_response = await client.get(WATCHLIST_PATH)

    assert add_response.status_code == 404
    assert add_response.json() == {
        "detail": "IBKR has no instrument 700 / NASDAQ / USD. Add an instrument from the instrument search."
    }
    assert list_response.json() == {"instruments": []}


@pytest.mark.anyio
async def test_refuses_an_empty_symbol(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> None:
    async with create_watchlist_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        add_response = await client.post(WATCHLIST_PATH, json={**TENCENT, "symbol": "  "})

    assert add_response.status_code == 422


@pytest.mark.anyio
async def test_reports_unreachable_gateway_when_adding(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"], is_gateway_reachable=False)
    async with create_watchlist_client(database_url, clock, frontend_build_dir, gateway_connection) as client:
        add_response = await client.post(WATCHLIST_PATH, json=TENCENT)
        list_response = await client.get(WATCHLIST_PATH)

    assert add_response.status_code == 503
    assert add_response.json() == {
        "detail": "IB Gateway is not reachable at ib-gateway:4004. The instrument check needs IB Gateway."
    }
    assert list_response.status_code == 200


@pytest.mark.anyio
async def test_reports_a_failed_instrument_check_when_the_gateway_answers_with_an_error(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = create_connected_fake()
    gateway_connection.search_error_message = "IB Gateway did not answer the instrument search in time."
    async with create_watchlist_client(database_url, clock, frontend_build_dir, gateway_connection) as client:
        add_response = await client.post(WATCHLIST_PATH, json=TENCENT)

    assert add_response.status_code == 502
    assert add_response.json() == {
        "detail": "The instrument check failed: IB Gateway did not answer the instrument search in time."
    }
