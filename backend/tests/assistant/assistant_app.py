"""Opens the Web app with the fake assistant service, for the HTTP routes and /ws/assistant."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection


@asynccontextmanager
async def open_assistant_client(
    *, database_url: str, clock: FixedClock, frontend_build_dir: Path, assistant_service: FakeAssistantService
) -> AsyncGenerator[httpx.AsyncClient]:
    app = create_web_app(
        settings=Settings(database_url=database_url, frontend_build_dir=frontend_build_dir),
        clock=clock,
        gateway_connection=FakeGatewayConnection(managed_accounts=["DU1234567"]),
        assistant_service=assistant_service,
    )
    async with httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client:
        yield client


async def create_strategy(client: httpx.AsyncClient, name: str) -> int:
    response = await client.post("/api/strategies", json={"name": name})
    assert response.status_code == httpx.codes.CREATED, response.text
    strategy_id: int = response.json()["id"]
    return strategy_id


async def create_conversation(client: httpx.AsyncClient, strategy_id: int) -> int:
    response = await client.post("/api/assistant/conversations", json={"strategy_id": strategy_id})
    assert response.status_code == httpx.codes.CREATED, response.text
    conversation_id: int = response.json()["id"]
    return conversation_id
