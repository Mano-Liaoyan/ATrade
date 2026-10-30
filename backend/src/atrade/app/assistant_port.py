"""Port 8001: the app that the assistant service calls, and the refusal of its subnet on port 8000.

docs/architecture/assistant.md 25.3.2 and 25.3.3. The app has only the routes of the allow-list. It has no `/ws/`
route, no frontend files, and no OpenAPI document. Compose does not publish the port.
"""

import ipaddress
from typing import Final

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from atrade.assistant import conversation_exists
from atrade.backtest import create_backtest_assistant_router
from atrade.foundation.assistant_conversation import CONVERSATION_HEADER
from atrade.foundation.clock import Clock
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection
from atrade.market_data import ExchangeRateReader
from atrade.strategy import create_strategy_assistant_router

ASSISTANT_PORT: Final = 8001
# The fixed subnet of atrade-assistant-internal in deploy/compose.yaml (decided in #178).
ASSISTANT_SUBNET: Final = ipaddress.ip_network("172.31.250.0/24")
REFUSED_TEXT: Final = b'{"detail":"Port 8000 does not answer requests from the assistant network."}'
# The WebSocket close code "policy violation". uvicorn answers a close before accept with HTTP 403.
POLICY_VIOLATION_CLOSE_CODE: Final = 1008

__all__ = [
    "ASSISTANT_PORT",
    "ASSISTANT_SUBNET",
    "CONVERSATION_HEADER",
    "RefuseAssistantSubnet",
    "create_assistant_port_app",
]


def create_assistant_port_app(*, settings: Settings, clock: Clock, gateway_connection: GatewayConnection) -> FastAPI:
    async def check_conversation(conversation_id: int) -> bool:
        return await conversation_exists(database_url=settings.database_url, conversation_id=conversation_id)

    app = FastAPI(title="ATrade assistant port", openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(
        create_strategy_assistant_router(
            database_url=settings.database_url, clock=clock, conversation_exists=check_conversation
        )
    )
    exchange_rate_reader = ExchangeRateReader(
        database_url=settings.database_url, clock=clock, gateway_connection=gateway_connection
    )
    app.include_router(
        create_backtest_assistant_router(
            database_url=settings.database_url,
            clock=clock,
            exchange_rate_reader=exchange_rate_reader,
            conversation_exists=check_conversation,
        )
    )
    return app


def is_assistant_address(scope: Scope) -> bool:
    """True when the local address of the request (ASGI `server`) is in the assistant subnet."""
    server = scope.get("server")
    if server is None:
        return False
    try:
        address = ipaddress.ip_address(server[0])
    except ValueError:
        # A host name (for example in a test client) is not an address of the subnet.
        return False
    return address in ASSISTANT_SUBNET


class RefuseAssistantSubnet:
    """ASGI middleware of port 8000: 403 for each request that arrives on an address of the assistant subnet."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or not is_assistant_address(scope):
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": POLICY_VIOLATION_CLOSE_CODE})
            return
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(REFUSED_TEXT)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": REFUSED_TEXT})
