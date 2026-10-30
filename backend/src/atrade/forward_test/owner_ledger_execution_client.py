"""`OwnerLedgerExecutionClient`: a NautilusTrader execution client that sends the orders of one forward test to IBKR
and keeps its fills in the owner ledger (docs/architecture/forward_test.md section 12.19, ADR 0007).

- The orders go through `ib_async` (`atrade.ibkr`) with the client ID of the forward test. The orderRef is the
  ClientOrderId, which holds `FT<ID>` (section 12.9).
- The owner ledger checks each order first. A failed rule gives `OrderDenied` with the reason, and no order.
- The client reads the executions of its own client ID every `fill_check_interval_seconds` (reqExecutions) and
  sends a fill for each new execution (execId) of an order that it sent in this run. It reads them once more at the
  stop. A failed save is tried again at the next read.
- Reconciliation reports the owner positions and the owner cash, not the account positions and the account cash.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, override

from nautilus_trader.common import Clock
from nautilus_trader.config import ExecutionClientConfig
from nautilus_trader.live import (
    CancelOrder,
    ClientCache,
    GenerateFillReports,
    GenerateOrderStatusReport,
    GenerateOrderStatusReports,
    GeneratePositionStatusReports,
    SubmitOrder,
)
from nautilus_trader.live.clients import ExecutionClient, ExecutionClientFactory
from nautilus_trader.model import (
    AccountBalance,
    AccountId,
    AccountType,
    ClientOrderId,
    Currency,
    FillReport,
    LiquiditySide,
    Money,
    OmsType,
    OrderSide,
    OrderStatus,
    OrderStatusReport,
    OrderType,
    PositionSide,
    PositionStatusReport,
    Quantity,
    TimeInForce,
    TradeId,
    TraderId,
    Venue,
    VenueOrderId,
)

from atrade.forward_test.atrade_instruments import PRICE_PRECISION, create_instrument_id, create_price
from atrade.forward_test.owner_ledger import OwnerFill, OwnerLedger, OwnerOrder
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import read_order_source
from atrade.ibkr import Execution, GatewayRequestError, OpenOrder, OrderRequest
from atrade.ibkr import OrderSide as IbkrOrderSide
from atrade.ibkr import OrderType as IbkrOrderType
from atrade.ibkr import TimeInForce as IbkrTimeInForce

OWNER_LEDGER_EXECUTION_CLIENT_NAME = "ATRADE_OWNER_LEDGER"
# The client handles the orders of all venues (primary exchanges) of the forward test.
EXECUTION_VENUE = Venue("ATRADE")
ACCOUNT_CURRENCY = "USD"
DEFAULT_FILL_CHECK_INTERVAL_SECONDS = 1.0
NANOSECONDS_PER_SECOND = 1_000_000_000
ORDER_TYPES: dict[OrderType, IbkrOrderType] = {OrderType.MARKET: "MKT", OrderType.LIMIT: "LMT"}
TIMES_IN_FORCE: dict[TimeInForce, IbkrTimeInForce] = {TimeInForce.DAY: "DAY", TimeInForce.GTC: "GTC"}
UNSUPPORTED_ORDER_REASON = "ATrade sends only market and limit orders with the time in force DAY or GTC."
UNKNOWN_INSTRUMENT_REASON = "The instrument is not an instrument of this forward test."

logger = logging.getLogger(__name__)


class OrderGateway(Protocol):
    """The functions of the `ibkr` GatewayConnection that the client uses. The connection has the client ID of the
    forward test."""

    async def connect(self) -> None: ...

    async def place_order(self, request: OrderRequest) -> int: ...

    async def cancel_order(self, order_id: int) -> None: ...

    async def read_own_open_orders(self) -> list[OpenOrder]: ...

    async def read_executions(self) -> list[Execution]: ...

    def disconnect(self) -> None: ...


@dataclass(frozen=True)
class OwnerLedgerInput:
    forward_test_id: int
    client_id: int
    # The IBKR paper account, for the orders.
    account_id: str
    instruments: tuple[Instrument, ...]
    fill_check_interval_seconds: float = DEFAULT_FILL_CHECK_INTERVAL_SECONDS


@dataclass
class SentOrder:
    order: object
    instrument: Instrument
    side: IbkrOrderSide
    order_ref: str
    # The execIds of the executions that are in the owner ledger.
    saved_execution_ids: set[str]


def create_quantity(value: Decimal) -> Quantity:
    return Quantity.from_str(str(int(value)))


class OwnerLedgerExecutionClient(ExecutionClient):
    def __init__(  # noqa: PLR0913 - the keywords of the NautilusTrader client
        self,
        *,
        name: str,
        config: ExecutionClientConfig,
        cache: ClientCache,
        clock: Clock,
        trader_id: TraderId,
        ledger_input: OwnerLedgerInput,
        ledger: OwnerLedger,
        gateway: OrderGateway,
    ) -> None:
        super().__init__(
            name=name,
            config=config,
            cache=cache,
            clock=clock,
            trader_id=trader_id,
            venue=EXECUTION_VENUE,
            # The account of the strategy is the owner, not the IBKR account (section 12.18).
            account_id=AccountId(f"ATRADE-FT{ledger_input.forward_test_id}"),
            account_type=AccountType.CASH,
            oms_type=OmsType.NETTING,
            base_currency=Currency.from_str(ACCOUNT_CURRENCY),
        )
        self.ledger_input = ledger_input
        self.ledger = ledger
        self.gateway = gateway
        self.instruments = {
            str(create_instrument_id(instrument)): instrument for instrument in ledger_input.instruments
        }
        # IBKR order ID -> the order that this client sent in this run.
        self.sent_orders: dict[int, SentOrder] = {}
        self.fill_check_task: asyncio.Task[None] | None = None

    @override
    async def _connect(self) -> None:
        await self.gateway.connect()
        cash = Money.from_str(
            f"{await self.ledger.read_cash_usd(self.ledger_input.forward_test_id)} {ACCOUNT_CURRENCY}"
        )
        no_cash = Money.from_str(f"0 {ACCOUNT_CURRENCY}")
        self.generate_account_state([AccountBalance(cash, no_cash, cash)], [], True, self.clock.timestamp_ns())
        self.fill_check_task = asyncio.get_running_loop().create_task(self.check_fills())

    @override
    async def _disconnect(self) -> None:
        if self.fill_check_task is not None:
            self.fill_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.fill_check_task
            # The last read: the fills since the last check go into the owner ledger before the stop.
            await self.read_new_fills()
        self.gateway.disconnect()

    @override
    def _handles_order_venue(self, venue: Venue | None) -> bool:
        return True

    async def check_fills(self) -> None:
        while True:
            await asyncio.sleep(self.ledger_input.fill_check_interval_seconds)
            await self.read_new_fills()

    async def read_new_fills(self) -> None:
        """A failed read or save does not stop the fill check. The next check tries the execution again."""
        try:
            await self.send_new_fills(await self.gateway.read_executions())
        except GatewayRequestError:
            return
        except Exception:
            logger.exception("Forward test %s could not save a fill", self.ledger_input.forward_test_id)

    async def send_new_fills(self, executions: list[Execution]) -> None:
        for execution in executions:
            sent_order = self.sent_orders.get(execution.order_id)
            # reqExecutions can return the executions of other client IDs. They are not fills of this forward test.
            if (
                execution.client_id != self.ledger_input.client_id
                or sent_order is None
                or execution.execution_id in sent_order.saved_execution_ids
            ):
                continue
            await self.send_fill(execution, sent_order)

    async def send_fill(self, execution: Execution, sent_order: SentOrder) -> None:
        await self.ledger.save_fill(
            OwnerFill(
                forward_test_id=self.ledger_input.forward_test_id,
                instrument=sent_order.instrument,
                side=sent_order.side,
                quantity=execution.quantity,
                price=execution.price,
                time_utc=execution.time_utc,
                order_ref=sent_order.order_ref,
            )
        )
        sent_order.saved_execution_ids.add(execution.execution_id)
        self.generate_order_filled(
            sent_order.order,
            VenueOrderId(str(execution.order_id)),
            None,
            TradeId(execution.execution_id),
            create_quantity(execution.quantity),
            create_price(execution.price),
            Currency.from_str(sent_order.instrument.currency),
            None,
            LiquiditySide.NO_LIQUIDITY_SIDE,
            int(execution.time_utc.timestamp() * NANOSECONDS_PER_SECOND),
        )

    @override
    async def _submit_order(self, command: SubmitOrder) -> None:
        order = command.order
        instrument = self.instruments.get(str(command.instrument_id))
        order_type = ORDER_TYPES.get(order.order_type)
        time_in_force = TIMES_IN_FORCE.get(order.time_in_force)
        if instrument is None:
            self.generate_order_denied(order, UNKNOWN_INSTRUMENT_REASON)
            return
        if order_type is None or time_in_force is None:
            self.generate_order_denied(order, UNSUPPORTED_ORDER_REASON)
            return
        side: IbkrOrderSide = "BUY" if order.side == OrderSide.BUY else "SELL"
        quantity = Decimal(str(order.quantity))
        limit_price = Decimal(str(order.price)) if order_type == "LMT" else None
        reason = await self.ledger.check_order(
            OwnerOrder(self.ledger_input.forward_test_id, instrument, side, quantity, limit_price)
        )
        if reason is not None:
            self.generate_order_denied(order, reason)
            return
        self.generate_order_submitted(order)
        order_ref = str(command.client_order_id)
        request = OrderRequest(
            account=self.ledger_input.account_id,
            instrument=instrument,
            side=side,
            quantity=int(quantity),
            order_type=order_type,
            limit_price=limit_price,
            time_in_force=time_in_force,
            order_ref=order_ref,
        )
        try:
            order_id = await self.gateway.place_order(request)
        except GatewayRequestError as error:
            self.generate_order_rejected(order, str(error), self.clock.timestamp_ns(), False)
            return
        self.sent_orders[order_id] = SentOrder(order, instrument, side, order_ref, set())
        self.generate_order_accepted(order, VenueOrderId(str(order_id)), self.clock.timestamp_ns())

    @override
    async def _cancel_order(self, command: CancelOrder) -> None:
        order = self.cache.order(command.client_order_id)
        venue_order_id = command.venue_order_id
        if order is None or venue_order_id is None:
            return
        try:
            await self.gateway.cancel_order(int(str(venue_order_id)))
        except GatewayRequestError as error:
            self.generate_order_cancel_rejected(order, venue_order_id, str(error), self.clock.timestamp_ns())
            return
        # The entry in sent_orders stays: a fill before the cancel can come with the next fill check.
        self.generate_order_canceled(order, venue_order_id, self.clock.timestamp_ns())

    def is_own_order(self, open_order: OpenOrder) -> bool:
        source = read_order_source(open_order.order_ref)
        return (
            open_order.client_id == self.ledger_input.client_id
            and source.forward_test_id == self.ledger_input.forward_test_id
            and open_order.order_type in ORDER_TYPES.values()
        )

    def create_order_status_report(self, open_order: OpenOrder) -> OrderStatusReport:
        now = self.clock.timestamp_ns()
        is_limit = open_order.order_type == "LMT"
        return OrderStatusReport(
            self.account_id,
            create_instrument_id(open_order.instrument),
            VenueOrderId(str(open_order.order_id)),
            OrderSide.BUY if open_order.side == "BUY" else OrderSide.SELL,
            OrderType.LIMIT if is_limit else OrderType.MARKET,
            TimeInForce.DAY if open_order.time_in_force == "DAY" else TimeInForce.GTC,
            OrderStatus.PARTIALLY_FILLED if open_order.filled_quantity > 0 else OrderStatus.ACCEPTED,
            create_quantity(open_order.quantity),
            create_quantity(open_order.filled_quantity),
            now,
            now,
            now,
            client_order_id=ClientOrderId(open_order.order_ref),
            price=create_price(open_order.limit_price) if is_limit and open_order.limit_price is not None else None,
        )

    @override
    async def _generate_order_status_report(self, command: GenerateOrderStatusReport) -> OrderStatusReport | None:
        reports = await self._generate_order_status_reports_of_own_orders()
        return next(
            (
                report
                for report in reports
                if report.client_order_id == command.client_order_id or report.venue_order_id == command.venue_order_id
            ),
            None,
        )

    async def _generate_order_status_reports_of_own_orders(self) -> list[OrderStatusReport]:
        """Only the open orders of this client ID and this forward test. The restart cancels them before the
        LiveNode starts (section 12.7), so the list is usually empty."""
        open_orders = await self.gateway.read_own_open_orders()
        return [self.create_order_status_report(order) for order in open_orders if self.is_own_order(order)]

    @override
    async def _generate_order_status_reports(self, command: GenerateOrderStatusReports) -> list[OrderStatusReport]:
        reports = await self._generate_order_status_reports_of_own_orders()
        return [report for report in reports if command.instrument_id in {None, report.instrument_id}]

    @override
    async def _generate_fill_reports(self, command: GenerateFillReports) -> list[FillReport]:
        """No fill reports. The owner ledger holds the fills, and the position reports give the owner positions."""
        return []

    @override
    async def _generate_position_status_reports(
        self, command: GeneratePositionStatusReports
    ) -> list[PositionStatusReport]:
        now = self.clock.timestamp_ns()
        positions = await self.ledger.read_positions(self.ledger_input.forward_test_id)
        reports = [
            PositionStatusReport(
                self.account_id,
                create_instrument_id(position.instrument),
                PositionSide.LONG,
                create_quantity(position.quantity),
                now,
                now,
                avg_px_open=round(position.average_price, PRICE_PRECISION),
            )
            for position in positions
        ]
        return [report for report in reports if command.instrument_id in {None, report.instrument_id}]


class OwnerLedgerExecutionClientFactory(ExecutionClientFactory):
    def __init__(self, ledger_input: OwnerLedgerInput, ledger: OwnerLedger, gateway: OrderGateway) -> None:
        self.ledger_input = ledger_input
        self.ledger = ledger
        self.gateway = gateway

    def create(  # pyright: ignore[reportIncompatibleMethodOverride] - an instance factory (python_adapters.md)
        self, *, name: str, config: ExecutionClientConfig, cache: ClientCache, clock: Clock, trader_id: TraderId
    ) -> OwnerLedgerExecutionClient:
        return OwnerLedgerExecutionClient(
            name=name,
            config=config,
            cache=cache,
            clock=clock,
            trader_id=trader_id,
            ledger_input=self.ledger_input,
            ledger=self.ledger,
            gateway=self.gateway,
        )
