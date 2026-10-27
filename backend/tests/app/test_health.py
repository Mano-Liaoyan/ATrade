"""Health route of the Web app: database reachability and server time."""

from pathlib import Path

import httpx
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection


@pytest.mark.anyio
async def test_health_reports_database_ok_and_server_time(
    web_client: httpx.AsyncClient,
) -> None:
    response = await web_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "time_utc": "2026-01-02T03:04:05Z",
    }


@pytest.mark.anyio
async def test_health_reports_unreachable_database(clock: FixedClock, frontend_build_dir: Path) -> None:
    settings = Settings(
        database_url="postgresql://atrade:wrong@127.0.0.1:1/atrade?connect_timeout=1",
        frontend_build_dir=frontend_build_dir,
    )
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "unreachable",
        "time_utc": "2026-01-02T03:04:05Z",
    }
