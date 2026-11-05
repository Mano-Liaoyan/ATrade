"""/ws/watchlist-live-bars: pushes the live daily bar of each watchlist instrument (market_data.md 8.5.1).

The socket follows the watchlist itself: it reads the instruments at the start and after each change of the
`watchlist_instrument` table, so it never subscribes to an instrument outside the watchlist. The browser sends nothing.
All sockets share the IBKR subscriptions through `LiveDailyBarHub`. Without IB Gateway, or when a subscription fails,
the instrument gets `"bar": null` and no error: the page then shows the values of the daily bars.
"""

from typing import Literal

import anyio
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage, serve_until_disconnect
from atrade.foundation.table_changes import TableChangeFeed
from atrade.market_data import BarResponse, LiveDailyBarHub, LiveDailyBarListener, to_bar_response
from atrade.watchlist.http_routes import WATCHLIST_CHANGE_SOCKET
from atrade.watchlist.watchlist_store import read_watchlist_instruments

WATCHLIST_LIVE_BAR_SOCKET_PATH = "/ws/watchlist-live-bars"
# IBKR updates a live bar about every 5 seconds. One message each second at most keeps a long watchlist light.
SEND_INTERVAL_SECONDS = 1.0


class WatchlistLiveBar(BaseModel):
    """The live daily bar of one watchlist instrument. `bar` is null when there is no live bar."""

    symbol: str
    exchange: str
    currency: str
    bar: BarResponse | None


class WatchlistLiveBarsMessage(BaseModel):
    """The instruments with a change since the last message. The first message has all followed instruments."""

    type: Literal["live_bars"] = "live_bars"
    live_bars: list[WatchlistLiveBar]


# The frontend types of these messages come from their JSON Schema (app/openapi_document.py).
WATCHLIST_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [WatchlistLiveBarsMessage, HeartbeatMessage]


async def follow_watchlist(listener: LiveDailyBarListener, feed: TableChangeFeed, database_url: str) -> None:
    with feed.subscribe(WATCHLIST_CHANGE_SOCKET.tables) as watchlist_change:
        listener.follow(await read_watchlist_instruments(database_url=database_url))
        while True:
            await watchlist_change.wait()
            listener.follow(await read_watchlist_instruments(database_url=database_url))


async def send_live_bars(websocket: WebSocket, listener: LiveDailyBarListener, send_interval_seconds: float) -> None:
    while True:
        with anyio.move_on_after(HEARTBEAT_INTERVAL_SECONDS) as wait_scope:
            await listener.wait()
        if wait_scope.cancelled_caught:
            await websocket.send_text(HeartbeatMessage().model_dump_json())
            continue
        live_bars = [
            WatchlistLiveBar(
                symbol=instrument.symbol,
                exchange=instrument.exchange,
                currency=instrument.currency,
                bar=None if bar is None else to_bar_response(bar),
            )
            for instrument, bar in listener.take_changes().items()
        ]
        await websocket.send_text(WatchlistLiveBarsMessage(live_bars=live_bars).model_dump_json())
        await anyio.sleep(send_interval_seconds)


def create_watchlist_live_bar_router(
    *,
    database_url: str,
    table_change_feed: TableChangeFeed,
    live_daily_bar_hub: LiveDailyBarHub,
    send_interval_seconds: float = SEND_INTERVAL_SECONDS,
) -> APIRouter:
    router = APIRouter()

    async def push_live_bars(websocket: WebSocket, listener: LiveDailyBarListener) -> None:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(follow_watchlist, listener, table_change_feed, database_url)
            task_group.start_soon(send_live_bars, websocket, listener, send_interval_seconds)

    @router.websocket(WATCHLIST_LIVE_BAR_SOCKET_PATH)
    async def stream_watchlist_live_bars(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        with live_daily_bar_hub.listen() as listener:
            await serve_until_disconnect(websocket, lambda: push_live_bars(websocket, listener))

    return router
