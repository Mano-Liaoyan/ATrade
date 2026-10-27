"""GET /api/market-data/instrument-search: finds instruments by symbol through the IBKR fake."""

from pathlib import Path

import httpx
import pytest

from atrade.app import create_web_app
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

SEARCH_PATH = "/api/market-data/instrument-search"


async def search_instruments(
    gateway_connection: FakeGatewayConnection, clock: FixedClock, frontend_build_dir: Path, query: str
) -> httpx.Response:
    settings = Settings(database_url="postgresql://unused/atrade", frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(SEARCH_PATH, params={"query": query})


def create_connected_fake(instruments: list[Instrument]) -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"], instruments=instruments)
    gateway_connection.connected = True
    return gateway_connection


@pytest.mark.anyio
async def test_returns_symbol_exchange_and_currency_of_each_match(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = create_connected_fake(
        [
            Instrument(symbol="700", exchange="SEHK", currency="HKD"),
            Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD"),
        ]
    )

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, "700")

    assert response.status_code == 200
    assert response.json() == {"instruments": [{"symbol": "700", "exchange": "SEHK", "currency": "HKD"}]}


@pytest.mark.anyio
async def test_matches_symbols_without_regard_to_letter_case(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = create_connected_fake([Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")])

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, " aap ")

    assert response.json() == {"instruments": [{"symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD"}]}


@pytest.mark.anyio
async def test_returns_an_empty_list_when_no_instrument_matches(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = create_connected_fake([Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")])

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, "ZZZZ")

    assert response.status_code == 200
    assert response.json() == {"instruments": []}


@pytest.mark.anyio
async def test_refuses_a_query_with_only_spaces(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = create_connected_fake([])

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, "   ")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_reports_unreachable_gateway_with_its_address(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"], is_gateway_reachable=False)

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, "700")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "IB Gateway is not reachable at ib-gateway:4004. Instrument search needs IB Gateway."
    }


@pytest.mark.anyio
async def test_reports_a_failed_search_when_the_gateway_answers_with_an_error(
    clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = create_connected_fake([])
    gateway_connection.search_error_message = "IB Gateway did not answer the instrument search in time."

    response = await search_instruments(gateway_connection, clock, frontend_build_dir, "700")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "The instrument search failed: IB Gateway did not answer the instrument search in time."
    }
