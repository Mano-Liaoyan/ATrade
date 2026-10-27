"""/ws/paper-trading: pushes the paper account check result, the balance, the positions, and the open orders to the
browser.

The socket sends an "account" and an "orders" message at once and after each change, and a "heartbeat" message
after a fixed time without messages, so that the browser can see a dead connection and connect again (section 13).
"""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from atrade.foundation.socket_push import ChangedMessageSender, HeartbeatMessage, serve_until_disconnect
from atrade.ibkr import GatewayRequestError, PortfolioPosition
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor
from atrade.paper_trading.paper_orders import OpenOrderResponse, read_open_orders_of_checked_account

PAPER_TRADING_SOCKET_PATH = "/ws/paper-trading"
PUSH_INTERVAL_SECONDS = 0.25
# Each refresh is one reqAllOpenOrders request to IB Gateway, so the order list refreshes less often.
ORDER_REFRESH_INTERVAL_SECONDS = 1.0


class PaperAccountCheckMessage(BaseModel):
    status: Literal["disconnected", "passed", "failed"]
    message: str | None
    actual_accounts: list[str]
    expected_account: str | None


class PaperAccountBalanceMessage(BaseModel):
    """The balance in USD. The base currency values and the rate show what ATrade converted (section 11.9)."""

    net_liquidation_usd: Decimal | None
    cash_usd: Decimal | None
    base_currency: str | None
    net_liquidation_base: Decimal | None
    cash_base: Decimal | None
    # USD for 1 unit of the base currency. 1 for a USD account.
    usd_per_base_unit: Decimal | None
    exchange_rate_source: Literal["base_currency_is_usd", "account", "ibkr_forex"] | None
    # Why the USD values are missing, or None.
    message: str | None


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


# The messages of /ws/paper-trading. The OpenAPI document adds their JSON Schema for the frontend types.
PAPER_TRADING_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [PaperAccountMessage, OpenOrdersMessage, HeartbeatMessage]


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


async def build_account_message(paper_account_monitor: PaperAccountMonitor) -> PaperAccountMessage:
    check = paper_account_monitor.read_check()
    balance = await paper_account_monitor.read_balance()
    balance_message = None
    if balance is not None:
        balance_message = PaperAccountBalanceMessage(
            net_liquidation_usd=balance.net_liquidation_usd,
            cash_usd=balance.cash_usd,
            base_currency=balance.base_currency,
            net_liquidation_base=balance.net_liquidation_base,
            cash_base=balance.cash_base,
            usd_per_base_unit=balance.usd_per_base_unit,
            exchange_rate_source=balance.exchange_rate_source,
            message=balance.message,
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


async def read_orders_message(paper_account_monitor: PaperAccountMonitor) -> OpenOrdersMessage | None:
    """The orders message, or None when IB Gateway does not answer. The socket then tries again later."""
    try:
        orders = await read_open_orders_of_checked_account(paper_account_monitor)
    except GatewayRequestError:
        return None
    return OpenOrdersMessage(orders=orders)


async def push_account_changes(websocket: WebSocket, paper_account_monitor: PaperAccountMonitor) -> None:
    sender = ChangedMessageSender(websocket)
    seconds_since_order_refresh = ORDER_REFRESH_INTERVAL_SECONDS
    while True:
        await sender.send_if_changed(await build_account_message(paper_account_monitor))
        if seconds_since_order_refresh >= ORDER_REFRESH_INTERVAL_SECONDS:
            seconds_since_order_refresh = 0.0
            orders_message = await read_orders_message(paper_account_monitor)
            if orders_message is not None:
                await sender.send_if_changed(orders_message)
        await sender.wait(PUSH_INTERVAL_SECONDS)
        seconds_since_order_refresh += PUSH_INTERVAL_SECONDS


def create_account_socket_router(*, paper_account_monitor: PaperAccountMonitor) -> APIRouter:
    router = APIRouter()

    @router.websocket(PAPER_TRADING_SOCKET_PATH)
    async def stream_paper_account(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        await serve_until_disconnect(websocket, lambda: push_account_changes(websocket, paper_account_monitor))

    return router
