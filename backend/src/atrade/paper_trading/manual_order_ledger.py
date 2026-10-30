"""The owner ledger of "By hand" in the Web process: the ledger start, the fills of orders by hand, and the 3 order rules
(docs/architecture/paper_trading.md sections 11.10 and 11.13).

- The ledger starts at the first passed paper account check with a USD cash value: the positions of the account and
  its cash go to "By hand" as `ledger_start` rows.
- The Web process records the fills of its orders by hand from reqExecutions before each order by hand and each second
  while /ws/paper-trading is open. A fill before the ledger start is already in the start positions.
- Rule 2 uses the limit price, or the last daily close for a market order, without the commission. Amounts of other
  currencies are converted to USD with the IBKR forex rate.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Literal

import psycopg

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import read_order_source
from atrade.ibkr import Execution, GatewayRequestError, OpenOrder, OrderSide
from atrade.paper_trading import manual_order_store, owner_ledger_store
from atrade.paper_trading.owner_ledger_store import BY_HAND, LedgerEntry, OwnerPosition
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor

USD = "USD"
BY_HAND_LABEL = "By hand"
# The last daily close of the last days is the price of a market buy order for rule 2.
LAST_CLOSE_DAYS = 10
CENT = Decimal("0.01")
BOUGHT_SIDE = "BOT"

type LedgerRule = Literal["sell_more_than_position", "buy_more_than_cash", "ledger_not_started"]


@dataclass(frozen=True)
class OrderRefusal:
    rule: LedgerRule
    detail: str


@dataclass(frozen=True)
class OrderByHand:
    instrument: Instrument
    side: OrderSide
    quantity: int
    limit_price: Decimal | None


def format_quantity(quantity: Decimal) -> str:
    return f"{quantity.normalize():f}"


def format_usd(amount: Decimal) -> str:
    return f"{amount.quantize(CENT):f} USD"


def is_open_order_by_hand(order: OpenOrder, account: str, side: OrderSide) -> bool:
    return order.account == account and order.side == side and read_order_source(order.order_ref).kind == "by_hand"


class ManualOrderLedger:
    def __init__(self, *, paper_account_monitor: PaperAccountMonitor, database_url: str, clock: Clock) -> None:
        self.paper_account_monitor = paper_account_monitor
        self.database_url = database_url
        self.clock = clock

    async def read_entries(self, account: str) -> list[LedgerEntry] | None:
        """The ledger of the account. Starts it first when needed. None when the ledger has no start and the balance
        has no USD cash value yet."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            entries = await owner_ledger_store.select_entries(connection, account=account)
            if entries:
                return entries
            balance = await self.paper_account_monitor.read_balance()
            if balance is None or balance.cash_usd is None:
                return None
            await owner_ledger_store.start_ledger(
                connection,
                account=account,
                positions=self.paper_account_monitor.read_positions(),
                cash_usd=balance.cash_usd,
                time_utc=self.clock.read_now_utc(),
            )
            await connection.commit()
            return await owner_ledger_store.select_entries(connection, account=account)

    async def record_fills(self, account: str) -> None:
        """Writes the fills of the orders by hand of this Web client ID. IBKR errors leave them for the next time."""
        entries = await self.read_entries(account)
        if entries is None:
            return
        start_utc = owner_ledger_store.find_ledger_start_utc(entries)
        try:
            executions = await self.paper_account_monitor.gateway_connection.read_executions()
        except GatewayRequestError:
            return
        web_client_id = self.paper_account_monitor.settings.ibkr_web_client_id
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            orders = {
                order.ibkr_order_id: order
                for order in await manual_order_store.select_manual_orders(connection)
                if order.account == account
            }
            for execution in executions:
                order = orders.get(execution.order_id)
                if (
                    order is None
                    or execution.account != account
                    or execution.client_id != web_client_id
                    or (start_utc is not None and execution.time_utc < start_utc)
                ):
                    continue
                instrument = Instrument(symbol=order.symbol, exchange=order.exchange, currency=order.currency)
                fill = await self.build_fill(account, instrument, execution)
                if fill is not None:
                    await owner_ledger_store.insert_fill(connection, fill)
            await connection.commit()

    async def build_fill(
        self, account: str, instrument: Instrument, execution: Execution
    ) -> owner_ledger_store.NewFill | None:
        quantity_change = execution.quantity if execution.side == BOUGHT_SIDE else -execution.quantity
        try:
            cash_change_usd = await self.convert_to_usd(
                -quantity_change * execution.price - execution.commission, instrument.currency
            )
        except GatewayRequestError:
            return None
        return owner_ledger_store.NewFill(
            owner=BY_HAND,
            time_utc=execution.time_utc,
            account=account,
            instrument=instrument,
            quantity_change=quantity_change,
            price=execution.price,
            commission=execution.commission,
            cash_change_usd=cash_change_usd,
            ibkr_execution_id=execution.execution_id,
            ibkr_order_id=execution.order_id,
        )

    async def check_order(self, account: str, order: OrderByHand) -> OrderRefusal | None:
        """The 3 order rules of "By hand" (section 11.10). Rule 1 also keeps "By hand" from selling short (rule 3).

        Raises GatewayRequestError when IBKR does not answer.
        """
        await self.record_fills(account)
        entries = await self.read_entries(account)
        if entries is None:
            return OrderRefusal(
                rule="ledger_not_started",
                detail="The owner ledger has no start: the paper account has no cash value in USD yet.",
            )
        open_orders = await self.paper_account_monitor.gateway_connection.read_open_orders()
        if order.side == "SELL":
            return check_sell(entries, open_orders, account, order)
        return await self.check_buy(entries, open_orders, account, order)

    async def check_buy(
        self, entries: list[LedgerEntry], open_orders: list[OpenOrder], account: str, order: OrderByHand
    ) -> OrderRefusal | None:
        cash = owner_ledger_store.sum_owner_cash_usd(entries, BY_HAND)
        open_buy_amount = Decimal(0)
        for open_order in open_orders:
            if is_open_order_by_hand(open_order, account, "BUY"):
                open_buy_amount += await self.find_amount_usd(
                    open_order.instrument, open_order.quantity - open_order.filled_quantity, open_order.limit_price
                )
        amount = await self.find_amount_usd(order.instrument, Decimal(order.quantity), order.limit_price)
        if amount <= cash - open_buy_amount:
            return None
        return OrderRefusal(
            rule="buy_more_than_cash",
            detail=(
                f"{BY_HAND_LABEL} has {format_usd(cash)} cash and open buy orders for {format_usd(open_buy_amount)}. "
                f"ATrade refuses a buy order for {format_usd(amount)}."
            ),
        )

    async def find_amount_usd(self, instrument: Instrument, quantity: Decimal, limit_price: Decimal | None) -> Decimal:
        price = limit_price if limit_price is not None else await self.read_last_close(instrument)
        return await self.convert_to_usd(quantity * price, instrument.currency)

    async def read_last_close(self, instrument: Instrument) -> Decimal:
        now_utc = self.clock.read_now_utc()
        bars = await self.paper_account_monitor.gateway_connection.read_historical_bars(
            instrument,
            BarPeriod.ONE_DAY,
            TimeRange(start_utc=now_utc - timedelta(days=LAST_CLOSE_DAYS), end_utc=now_utc),
        )
        if not bars:
            message = f"IBKR sent no daily bar of {instrument.symbol} for the amount of the market order."
            raise GatewayRequestError(message)
        return bars[-1].close

    async def convert_to_usd(self, amount: Decimal, currency: str) -> Decimal:
        if currency == USD:
            return amount
        rate = await self.paper_account_monitor.gateway_connection.read_exchange_rate(currency, USD)
        return amount * rate


def check_sell(
    entries: list[LedgerEntry], open_orders: list[OpenOrder], account: str, order: OrderByHand
) -> OrderRefusal | None:
    position = sum(
        (
            owner_position.quantity
            for owner_position in owner_ledger_store.sum_owner_positions(entries)
            if owner_position.owner == BY_HAND and owner_position.instrument == order.instrument
        ),
        Decimal(0),
    )
    open_sell_quantity = sum(
        (
            open_order.quantity - open_order.filled_quantity
            for open_order in open_orders
            if is_open_order_by_hand(open_order, account, "SELL") and open_order.instrument == order.instrument
        ),
        Decimal(0),
    )
    if order.quantity <= position - open_sell_quantity:
        return None
    return OrderRefusal(
        rule="sell_more_than_position",
        detail=(
            f"{BY_HAND_LABEL} holds {format_quantity(position)} {order.instrument.symbol} and has open sell orders for "
            f"{format_quantity(open_sell_quantity)}. ATrade refuses a sell order for {order.quantity}."
        ),
    )


def find_owner_positions(entries: list[LedgerEntry], instrument: Instrument) -> list[OwnerPosition]:
    return [
        owner_position
        for owner_position in owner_ledger_store.sum_owner_positions(entries)
        if owner_position.instrument == instrument
    ]
