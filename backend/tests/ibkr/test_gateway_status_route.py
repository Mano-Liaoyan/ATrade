"""GET /api/ibkr/gateway: tells the UI if the Web process is connected to IB Gateway."""

from pathlib import Path

import httpx
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection


async def read_gateway_status(
    gateway_connection: FakeGatewayConnection, clock: FixedClock, frontend_build_dir: Path
) -> httpx.Response:
    settings = Settings(database_url="postgresql://unused/atrade", frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/api/ibkr/gateway")


@pytest.mark.anyio
async def test_reports_connected_gateway(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True

    response = await read_gateway_status(gateway_connection, clock, frontend_build_dir)

    assert response.status_code == 200
    assert response.json() == {"status": "connected", "host": "ib-gateway", "port": 4004}


@pytest.mark.anyio
async def test_reports_unreachable_gateway_with_its_address(clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"], is_gateway_reachable=False)

    response = await read_gateway_status(gateway_connection, clock, frontend_build_dir)

    assert response.status_code == 200
    assert response.json() == {"status": "unreachable", "host": "ib-gateway", "port": 4004}
