"""Port 8001: the app that the assistant service calls, and the refusals of port 8000 (assistant subnet, other sites).

docs/architecture/assistant.md 25.3.2 and 25.3.3. The app has only the routes of the allow-list. It has no `/ws/`
route, no frontend files, and no OpenAPI document. Compose does not publish the port.
"""

import ipaddress
import logging
from typing import Final
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from atrade.assistant import conversation_exists
from atrade.backtest import create_backtest_assistant_router
from atrade.foundation.assistant_conversation import CONVERSATION_HEADER
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import add_validation_error_handler
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection
from atrade.market_data import ExchangeRateReader, create_custom_indicator_assistant_router
from atrade.screen import create_screen_assistant_router
from atrade.strategy import create_strategy_assistant_router

ASSISTANT_PORT: Final = 8001
# The fixed subnet of atrade-assistant-internal in deploy/compose.yaml (decided in #178).
ASSISTANT_SUBNET: Final = ipaddress.ip_network("172.31.250.0/24")
REFUSED_TEXT: Final = b'{"detail":"Port 8000 does not answer requests from the assistant network."}'
OTHER_SITE_REFUSED_TEXT: Final = b'{"detail":"Port 8000 does not answer requests from another site."}'
# The WebSocket close code "policy violation". uvicorn answers a close before accept with HTTP 403.
POLICY_VIOLATION_CLOSE_CODE: Final = 1008

__all__ = [
    "ASSISTANT_PORT",
    "ASSISTANT_SUBNET",
    "CONVERSATION_HEADER",
    "RefuseAssistantSubnet",
    "RefuseOtherSite",
    "create_assistant_port_app",
]

logger = logging.getLogger("atrade.web")


def create_assistant_port_app(*, settings: Settings, clock: Clock, gateway_connection: GatewayConnection) -> FastAPI:
    async def check_conversation(conversation_id: int) -> bool:
        return await conversation_exists(database_url=settings.database_url, conversation_id=conversation_id)

    app = FastAPI(title="ATrade assistant port", openapi_url=None, docs_url=None, redoc_url=None)
    add_validation_error_handler(app)
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
    app.include_router(
        create_screen_assistant_router(
            database_url=settings.database_url, clock=clock, conversation_exists=check_conversation
        )
    )
    app.include_router(
        create_custom_indicator_assistant_router(
            database_url=settings.database_url, clock=clock, conversation_exists=check_conversation
        )
    )
    return app


def is_assistant_address(scope: Scope) -> bool:
    """True when the peer address (ASGI `client`) is in the assistant subnet and is not the local address.

    The local address (ASGI `server`) alone is not enough: rootless Podman sends a published port to the address of
    web in atrade-assistant-internal and connects from that same address. A peer that is web itself is not assistant.
    """
    client = scope.get("client")
    if client is None:
        return False
    try:
        peer = ipaddress.ip_address(client[0])
    except ValueError:
        # A host name (for example in a test client) is not an address of the subnet.
        return False
    if peer not in ASSISTANT_SUBNET:
        return False
    server = scope.get("server")
    return server is None or server[0] != client[0]


async def refuse_request(scope: Scope, send: Send, refused_text: bytes) -> None:
    """A WebSocket is closed before accept, so uvicorn answers 403. Each other request gets 403 with `refused_text`."""
    if scope["type"] == "websocket":
        await send({"type": "websocket.close", "code": POLICY_VIOLATION_CLOSE_CODE})
        return
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(refused_text)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": refused_text})


class RefuseAssistantSubnet:
    """ASGI middleware of port 8000: 403 for each request from another address of the assistant subnet."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or not is_assistant_address(scope):
            await self.app(scope, receive, send)
            return
        await refuse_request(scope, send, REFUSED_TEXT)


def read_origin_host(origin: bytes) -> str:
    """The host and port of an Origin header. Empty for "null" (a sandboxed page) and for a value that is not a URL."""
    try:
        return urlsplit(origin.decode("latin-1")).netloc.lower()
    except ValueError:
        return ""


def is_other_site_request(scope: Scope) -> bool:
    """True when a page of another site sent a WebSocket or a non-GET request. The browser sets Origin and the page
    cannot change it. A tool sends no Origin, so it is not refused. The Vite proxy, Cloudflare, and Nginx Proxy Manager
    keep the Host header of the browser (docs/architecture.md section 14)."""
    if scope["type"] == "http" and scope["method"] == "GET":
        return False
    headers = dict(scope["headers"])
    origin = headers.get(b"origin")
    if origin is None:
        return False
    origin_host = read_origin_host(origin)
    return not origin_host or origin_host != headers.get(b"host", b"").decode("latin-1").lower()


class RefuseOtherSite:
    """ASGI middleware of port 8000: 403 for a WebSocket or a non-GET request from a page of another site."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or not is_other_site_request(scope):
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        logger.warning(
            "Refused a request from another site: Origin %r, Host %r", headers.get(b"origin"), headers.get(b"host")
        )
        await refuse_request(scope, send, OTHER_SITE_REFUSED_TEXT)
