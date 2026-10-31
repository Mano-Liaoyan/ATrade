"""/ws/paper-trading: pushes the paper account check result, the balance, the positions, and the open orders to the
browser.

The socket sends an "account" and an "orders" message at once and after each change, and a "heartbeat" message
after a fixed time without messages, so that the browser can see a dead connection and connect again (section 13).
"""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from atrade.foundation.instrument import Instrument
from atrade.foundation.socket_push import ChangedMessageSender, HeartbeatMessage, serve_until_disconnect
from atrade.ibkr import GatewayRequestError, PortfolioPosition
from atrade.paper_trading.manual_order_ledger import ManualOrderLedger, find_owner_positions
from atrade.paper_trading.owner_ledger_store import LedgerEntry, OwnerKind, sum_owner_cash_usd
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor
from atrade.paper_trading.paper_orders import OpenOrderResponse, read_open_orders_of_checked_account
from atrade.paper_trading.split_check_store import SplitCheck
from atrade.paper_trading.stock_split_ledger import read_needed_split_checks

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


class OwnerMessage(BaseModel):
    kind: OwnerKind
    # None for "By hand".
    forward_test_id: int | None


class OwnerPositionMessage(BaseModel):
    """The part of an IBKR position that belongs to one owner in the owner ledger (section 11.10)."""

    owner: OwnerMessage
    quantity: Decimal
    average_cost: Decimal | None


class SplitCheckMessage(BaseModel):
    """The "Split check needed" state of the instrument (section 11.11). `id` is the ID of the stock split routes.
    `stock_split_id` is None when only the position shows the stock split."""

    id: int
    stock_split_id: int | None
    split_ratio: Decimal
    account_quantity_before: Decimal
    account_quantity_after: Decimal


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
    owners: list[OwnerPositionMessage]
    # The IBKR quantity minus the sum of the owner quantities. Not 0 shows as "Unattributed" (section 11.7).
    unattributed_quantity: Decimal
    split_check: SplitCheckMessage | None


class OpenOrdersMessage(BaseModel):
    type: Literal["orders"] = "orders"
    orders: list[OpenOrderResponse]


class PaperAccountMessage(BaseModel):
    type: Literal["account"] = "account"
    check: PaperAccountCheckMessage
    balance: PaperAccountBalanceMessage | None
    positions: list[PositionMessage]
    # The account cash minus the cash of all owners. None without a USD cash value or an owner ledger (section 11.12).
    unattributed_cash_usd: Decimal | None


# The messages of /ws/paper-trading. The OpenAPI document adds their JSON Schema for the frontend types.
PAPER_TRADING_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [PaperAccountMessage, OpenOrdersMessage, HeartbeatMessage]


def convert_split_check(instrument: Instrument, split_checks: list[SplitCheck]) -> SplitCheckMessage | None:
    for split_check in split_checks:
        if split_check.instrument == instrument:
            return SplitCheckMessage(
                id=split_check.id,
                stock_split_id=split_check.stock_split_id,
                split_ratio=split_check.detected_ratio,
                account_quantity_before=split_check.account_quantity_before,
                account_quantity_after=split_check.account_quantity_after,
            )
    return None


def convert_position(
    position: PortfolioPosition, entries: list[LedgerEntry] | None, split_checks: list[SplitCheck]
) -> PositionMessage:
    instrument = Instrument(symbol=position.symbol, exchange=position.exchange, currency=position.currency)
    owner_positions = [] if entries is None else find_owner_positions(entries, instrument)
    owners = [
        OwnerPositionMessage(
            owner=OwnerMessage(kind=owner_position.owner.kind, forward_test_id=owner_position.owner.forward_test_id),
            quantity=owner_position.quantity,
            average_cost=owner_position.average_cost,
        )
        for owner_position in owner_positions
    ]
    owned_quantity = sum((owner_position.quantity for owner_position in owner_positions), Decimal(0))
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
        owners=owners,
        unattributed_quantity=position.quantity - owned_quantity,
        split_check=convert_split_check(instrument, split_checks),
    )


async def read_ledger_entries(
    paper_account_monitor: PaperAccountMonitor, ledger: ManualOrderLedger
) -> list[LedgerEntry] | None:
    account_id = paper_account_monitor.read_checked_account_id()
    if account_id is None:
        return None
    return await ledger.read_entries(account_id)


def find_unattributed_cash_usd(cash_usd: Decimal | None, entries: list[LedgerEntry] | None) -> Decimal | None:
    if cash_usd is None or entries is None:
        return None
    owners = {entry.owner for entry in entries}
    return cash_usd - sum((sum_owner_cash_usd(entries, owner) for owner in owners), Decimal(0))


async def build_account_message(
    paper_account_monitor: PaperAccountMonitor, ledger: ManualOrderLedger
) -> PaperAccountMessage:
    check = paper_account_monitor.read_check()
    balance = await paper_account_monitor.read_balance()
    entries = await read_ledger_entries(paper_account_monitor, ledger)
    account_id = paper_account_monitor.read_checked_account_id()
    split_checks = (
        []
        if account_id is None
        else await read_needed_split_checks(database_url=ledger.database_url, account=account_id)
    )
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
        positions=[
            convert_position(position, entries, split_checks) for position in paper_account_monitor.read_positions()
        ],
        unattributed_cash_usd=find_unattributed_cash_usd(None if balance is None else balance.cash_usd, entries),
    )


async def read_orders_message(
    paper_account_monitor: PaperAccountMonitor, ledger: ManualOrderLedger
) -> OpenOrdersMessage | None:
    """The orders message, or None when IB Gateway does not answer. The socket then tries again later.

    It also records the new fills of orders by hand in the owner ledger, because a fill changes the open orders.
    """
    account_id = paper_account_monitor.read_checked_account_id()
    if account_id is not None:
        await ledger.record_fills(account_id)
    try:
        orders = await read_open_orders_of_checked_account(paper_account_monitor)
    except GatewayRequestError:
        return None
    return OpenOrdersMessage(orders=orders)


async def push_account_changes(
    websocket: WebSocket, paper_account_monitor: PaperAccountMonitor, ledger: ManualOrderLedger
) -> None:
    sender = ChangedMessageSender(websocket)
    seconds_since_order_refresh = ORDER_REFRESH_INTERVAL_SECONDS
    while True:
        await sender.send_if_changed(await build_account_message(paper_account_monitor, ledger))
        if seconds_since_order_refresh >= ORDER_REFRESH_INTERVAL_SECONDS:
            seconds_since_order_refresh = 0.0
            orders_message = await read_orders_message(paper_account_monitor, ledger)
            if orders_message is not None:
                await sender.send_if_changed(orders_message)
        await sender.wait(PUSH_INTERVAL_SECONDS)
        seconds_since_order_refresh += PUSH_INTERVAL_SECONDS


def create_account_socket_router(*, paper_account_monitor: PaperAccountMonitor, ledger: ManualOrderLedger) -> APIRouter:
    router = APIRouter()

    @router.websocket(PAPER_TRADING_SOCKET_PATH)
    async def stream_paper_account(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        await serve_until_disconnect(websocket, lambda: push_account_changes(websocket, paper_account_monitor, ledger))

    return router
