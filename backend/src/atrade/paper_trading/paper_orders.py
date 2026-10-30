"""Paper orders sent by hand: send, list, and cancel. The order list is all open orders of the paper account.

Each order and each cancel runs the paper account check first and fails closed (section 11.2). IBKR is the only
source of order status. ATrade stores only its orders by hand, without status (section 11.4).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

import psycopg
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints, model_validator

from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import MANUAL_ORDER_REF, read_order_source
from atrade.ibkr import Execution, GatewayRequestError, OpenOrder, OrderRequest, OrderSide, OrderType, TimeInForce
from atrade.paper_trading import manual_order_store
from atrade.paper_trading.manual_order_ledger import LedgerRule, ManualOrderLedger, OrderByHand, OrderRefusal
from atrade.paper_trading.paper_account_check import PaperAccountCheckError
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor

MAX_INSTRUMENT_FIELD_LENGTH = 32

InstrumentField = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_INSTRUMENT_FIELD_LENGTH)
]


class SendOrderRequest(BaseModel):
    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    side: OrderSide
    quantity: Annotated[int, Field(gt=0)]
    order_type: OrderType
    limit_price: Annotated[Decimal, Field(gt=0)] | None
    time_in_force: TimeInForce

    @model_validator(mode="after")
    def require_limit_price_only_for_limit_orders(self) -> Self:
        if self.order_type == "LMT" and self.limit_price is None:
            message = "A limit order needs a limit price."
            raise ValueError(message)
        if self.order_type == "MKT" and self.limit_price is not None:
            message = "A market order has no limit price."
            raise ValueError(message)
        return self


class ManualOrderResponse(BaseModel):
    id: int
    created_at_utc: datetime
    account: str
    symbol: str
    exchange: str
    currency: str
    side: str
    quantity: int
    order_type: str
    limit_price: Decimal | None
    time_in_force: str
    ibkr_order_id: int


class ManualOrderWithFillsResponse(ManualOrderResponse):
    """A stored order by hand with its fills from reqExecutions. None when ATrade cannot ask IBKR."""

    filled_quantity: Decimal | None
    average_fill_price: Decimal | None


class ManualOrderListResponse(BaseModel):
    manual_orders: list[ManualOrderWithFillsResponse]


class OrderSourceResponse(BaseModel):
    kind: Literal["by_hand", "forward_test"]
    forward_test_id: int | None


class OpenOrderResponse(BaseModel):
    order_id: int
    account: str
    symbol: str
    exchange: str
    currency: str
    side: str
    quantity: Decimal
    order_type: str
    limit_price: Decimal | None
    time_in_force: str
    status: str
    filled_quantity: Decimal
    source: OrderSourceResponse
    can_cancel: bool


class OpenOrderListResponse(BaseModel):
    orders: list[OpenOrderResponse]


class OrderRefusedResponse(BaseModel):
    """The paper account check did not pass. ATrade did not send the order."""

    detail: str
    actual_accounts: list[str]
    expected_account: str | None


class OrderErrorResponse(BaseModel):
    detail: str


class OrderRefusedByLedgerResponse(BaseModel):
    """An order rule of the owner ledger failed for "By hand". ATrade did not send the order (section 11.10)."""

    detail: str
    rule: LedgerRule


def to_manual_order_response(record: manual_order_store.ManualOrderRecord) -> ManualOrderResponse:
    return ManualOrderResponse(
        id=record.id,
        created_at_utc=record.created_at_utc,
        account=record.account,
        symbol=record.symbol,
        exchange=record.exchange,
        currency=record.currency,
        side=record.side,
        quantity=record.quantity,
        order_type=record.order_type,
        limit_price=record.limit_price,
        time_in_force=record.time_in_force,
        ibkr_order_id=record.ibkr_order_id,
    )


def is_cancellable_by_hand(order: OpenOrder, web_client_id: int) -> bool:
    """Only orders by hand of the Web client ID. IBKR lets a client cancel only its own orders."""
    return read_order_source(order.order_ref).kind == "by_hand" and order.client_id == web_client_id


def to_open_order_response(order: OpenOrder, web_client_id: int) -> OpenOrderResponse:
    source = read_order_source(order.order_ref)
    return OpenOrderResponse(
        order_id=order.order_id,
        account=order.account,
        symbol=order.instrument.symbol,
        exchange=order.instrument.exchange,
        currency=order.instrument.currency,
        side=order.side,
        quantity=order.quantity,
        order_type=order.order_type,
        limit_price=order.limit_price,
        time_in_force=order.time_in_force,
        status=order.status,
        filled_quantity=order.filled_quantity,
        source=OrderSourceResponse(kind=source.kind, forward_test_id=source.forward_test_id),
        can_cancel=is_cancellable_by_hand(order, web_client_id),
    )


def add_fills(
    record: manual_order_store.ManualOrderRecord, executions: list[Execution] | None, web_client_id: int
) -> ManualOrderWithFillsResponse:
    order = to_manual_order_response(record)
    if executions is None:
        return ManualOrderWithFillsResponse(**order.model_dump(), filled_quantity=None, average_fill_price=None)
    # IBKR order IDs belong to a client ID. Orders by hand come from the Web client ID.
    order_executions = [
        execution
        for execution in executions
        if execution.order_id == record.ibkr_order_id
        and execution.client_id == web_client_id
        and execution.account == record.account
    ]
    filled_quantity = sum((execution.quantity for execution in order_executions), Decimal(0))
    average_fill_price = None
    if filled_quantity > 0:
        filled_amount = sum((execution.quantity * execution.price for execution in order_executions), Decimal(0))
        average_fill_price = filled_amount / filled_quantity
    return ManualOrderWithFillsResponse(
        **order.model_dump(), filled_quantity=filled_quantity, average_fill_price=average_fill_price
    )


async def read_executions_of_checked_account(paper_account_monitor: PaperAccountMonitor) -> list[Execution] | None:
    """None when the check did not pass or IB Gateway does not answer: then ATrade does not know the fills."""
    account_id = paper_account_monitor.read_checked_account_id()
    if account_id is None:
        return None
    try:
        executions = await paper_account_monitor.gateway_connection.read_executions()
    except GatewayRequestError:
        return None
    return [execution for execution in executions if execution.account == account_id]


def refuse_order(error: PaperAccountCheckError) -> JSONResponse:
    refused = OrderRefusedResponse(
        detail=error.check.message or "The paper account check did not pass.",
        actual_accounts=list(error.check.actual_accounts),
        expected_account=error.check.expected_account,
    )
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=refused.model_dump())


async def read_open_orders_of_checked_account(paper_account_monitor: PaperAccountMonitor) -> list[OpenOrderResponse]:
    """The open orders of the checked paper account. Empty when the check did not pass."""
    account_id = paper_account_monitor.read_checked_account_id()
    if account_id is None:
        return []
    gateway_connection = paper_account_monitor.gateway_connection
    web_client_id = paper_account_monitor.settings.ibkr_web_client_id
    open_orders = await gateway_connection.read_open_orders()
    return [to_open_order_response(order, web_client_id) for order in open_orders if order.account == account_id]


class PaperOrderRoutes:
    """The route functions. They share the paper account monitor, the database URL, and the clock."""

    def __init__(
        self,
        *,
        paper_account_monitor: PaperAccountMonitor,
        database_url: str,
        clock: Clock,
    ) -> None:
        self.paper_account_monitor = paper_account_monitor
        self.database_url = database_url
        self.clock = clock
        self.ledger = ManualOrderLedger(
            paper_account_monitor=paper_account_monitor, database_url=database_url, clock=clock
        )

    async def send_order(self, request: SendOrderRequest) -> ManualOrderResponse | JSONResponse:
        try:
            account_id = self.paper_account_monitor.require_checked_paper_account()
        except PaperAccountCheckError as error:
            return refuse_order(error)
        instrument = Instrument(symbol=request.symbol, exchange=request.exchange, currency=request.currency)
        order_by_hand = OrderByHand(
            instrument=instrument, side=request.side, quantity=request.quantity, limit_price=request.limit_price
        )
        try:
            refusal = await self.ledger.check_order(account_id, order_by_hand)
        except GatewayRequestError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        if refusal is not None:
            return refuse_by_ledger(refusal)
        order_request = OrderRequest(
            account=account_id,
            instrument=instrument,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price=request.limit_price,
            time_in_force=request.time_in_force,
            order_ref=MANUAL_ORDER_REF,
        )
        try:
            ibkr_order_id = await self.paper_account_monitor.gateway_connection.place_order(order_request)
        except GatewayRequestError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"IB Gateway refused the order: {error}") from error
        new_order = manual_order_store.NewManualOrder(
            created_at_utc=self.clock.read_now_utc(),
            account=account_id,
            symbol=request.symbol,
            exchange=request.exchange,
            currency=request.currency,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price=request.limit_price,
            time_in_force=request.time_in_force,
            ibkr_order_id=ibkr_order_id,
        )
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            record = await manual_order_store.insert_manual_order(connection, new_order)
            await connection.commit()
        return to_manual_order_response(record)

    async def list_open_orders(self) -> OpenOrderListResponse:
        try:
            orders = await read_open_orders_of_checked_account(self.paper_account_monitor)
        except GatewayRequestError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        return OpenOrderListResponse(orders=orders)

    async def list_manual_orders(self) -> ManualOrderListResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            records = await manual_order_store.select_manual_orders(connection)
        executions = await read_executions_of_checked_account(self.paper_account_monitor)
        web_client_id = self.paper_account_monitor.settings.ibkr_web_client_id
        return ManualOrderListResponse(
            manual_orders=[add_fills(record, executions, web_client_id) for record in records]
        )

    async def cancel_order(self, order_id: int) -> JSONResponse | None:
        try:
            account_id = self.paper_account_monitor.require_checked_paper_account()
        except PaperAccountCheckError as error:
            return refuse_order(error)
        gateway_connection = self.paper_account_monitor.gateway_connection
        try:
            open_orders = await gateway_connection.read_open_orders()
        except GatewayRequestError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        matching_orders = [order for order in open_orders if order.order_id == order_id and order.account == account_id]
        web_client_id = self.paper_account_monitor.settings.ibkr_web_client_id
        manual_orders = [order for order in matching_orders if is_cancellable_by_hand(order, web_client_id)]
        if not manual_orders:
            raise_not_cancellable(matching_orders)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            is_known = await manual_order_store.has_manual_order(connection, account=account_id, ibkr_order_id=order_id)
        if not is_known:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ATrade did not send this order by hand.")
        try:
            await gateway_connection.cancel_order(order_id)
        except GatewayRequestError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        return None


def refuse_by_ledger(refusal: OrderRefusal) -> JSONResponse:
    refused = OrderRefusedByLedgerResponse(detail=refusal.detail, rule=refusal.rule)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=refused.model_dump())


def raise_not_cancellable(matching_orders: list[OpenOrder]) -> None:
    if not matching_orders:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No open order of the paper account has this ID.")
    source = read_order_source(matching_orders[0].order_ref)
    if source.kind == "forward_test":
        message = f"This order belongs to forward test {source.forward_test_id}. Stop the forward test to cancel it."
    else:
        message = "Another IBKR client sent this order. Cancel it there."
    raise HTTPException(status.HTTP_409_CONFLICT, detail=message)
