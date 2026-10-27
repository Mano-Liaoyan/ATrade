"""Order data that the Web process sends to and reads from IB Gateway: an order request and an open order.

The `ibkr` module converts between these types and the ib_async types. It adds no business rules. The paper
account check is the job of `paper_trading` (docs/architecture/paper_trading.md section 11.2).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from ib_async import Contract, LimitOrder, MarketOrder, Order, Stock, Trade

from atrade.foundation.instrument import Instrument

# ATrade sends stock orders to IBKR smart routing. The primary exchange identifies the stock.
SMART_ROUTING_EXCHANGE = "SMART"
# ib_async uses the largest float for a price that is not set.
UNSET_PRICE_LIMIT = 1e300

type OrderSide = Literal["BUY", "SELL"]
type OrderType = Literal["MKT", "LMT"]
type TimeInForce = Literal["DAY", "GTC"]


@dataclass(frozen=True)
class OrderRequest:
    account: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    order_type: OrderType
    # Only for a limit order. None for a market order.
    limit_price: Decimal | None
    time_in_force: TimeInForce
    order_ref: str


@dataclass(frozen=True)
class OpenOrder:
    """One open order of the account from reqAllOpenOrders. It can come from any client ID, also a forward test."""

    order_id: int
    client_id: int
    perm_id: int
    account: str
    instrument: Instrument
    # Text from IBKR. Orders of other clients can have other values, for example "STP".
    side: str
    quantity: Decimal
    order_type: str
    limit_price: Decimal | None
    time_in_force: str
    status: str
    filled_quantity: Decimal
    order_ref: str


def build_contract(instrument: Instrument) -> Contract:
    return Stock(
        symbol=instrument.symbol,
        exchange=SMART_ROUTING_EXCHANGE,
        currency=instrument.currency,
        primaryExchange=instrument.exchange,
    )


def build_order(request: OrderRequest) -> Order:
    if request.order_type == "LMT":
        if request.limit_price is None:
            message = "A limit order needs a limit price."
            raise ValueError(message)
        return LimitOrder(
            request.side,
            request.quantity,
            float(request.limit_price),
            tif=request.time_in_force,
            account=request.account,
            orderRef=request.order_ref,
        )
    return MarketOrder(
        request.side, request.quantity, tif=request.time_in_force, account=request.account, orderRef=request.order_ref
    )


def read_price(price: float | Decimal | None) -> Decimal | None:
    if price is None or abs(float(price)) >= UNSET_PRICE_LIMIT:
        return None
    # str() first, so that the Decimal has the short form of the float, for example 1.1 and not 1.0999...
    return Decimal(str(price))


def convert_trade(trade: Trade) -> OpenOrder:
    contract = trade.contract
    order = trade.order
    return OpenOrder(
        order_id=order.orderId,
        client_id=order.clientId,
        perm_id=order.permId,
        account=order.account,
        instrument=Instrument(
            symbol=contract.localSymbol or contract.symbol,
            exchange=contract.primaryExchange or contract.exchange,
            currency=contract.currency,
        ),
        side=order.action,
        quantity=Decimal(str(order.totalQuantity)),
        order_type=order.orderType,
        limit_price=read_price(order.lmtPrice),
        time_in_force=order.tif,
        status=trade.orderStatus.status,
        filled_quantity=Decimal(str(trade.orderStatus.filled)),
        order_ref=order.orderRef,
    )
