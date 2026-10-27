"""Routes of paper_trading: the order routes, GET /api/paper-trading/paper-capital, and /ws/paper-trading, which
pushes the paper account check result, the balance, the positions, and the open orders to the browser.

The socket sends an "account" and an "orders" message at once and after each change, and a "heartbeat" message
after a fixed time without messages, so that the browser can see a dead connection and connect again (section 13).
"""

from decimal import Decimal
from typing import Any, Literal

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from atrade.foundation.clock import Clock
from atrade.ibkr import GatewayRequestError, PortfolioPosition
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor, fetch_paper_capital_usd
from atrade.paper_trading.paper_orders import (
    ManualOrderResponse,
    OpenOrderResponse,
    OrderErrorResponse,
    OrderRefusedResponse,
    PaperOrderRoutes,
    read_open_orders_of_checked_account,
)

PUSH_INTERVAL_SECONDS = 0.25
HEARTBEAT_INTERVAL_SECONDS = 10.0
# Each refresh is one reqAllOpenOrders request to IB Gateway, so the order list refreshes less often.
ORDER_REFRESH_INTERVAL_SECONDS = 1.0
HEARTBEAT_MESSAGE = '{"type":"heartbeat"}'


class PaperAccountCheckMessage(BaseModel):
    status: Literal["disconnected", "passed", "failed"]
    message: str | None
    actual_accounts: list[str]
    expected_account: str | None


class PaperAccountBalanceMessage(BaseModel):
    net_liquidation_usd: Decimal | None
    cash_usd: Decimal | None


class PositionMessage(BaseModel):
    symbol: str
    security_type: str
    exchange: str
    currency: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


class OpenOrdersMessage(BaseModel):
    type: Literal["orders"] = "orders"
    orders: list[OpenOrderResponse]


class PaperAccountMessage(BaseModel):
    type: Literal["account"] = "account"
    check: PaperAccountCheckMessage
    balance: PaperAccountBalanceMessage | None
    positions: list[PositionMessage]


class PaperCapitalResponse(BaseModel):
    """The default paper capital of the backtest form (docs/architecture.md section 10)."""

    paper_capital_usd: Decimal


def convert_position(position: PortfolioPosition) -> PositionMessage:
    return PositionMessage(
        symbol=position.symbol,
        security_type=position.security_type,
        exchange=position.exchange,
        currency=position.currency,
        quantity=position.quantity,
        average_cost=position.average_cost,
        market_price=position.market_price,
        market_value=position.market_value,
        unrealized_pnl=position.unrealized_pnl,
    )


def build_account_message(paper_account_monitor: PaperAccountMonitor) -> PaperAccountMessage:
    check = paper_account_monitor.read_check()
    balance = paper_account_monitor.read_balance()
    balance_message = None
    if balance is not None:
        balance_message = PaperAccountBalanceMessage(
            net_liquidation_usd=balance.net_liquidation_usd, cash_usd=balance.cash_usd
        )
    return PaperAccountMessage(
        check=PaperAccountCheckMessage(
            status=check.status,
            message=check.message,
            actual_accounts=list(check.actual_accounts),
            expected_account=check.expected_account,
        ),
        balance=balance_message,
        positions=[convert_position(position) for position in paper_account_monitor.read_positions()],
    )


async def read_orders_text(paper_account_monitor: PaperAccountMonitor, last_orders_text: str) -> str:
    """The orders message. Keeps the last message when IB Gateway does not answer, and tries again later."""
    try:
        orders = await read_open_orders_of_checked_account(paper_account_monitor)
    except GatewayRequestError:
        return last_orders_text
    return OpenOrdersMessage(orders=orders).model_dump_json()


async def push_account_changes(websocket: WebSocket, paper_account_monitor: PaperAccountMonitor) -> None:
    last_sent_account_text = ""
    last_sent_orders_text = ""
    seconds_since_last_message = 0.0
    seconds_since_order_refresh = ORDER_REFRESH_INTERVAL_SECONDS
    while True:
        sent_message = False
        account_text = build_account_message(paper_account_monitor).model_dump_json()
        if account_text != last_sent_account_text:
            await websocket.send_text(account_text)
            last_sent_account_text = account_text
            sent_message = True
        if seconds_since_order_refresh >= ORDER_REFRESH_INTERVAL_SECONDS:
            seconds_since_order_refresh = 0.0
            orders_text = await read_orders_text(paper_account_monitor, last_sent_orders_text)
            if orders_text != last_sent_orders_text:
                await websocket.send_text(orders_text)
                last_sent_orders_text = orders_text
                sent_message = True
        if sent_message:
            seconds_since_last_message = 0.0
        elif seconds_since_last_message >= HEARTBEAT_INTERVAL_SECONDS:
            await websocket.send_text(HEARTBEAT_MESSAGE)
            seconds_since_last_message = 0.0
        await anyio.sleep(PUSH_INTERVAL_SECONDS)
        seconds_since_last_message += PUSH_INTERVAL_SECONDS
        seconds_since_order_refresh += PUSH_INTERVAL_SECONDS


async def wait_for_disconnect(websocket: WebSocket) -> None:
    # The browser sends nothing that the server needs. Reading the socket shows when the browser leaves.
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


def add_order_routes(
    router: APIRouter, *, paper_account_monitor: PaperAccountMonitor, database_url: str, clock: Clock
) -> None:
    routes = PaperOrderRoutes(paper_account_monitor=paper_account_monitor, database_url=database_url, clock=clock)
    refused_or_failed: dict[int | str, dict[str, Any]] = {
        status.HTTP_403_FORBIDDEN: {"model": OrderRefusedResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": OrderErrorResponse},
    }
    router.add_api_route(
        "/api/paper-trading/orders",
        routes.send_order,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ManualOrderResponse,
        responses=refused_or_failed,
    )
    router.add_api_route(
        "/api/paper-trading/orders",
        routes.list_open_orders,
        methods=["GET"],
        responses={status.HTTP_502_BAD_GATEWAY: {"model": OrderErrorResponse}},
    )
    router.add_api_route(
        "/api/paper-trading/orders/{order_id}",
        routes.cancel_order,
        methods=["DELETE"],
        status_code=status.HTTP_202_ACCEPTED,
        response_model=None,
        responses={
            **refused_or_failed,
            status.HTTP_404_NOT_FOUND: {"model": OrderErrorResponse},
            status.HTTP_409_CONFLICT: {"model": OrderErrorResponse},
        },
    )
    router.add_api_route("/api/paper-trading/manual-orders", routes.list_manual_orders, methods=["GET"])


def create_paper_trading_router(
    *, paper_account_monitor: PaperAccountMonitor, database_url: str, clock: Clock
) -> APIRouter:
    router = APIRouter()
    add_order_routes(router, paper_account_monitor=paper_account_monitor, database_url=database_url, clock=clock)

    @router.get("/api/paper-trading/paper-capital")
    def read_paper_capital() -> PaperCapitalResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        return PaperCapitalResponse(paper_capital_usd=fetch_paper_capital_usd(paper_account_monitor))

    @router.websocket("/ws/paper-trading")
    async def stream_paper_account(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        await websocket.accept()
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(push_account_changes, websocket, paper_account_monitor)
            await wait_for_disconnect(websocket)
            task_group.cancel_scope.cancel()

    return router
