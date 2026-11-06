"""Port 8000 refuses a WebSocket and a changing request from a page of another site (docs/architecture.md section 6).

The base URL of the client is http://test, so the Host header is "test".
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from httpx_ws import WebSocketDisconnect, aconnect_ws

from atrade.app.assistant_port import POLICY_VIOLATION_CLOSE_CODE
from tests.assistant.assistant_app import open_assistant_client
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock

SPLIT_APPLY_PATH = "/api/paper-trading/stock-splits/1/apply"
OTHER_ORIGINS = ["https://evil.example", "http://test:8080", "null", "http://["]


def is_policy_violation(error: WebSocketDisconnect) -> bool:
    return error.code == POLICY_VIOLATION_CLOSE_CODE


@pytest.fixture
async def client(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> AsyncGenerator[httpx.AsyncClient]:
    async with open_assistant_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        assistant_service=FakeAssistantService(),
    ) as client:
        yield client


@pytest.mark.anyio
@pytest.mark.parametrize("origin", OTHER_ORIGINS)
async def test_refuses_a_post_from_another_site(client: httpx.AsyncClient, origin: str) -> None:
    response = await client.post(SPLIT_APPLY_PATH, headers={"Origin": origin})

    assert response.status_code == httpx.codes.FORBIDDEN
    assert "another site" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize("headers", [{}, {"Origin": "http://test"}, {"Origin": "HTTP://TEST"}])
async def test_a_post_of_the_same_site_or_of_a_tool_reaches_the_route(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    response = await client.post(SPLIT_APPLY_PATH, headers=headers)

    assert response.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
async def test_a_get_from_another_site_reaches_the_route(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/access-session", headers={"Origin": "https://evil.example"})

    assert response.status_code == httpx.codes.OK


@pytest.mark.anyio
@pytest.mark.parametrize("origin", OTHER_ORIGINS)
async def test_refuses_a_websocket_from_another_site(client: httpx.AsyncClient, origin: str) -> None:
    # The middleware closes the socket before accept, with the policy violation code.
    with pytest.raises(WebSocketDisconnect, check=is_policy_violation):
        async with aconnect_ws("/ws/assistant", client, headers={"Origin": origin}):
            pass


@pytest.mark.anyio
@pytest.mark.parametrize("headers", [{}, {"Origin": "http://test"}])
async def test_a_websocket_of_the_same_site_or_of_a_tool_connects(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    async with aconnect_ws("/ws/assistant", client, headers=headers) as socket:
        await socket.close()
