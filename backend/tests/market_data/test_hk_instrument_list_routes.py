"""HK instrument list HTTP routes: add pasted symbols, list, and delete. Real PostgreSQL and the IBKR fake."""

from pathlib import Path

import httpx
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

HK_LIST_PATH = "/api/market-data/hk-instrument-list"
ADDED_AT_UTC = "2026-01-02T03:04:05Z"


def create_hk_list_client(
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
async def test_adds_pasted_symbols_and_lists_them_in_the_order_of_adding(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_hk_list_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        add_response = await client.post(HK_LIST_PATH, json={"symbols": ["9988", " 700 "]})
        list_response = await client.get(HK_LIST_PATH)

    assert add_response.status_code == 200
    assert add_response.json() == {"added": ["9988", "700"], "not_found": [], "already_in_list": []}
    assert list_response.status_code == 200
    instruments = list_response.json()["instruments"]
    assert [{key: value for key, value in item.items() if key != "id"} for item in instruments] == [
        {"symbol": "9988", "exchange": "SEHK", "currency": "HKD", "added_at_utc": ADDED_AT_UTC},
        {"symbol": "700", "exchange": "SEHK", "currency": "HKD", "added_at_utc": ADDED_AT_UTC},
    ]
    assert instruments[0]["id"] < instruments[1]["id"]


@pytest.mark.anyio
async def test_reports_symbols_that_ibkr_does_not_know_on_sehk_and_symbols_already_in_the_list(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_hk_list_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        await client.post(HK_LIST_PATH, json={"symbols": ["700"]})
        # AAPL is a NASDAQ instrument, so it is not an HK instrument. A symbol pasted 2 times is added 1 time.
        add_response = await client.post(HK_LIST_PATH, json={"symbols": ["700", "AAPL", "123456", "9988", "9988"]})
        list_response = await client.get(HK_LIST_PATH)

    assert add_response.status_code == 200
    assert add_response.json() == {
        "added": ["9988"],
        "not_found": ["AAPL", "123456"],
        "already_in_list": ["700", "9988"],
    }
    assert [item["symbol"] for item in list_response.json()["instruments"]] == ["700", "9988"]


@pytest.mark.anyio
@pytest.mark.parametrize("symbols", [[], [""], ["  "], ["700", "X" * 33]])
async def test_refuses_an_empty_list_or_an_empty_or_too_long_symbol(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, symbols: list[str]
) -> None:
    async with create_hk_list_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        add_response = await client.post(HK_LIST_PATH, json={"symbols": symbols})
        list_response = await client.get(HK_LIST_PATH)

    assert add_response.status_code == 422
    assert list_response.json() == {"instruments": []}


@pytest.mark.anyio
async def test_reports_an_unreachable_gateway_and_adds_nothing(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    async with create_hk_list_client(database_url, clock, frontend_build_dir, gateway_connection) as client:
        add_response = await client.post(HK_LIST_PATH, json={"symbols": ["700"]})
        list_response = await client.get(HK_LIST_PATH)

    assert add_response.status_code == 503
    assert add_response.json() == {
        "detail": "IB Gateway is not reachable at ib-gateway:4004. The instrument check needs IB Gateway."
    }
    assert list_response.json() == {"instruments": []}


@pytest.mark.anyio
async def test_reports_a_failed_instrument_check_and_adds_nothing(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = create_connected_fake()
    gateway_connection.search_error_message = "IB Gateway did not answer the instrument search in time."
    async with create_hk_list_client(database_url, clock, frontend_build_dir, gateway_connection) as client:
        add_response = await client.post(HK_LIST_PATH, json={"symbols": ["700", "9988"]})
        list_response = await client.get(HK_LIST_PATH)

    assert add_response.status_code == 502
    assert add_response.json() == {
        "detail": "The instrument check failed: IB Gateway did not answer the instrument search in time."
    }
    assert list_response.json() == {"instruments": []}


@pytest.mark.anyio
async def test_deletes_an_instrument_and_reports_an_instrument_that_is_not_in_the_list(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_hk_list_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        await client.post(HK_LIST_PATH, json={"symbols": ["700", "9988"]})
        tencent, alibaba = (await client.get(HK_LIST_PATH)).json()["instruments"]
        delete_response = await client.delete(f"{HK_LIST_PATH}/{tencent['id']}")
        second_delete_response = await client.delete(f"{HK_LIST_PATH}/{tencent['id']}")
        list_response = await client.get(HK_LIST_PATH)

    assert delete_response.status_code == 204
    assert second_delete_response.status_code == 404
    assert second_delete_response.json() == {"detail": "This instrument is not in the HK instrument list."}
    assert list_response.json() == {"instruments": [alibaba]}


@pytest.mark.anyio
async def test_lists_and_deletes_without_ib_gateway(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with create_hk_list_client(database_url, clock, frontend_build_dir, create_connected_fake()) as client:
        await client.post(HK_LIST_PATH, json={"symbols": ["700"]})
    async with create_hk_list_client(
        database_url, clock, frontend_build_dir, FakeGatewayConnection(managed_accounts=["DU1234567"])
    ) as client:
        [tencent] = (await client.get(HK_LIST_PATH)).json()["instruments"]
        delete_response = await client.delete(f"{HK_LIST_PATH}/{tencent['id']}")

    assert delete_response.status_code == 204
