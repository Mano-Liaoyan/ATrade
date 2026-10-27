"""/ws/market-data: pushes the live bar of one instrument and one bar period to the chart.

The socket sends a "bar" message at once and after each IBKR update, and a "heartbeat" message after a time without
another message, so that the browser can see a dead connection and connect again (section 13). When IB Gateway is
not reachable or the subscription fails, the socket sends an "error" message and closes. The browser connects again.
"""

from contextlib import aclosing
from typing import Annotated, Literal

import anyio
from fastapi import APIRouter, Query, WebSocket, status
from pydantic import BaseModel

from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage, wait_for_disconnect
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data.bar_models import BarResponse, InstrumentField, to_bar_response

MARKET_DATA_SOCKET_PATH = "/ws/market-data"
HEARTBEAT_CHECK_SECONDS = 1.0


class LiveBarsQuery(BaseModel):
    """The query parameters of /ws/market-data."""

    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    bar_period: BarPeriod


class LiveBarMessage(BaseModel):
    """The current bar. A bar with the time of the last bar replaces it; a later time adds a bar."""

    type: Literal["bar"] = "bar"
    bar: BarResponse


class LiveBarErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    detail: str


# The frontend types of these messages come from their JSON Schema (app/openapi_document.py).
MARKET_DATA_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [LiveBarMessage, LiveBarErrorMessage, HeartbeatMessage]


class LiveBarSender:
    """Sends the messages of one socket. One lock keeps the bar task and the heartbeat task from sending at once."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.lock = anyio.Lock()
        self.seconds_since_last_message = 0.0

    async def send(self, message: BaseModel) -> None:
        async with self.lock:
            await self.websocket.send_text(message.model_dump_json())
            self.seconds_since_last_message = 0.0

    async def send_heartbeats(self) -> None:
        while True:
            await anyio.sleep(HEARTBEAT_CHECK_SECONDS)
            self.seconds_since_last_message += HEARTBEAT_CHECK_SECONDS
            if self.seconds_since_last_message >= HEARTBEAT_INTERVAL_SECONDS:
                await self.send(HeartbeatMessage())


def create_live_bar_router(*, gateway_connection: GatewayConnection, host: str, port: int) -> APIRouter:
    router = APIRouter()

    async def push_live_bars(sender: LiveBarSender, instrument: Instrument, bar_period: BarPeriod) -> str:
        """Sends each live bar. Returns the error text when the stream ends."""
        try:
            async with aclosing(gateway_connection.stream_live_bars(instrument, bar_period)) as live_bars:
                async for bar in live_bars:
                    await sender.send(LiveBarMessage(bar=to_bar_response(bar)))
        except GatewayRequestError as error:
            return f"Reading live bars from IB Gateway failed: {error}"
        return "IB Gateway ended the live bars."

    @router.websocket(MARKET_DATA_SOCKET_PATH)
    async def stream_live_bars(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        websocket: WebSocket, live_bars_query: Annotated[LiveBarsQuery, Query()]
    ) -> None:
        await websocket.accept()
        sender = LiveBarSender(websocket)
        if not gateway_connection.is_connected():
            detail = f"IB Gateway is not reachable at {host}:{port}. Live bars need IB Gateway."
            await sender.send(LiveBarErrorMessage(detail=detail))
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return
        instrument = Instrument(
            symbol=live_bars_query.symbol.strip(),
            exchange=live_bars_query.exchange.strip(),
            currency=live_bars_query.currency.strip(),
        )
        error_detail: str | None = None
        async with anyio.create_task_group() as task_group:

            async def push_until_error() -> None:
                nonlocal error_detail
                error_detail = await push_live_bars(sender, instrument, live_bars_query.bar_period)
                await sender.send(LiveBarErrorMessage(detail=error_detail))
                task_group.cancel_scope.cancel()

            task_group.start_soon(push_until_error)
            task_group.start_soon(sender.send_heartbeats)
            await wait_for_disconnect(websocket)
            task_group.cancel_scope.cancel()
        if error_detail is not None:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    return router
