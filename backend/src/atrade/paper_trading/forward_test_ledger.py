"""The owner ledger of the forward tests (docs/architecture/paper_trading.md sections 11.10 and 11.13).

- The Web process writes the allocated capital of a new forward test as a `transfer` from "By hand" to the forward
  test (`write_capital_allocation`). So the cash of "By hand" is its ledger cash minus the allocated capital of the
  forward tests, and the cash of a forward test starts at its allocated capital.
- The ATrade execution client of the forward test child uses `ForwardTestLedger`: the 3 order rules, the fills, and
  the owner positions and cash for reconciliation (forward_test.md section 12.19).
- The worker transfers the positions and the cash of a stopped forward test to "By hand" (`transfer_to_by_hand`).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import psycopg

from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import read_order_source
from atrade.ibkr import GatewayConnection, OrderSide
from atrade.paper_trading import owner_ledger_store
from atrade.paper_trading.manual_order_ledger import (
    LedgerOrder,
    OrderAmounts,
    check_owner_order,
    find_split_check_refusal,
)
from atrade.paper_trading.owner_ledger_store import BY_HAND, LedgerEntry, LedgerFill, Owner


def create_forward_test_owner(forward_test_id: int) -> Owner:
    return Owner(kind="forward_test", forward_test_id=forward_test_id)


@dataclass(frozen=True)
class OwnerOrder:
    """An order that a forward test wants to send. The ledger checks it with the order rules of section 11.10."""

    forward_test_id: int
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    # None for a market order.
    limit_price: Decimal | None


@dataclass(frozen=True)
class OwnerFill:
    forward_test_id: int
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    price: Decimal
    time_utc: datetime
    # The IBKR orderRef of the order: the NautilusTrader ClientOrderId, which holds `FT<ID>` (section 12.9).
    order_ref: str
    # The IBKR execId. The ledger stores each execution once.
    execution_id: str
    ibkr_order_id: int
    # In the currency of the instrument.
    commission: Decimal


@dataclass(frozen=True)
class OwnerPosition:
    instrument: Instrument
    quantity: Decimal
    average_price: Decimal


async def write_capital_allocation(
    connection: psycopg.AsyncConnection,
    *,
    account: str,
    forward_test_id: int,
    allocated_capital_usd: Decimal,
    time_utc: datetime,
) -> None:
    """Moves the allocated capital from the cash of "By hand" to the forward test. The caller commits."""
    await owner_ledger_store.insert_cash_transfer(
        connection,
        account=account,
        source=BY_HAND,
        target=create_forward_test_owner(forward_test_id),
        cash_usd=allocated_capital_usd,
        time_utc=time_utc,
    )


async def transfer_to_by_hand(connection: psycopg.AsyncConnection, *, forward_test_id: int, time_utc: datetime) -> None:
    """Moves the positions and the remaining cash of a stopped forward test to "By hand" (section 11.10).

    The fills of the forward test stay. A second call moves nothing, because the forward test then holds nothing.
    The caller commits.
    """
    owner = create_forward_test_owner(forward_test_id)
    account = await owner_ledger_store.select_owner_account(connection, owner)
    if account is None:
        return
    entries = await owner_ledger_store.select_entries(connection, account=account)
    for position in owner_ledger_store.sum_owner_positions(entries):
        if position.owner == owner:
            await owner_ledger_store.insert_position_transfer(
                connection, account=account, source=owner, target=BY_HAND, position=position, time_utc=time_utc
            )
    cash_usd = owner_ledger_store.sum_owner_cash_usd(entries, owner)
    if cash_usd != 0:
        await owner_ledger_store.insert_cash_transfer(
            connection, account=account, source=owner, target=BY_HAND, cash_usd=cash_usd, time_utc=time_utc
        )


async def read_forward_test_fills(connection: psycopg.AsyncConnection, forward_test_id: int) -> list[LedgerFill]:
    """The fills of the forward test in the owner ledger, oldest first (forward_test.md section 12.8)."""
    return await owner_ledger_store.select_owner_fills(connection, create_forward_test_owner(forward_test_id))


def read_forward_test_fills_blocking(connection: psycopg.Connection, forward_test_id: int) -> list[LedgerFill]:
    """`read_forward_test_fills` for the synchronous connection of the recorder DataActor."""
    return owner_ledger_store.select_owner_fills_blocking(connection, create_forward_test_owner(forward_test_id))


class ForwardTestLedger:
    """The `OwnerLedger` of `forward_test` (section 12.19) for one forward test on one paper account.

    `gateway_connection` has the client ID of the forward test. Its open orders are the open orders of the owner.
    """

    def __init__(
        self,
        *,
        database_url: str,
        account: str,
        forward_test_id: int,
        gateway_connection: GatewayConnection,
        clock: Clock,
    ) -> None:
        self.database_url = database_url
        self.account = account
        self.owner = create_forward_test_owner(forward_test_id)
        self.gateway_connection = gateway_connection
        self.amounts = OrderAmounts(gateway_connection=gateway_connection, clock=clock)

    async def read_entries(self) -> list[LedgerEntry]:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            return await owner_ledger_store.select_entries(connection, account=self.account)

    async def check_order(self, order: OwnerOrder) -> str | None:
        """Returns the reason when a rule fails. An IBKR error also refuses the order: the rules need IBKR."""
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                split_check_refusal = await find_split_check_refusal(connection, self.account, order.instrument)
            if split_check_refusal is not None:
                return split_check_refusal.detail
            open_orders = [
                open_order
                for open_order in await self.gateway_connection.read_own_open_orders()
                if read_order_source(open_order.order_ref).forward_test_id == order.forward_test_id
            ]
            refusal = await check_owner_order(
                self.amounts,
                await self.read_entries(),
                open_orders,
                LedgerOrder(
                    owner=self.owner,
                    owner_label=f"Forward test {order.forward_test_id}",
                    instrument=order.instrument,
                    side=order.side,
                    quantity=order.quantity,
                    limit_price=order.limit_price,
                ),
            )
        except Exception as error:  # noqa: BLE001 - every failed check refuses the order, with the reason.
            return f"The owner ledger could not check the order: {error}"
        return None if refusal is None else refusal.detail

    async def save_fill(self, fill: OwnerFill) -> None:
        """A fill that ATrade reads again adds no row. Raises GatewayRequestError without a forex rate."""
        quantity_change = fill.quantity if fill.side == "BUY" else -fill.quantity
        cash_change_usd = await self.amounts.convert_to_usd(
            -quantity_change * fill.price - fill.commission, fill.instrument.currency
        )
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            await owner_ledger_store.insert_fill(
                connection,
                owner_ledger_store.NewFill(
                    owner=self.owner,
                    time_utc=fill.time_utc,
                    account=self.account,
                    instrument=fill.instrument,
                    quantity_change=quantity_change,
                    price=fill.price,
                    commission=fill.commission,
                    cash_change_usd=cash_change_usd,
                    ibkr_execution_id=fill.execution_id,
                    ibkr_order_id=fill.ibkr_order_id,
                ),
            )
            await connection.commit()

    async def read_positions(self, forward_test_id: int) -> list[OwnerPosition]:
        owner = create_forward_test_owner(forward_test_id)
        return [
            OwnerPosition(
                instrument=position.instrument,
                quantity=position.quantity,
                average_price=position.average_cost or Decimal(0),
            )
            for position in owner_ledger_store.sum_owner_positions(await self.read_entries())
            if position.owner == owner
        ]

    async def read_cash_usd(self, forward_test_id: int) -> Decimal:
        return owner_ledger_store.sum_owner_cash_usd(
            await self.read_entries(), create_forward_test_owner(forward_test_id)
        )
