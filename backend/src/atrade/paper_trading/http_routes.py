"""/ws/paper-trading: pushes the paper account check result, the balance, and the positions to the browser.

The socket sends an "account" message at once and after each change, and a "heartbeat" message at a fixed
interval, so that the browser can see a dead connection and connect again (section 13).
"""

from decimal import Decimal
from typing import Literal

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from atrade.ibkr import PortfolioPosition
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor

PUSH_INTERVAL_SECONDS = 0.25
HEARTBEAT_INTERVAL_SECONDS = 10.0
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


class PaperAccountMessage(BaseModel):
    type: Literal["account"] = "account"
    check: PaperAccountCheckMessage
    balance: PaperAccountBalanceMessage | None
    positions: list[PositionMessage]


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


async def push_account_changes(websocket: WebSocket, paper_account_monitor: PaperAccountMonitor) -> None:
    last_sent_text = ""
    seconds_since_last_message = 0.0
    while True:
        account_text = build_account_message(paper_account_monitor).model_dump_json()
        if account_text != last_sent_text:
            await websocket.send_text(account_text)
            last_sent_text = account_text
            seconds_since_last_message = 0.0
        elif seconds_since_last_message >= HEARTBEAT_INTERVAL_SECONDS:
            await websocket.send_text(HEARTBEAT_MESSAGE)
            seconds_since_last_message = 0.0
        await anyio.sleep(PUSH_INTERVAL_SECONDS)
        seconds_since_last_message += PUSH_INTERVAL_SECONDS


async def wait_for_disconnect(websocket: WebSocket) -> None:
    # The browser sends nothing that the server needs. Reading the socket shows when the browser leaves.
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


def create_paper_trading_router(*, paper_account_monitor: PaperAccountMonitor) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/paper-trading")
    async def stream_paper_account(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        await websocket.accept()
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(push_account_changes, websocket, paper_account_monitor)
            await wait_for_disconnect(websocket)
            task_group.cancel_scope.cancel()

    return router
