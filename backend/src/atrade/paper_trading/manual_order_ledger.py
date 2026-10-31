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
from atrade.ibkr import Execution, GatewayConnection, GatewayRequestError, OpenOrder, OrderSide
from atrade.paper_trading import manual_order_store, owner_ledger_store, split_check_store
from atrade.paper_trading.owner_ledger_store import BY_HAND, LedgerEntry, Owner, OwnerPosition
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor

USD = "USD"
BY_HAND_LABEL = "By hand"
# The last daily close of the last days is the price of a market buy order for rule 2.
LAST_CLOSE_DAYS = 10
CENT = Decimal("0.01")
BOUGHT_SIDE = "BOT"

type LedgerRule = Literal["sell_more_than_position", "buy_more_than_cash", "ledger_not_started", "split_check_needed"]


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


async def find_split_check_refusal(
    connection: psycopg.AsyncConnection, account: str, instrument: Instrument
) -> OrderRefusal | None:
    """No owner can send an order on an instrument in the "Split check needed" state (section 11.11)."""
    split_checks = await split_check_store.select_split_checks(connection, account=account, status="needed")
    if not any(split_check.instrument == instrument for split_check in split_checks):
        return None
    return OrderRefusal(
        rule="split_check_needed",
        detail=(
            f"{instrument.symbol} needs a split check. Apply the split or keep the ledger on the paper trading page."
        ),
    )


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
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            split_check_refusal = await find_split_check_refusal(connection, account, order.instrument)
        if split_check_refusal is not None:
            return split_check_refusal
        open_orders = [
            open_order
            for open_order in await self.paper_account_monitor.gateway_connection.read_open_orders()
            if open_order.account == account and read_order_source(open_order.order_ref).kind == "by_hand"
        ]
        owner_order = LedgerOrder(
            owner=BY_HAND,
            owner_label=BY_HAND_LABEL,
            instrument=order.instrument,
            side=order.side,
            quantity=Decimal(order.quantity),
            limit_price=order.limit_price,
        )
        amounts = OrderAmounts(gateway_connection=self.paper_account_monitor.gateway_connection, clock=self.clock)
        return await check_owner_order(amounts, entries, open_orders, owner_order)

    async def convert_to_usd(self, amount: Decimal, currency: str) -> Decimal:
        amounts = OrderAmounts(gateway_connection=self.paper_account_monitor.gateway_connection, clock=self.clock)
        return await amounts.convert_to_usd(amount, currency)


@dataclass(frozen=True)
class LedgerOrder:
    """An order of one owner for the order rules (section 11.10)."""

    owner: Owner
    # "By hand", or "Forward test 3", for the reason of a refusal.
    owner_label: str
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    # None for a market order.
    limit_price: Decimal | None


class OrderAmounts:
    """The USD amount of a buy order for rule 2 (section 11.13): the limit price, or the last daily close for a market
    order, without the commission. Other currencies use the IBKR forex rate."""

    def __init__(self, *, gateway_connection: GatewayConnection, clock: Clock) -> None:
        self.gateway_connection = gateway_connection
        self.clock = clock

    async def find_amount_usd(self, instrument: Instrument, quantity: Decimal, limit_price: Decimal | None) -> Decimal:
        price = limit_price if limit_price is not None else await self.read_last_close(instrument)
        return await self.convert_to_usd(quantity * price, instrument.currency)

    async def read_last_close(self, instrument: Instrument) -> Decimal:
        now_utc = self.clock.read_now_utc()
        bars = await self.gateway_connection.read_historical_bars(
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
        rate = await self.gateway_connection.read_exchange_rate(currency, USD)
        return amount * rate


async def check_owner_order(
    amounts: OrderAmounts, entries: list[LedgerEntry], owner_open_orders: list[OpenOrder], order: LedgerOrder
) -> OrderRefusal | None:
    """The 3 order rules for one owner. `owner_open_orders` are the open orders of this owner only.

    Raises GatewayRequestError when IBKR does not answer.
    """
    if order.side == "SELL":
        return check_sell(entries, owner_open_orders, order)
    return await check_buy(amounts, entries, owner_open_orders, order)


async def check_buy(
    amounts: OrderAmounts, entries: list[LedgerEntry], owner_open_orders: list[OpenOrder], order: LedgerOrder
) -> OrderRefusal | None:
    cash = owner_ledger_store.sum_owner_cash_usd(entries, order.owner)
    open_buy_amount = Decimal(0)
    for open_order in owner_open_orders:
        if open_order.side == "BUY":
            open_buy_amount += await amounts.find_amount_usd(
                open_order.instrument, open_order.quantity - open_order.filled_quantity, open_order.limit_price
            )
    amount = await amounts.find_amount_usd(order.instrument, order.quantity, order.limit_price)
    if amount <= cash - open_buy_amount:
        return None
    return OrderRefusal(
        rule="buy_more_than_cash",
        detail=(
            f"{order.owner_label} has {format_usd(cash)} cash and open buy orders for {format_usd(open_buy_amount)}. "
            f"ATrade refuses a buy order for {format_usd(amount)}."
        ),
    )


def check_sell(
    entries: list[LedgerEntry], owner_open_orders: list[OpenOrder], order: LedgerOrder
) -> OrderRefusal | None:
    position = sum(
        (
            owner_position.quantity
            for owner_position in owner_ledger_store.sum_owner_positions(entries)
            if owner_position.owner == order.owner and owner_position.instrument == order.instrument
        ),
        Decimal(0),
    )
    open_sell_quantity = sum(
        (
            open_order.quantity - open_order.filled_quantity
            for open_order in owner_open_orders
            if open_order.side == "SELL" and open_order.instrument == order.instrument
        ),
        Decimal(0),
    )
    if order.quantity <= position - open_sell_quantity:
        return None
    return OrderRefusal(
        rule="sell_more_than_position",
        detail=(
            f"{order.owner_label} holds {format_quantity(position)} {order.instrument.symbol} and has open sell orders "
            f"for {format_quantity(open_sell_quantity)}. ATrade refuses a sell order for "
            f"{format_quantity(order.quantity)}."
        ),
    )


def find_owner_positions(entries: list[LedgerEntry], instrument: Instrument) -> list[OwnerPosition]:
    return [
        owner_position
        for owner_position in owner_ledger_store.sum_owner_positions(entries)
        if owner_position.instrument == instrument
    ]
