"""SQL for the owner_ledger_entry table (docs/architecture/paper_trading.md section 11.10), and the sums of the ledger.

Only paper_trading reads or writes the table. `cash_change` is USD. The position of an owner is the sum of
`quantity_change`. The average cost follows from the entries with a price, oldest first.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg
from psycopg.rows import class_row

from atrade.foundation.instrument import Instrument
from atrade.ibkr import PortfolioPosition

type OwnerKind = Literal["by_hand", "forward_test"]
type EntryKind = Literal["fill", "split_adjustment", "transfer", "ledger_start"]

LEDGER_CASH_CURRENCY = "USD"


@dataclass(frozen=True)
class Owner:
    kind: OwnerKind
    # None for "By hand".
    forward_test_id: int | None


BY_HAND = Owner(kind="by_hand", forward_test_id=None)


@dataclass(frozen=True)
class LedgerEntry:
    owner_kind: OwnerKind
    forward_test_id: int | None
    entry_kind: EntryKind
    time_utc: datetime
    # None for a cash row.
    symbol: str | None
    exchange: str | None
    currency: str
    quantity_change: Decimal
    price: Decimal | None
    cash_change: Decimal

    @property
    def owner(self) -> Owner:
        return Owner(kind=self.owner_kind, forward_test_id=self.forward_test_id)

    def is_for(self, instrument: Instrument) -> bool:
        return (self.symbol, self.exchange, self.currency) == (
            instrument.symbol,
            instrument.exchange,
            instrument.currency,
        )


@dataclass(frozen=True)
class NewFill:
    """One fill of an order by hand. `cash_change_usd` is the signed cash of the fill in USD, with the commission."""

    owner: Owner
    time_utc: datetime
    account: str
    instrument: Instrument
    quantity_change: Decimal
    price: Decimal
    commission: Decimal
    cash_change_usd: Decimal
    ibkr_execution_id: str
    ibkr_order_id: int


@dataclass(frozen=True)
class OwnerPosition:
    owner: Owner
    instrument: Instrument
    quantity: Decimal
    # None when the owner holds no shares.
    average_cost: Decimal | None


ENTRY_COLUMNS = """
    owner_kind, forward_test_id, entry_kind, time_utc, symbol, exchange, currency, quantity_change, price, cash_change
"""


async def select_entries(connection: psycopg.AsyncConnection, *, account: str) -> list[LedgerEntry]:
    async with connection.cursor(row_factory=class_row(LedgerEntry)) as cursor:
        await cursor.execute(
            f"SELECT {ENTRY_COLUMNS} FROM owner_ledger_entry WHERE account = %(account)s ORDER BY id",
            {"account": account},
        )
        return await cursor.fetchall()


async def start_ledger(
    connection: psycopg.AsyncConnection,
    *,
    account: str,
    positions: list[PortfolioPosition],
    cash_usd: Decimal,
    time_utc: datetime,
) -> None:
    """Writes the positions and the cash of the account as `ledger_start` rows of "By hand", once per account.

    The caller commits. An advisory lock keeps 2 Web requests from writing the start twice.
    """
    await connection.execute(
        "SELECT pg_advisory_xact_lock(hashtext('owner_ledger_entry:' || %(account)s))", {"account": account}
    )
    cursor = await connection.execute(
        "SELECT 1 FROM owner_ledger_entry WHERE account = %(account)s LIMIT 1", {"account": account}
    )
    if await cursor.fetchone() is not None:
        return
    rows: list[tuple[str | None, str | None, str, Decimal, Decimal | None, Decimal]] = [
        (position.symbol, position.exchange, position.currency, position.quantity, position.average_cost, Decimal(0))
        for position in positions
        if position.quantity != 0
    ]
    rows.append((None, None, LEDGER_CASH_CURRENCY, Decimal(0), None, cash_usd))
    async with connection.cursor() as insert_cursor:
        await insert_cursor.executemany(
            """
            INSERT INTO owner_ledger_entry (
                owner_kind, entry_kind, time_utc, account, symbol, exchange, currency, quantity_change, price,
                cash_change
            ) VALUES ('by_hand', 'ledger_start', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [(time_utc, account, *row) for row in rows],
        )


async def insert_fill(connection: psycopg.AsyncConnection, fill: NewFill) -> None:
    """A fill that ATrade reads again adds no row (ON CONFLICT DO NOTHING on the IBKR execution ID)."""
    await connection.execute(
        """
        INSERT INTO owner_ledger_entry (
            owner_kind, forward_test_id, entry_kind, time_utc, account, symbol, exchange, currency, quantity_change,
            price, commission, cash_change, ibkr_execution_id, ibkr_order_id
        ) VALUES (
            %(owner_kind)s, %(forward_test_id)s, 'fill', %(time_utc)s, %(account)s, %(symbol)s, %(exchange)s,
            %(currency)s, %(quantity_change)s, %(price)s, %(commission)s, %(cash_change)s, %(ibkr_execution_id)s,
            %(ibkr_order_id)s
        )
        ON CONFLICT (ibkr_execution_id) WHERE ibkr_execution_id IS NOT NULL DO NOTHING
        """,
        {
            "owner_kind": fill.owner.kind,
            "forward_test_id": fill.owner.forward_test_id,
            "time_utc": fill.time_utc,
            "account": fill.account,
            "symbol": fill.instrument.symbol,
            "exchange": fill.instrument.exchange,
            "currency": fill.instrument.currency,
            "quantity_change": fill.quantity_change,
            "price": fill.price,
            "commission": fill.commission,
            "cash_change": fill.cash_change_usd,
            "ibkr_execution_id": fill.ibkr_execution_id,
            "ibkr_order_id": fill.ibkr_order_id,
        },
    )


@dataclass(frozen=True)
class LedgerFill:
    """One fill or stock split adjustment of an owner. `commission` is in the currency of the instrument,
    `cash_change` in USD. A split adjustment has no price, the cash in lieu as `cash_change`, and the split ratio."""

    entry_kind: Literal["fill", "split_adjustment"]
    time_utc: datetime
    symbol: str
    exchange: str
    currency: str
    quantity_change: Decimal
    price: Decimal | None
    commission: Decimal
    cash_change: Decimal
    ibkr_execution_id: str | None
    split_ratio: Decimal | None


OWNER_FILLS_QUERY = """
    SELECT entry.entry_kind, entry.time_utc, entry.symbol, entry.exchange, entry.currency, entry.quantity_change,
        CASE WHEN entry.entry_kind = 'fill' THEN entry.price END AS price, entry.commission, entry.cash_change,
        entry.ibkr_execution_id, stock_split.split_ratio
    FROM owner_ledger_entry AS entry
    LEFT JOIN stock_split ON stock_split.id = entry.stock_split_id
    WHERE entry.entry_kind IN ('fill', 'split_adjustment') AND entry.owner_kind = %(owner_kind)s
        AND entry.forward_test_id IS NOT DISTINCT FROM %(forward_test_id)s
    ORDER BY entry.time_utc, entry.id
"""


async def select_owner_fills(connection: psycopg.AsyncConnection, owner: Owner) -> list[LedgerFill]:
    """The fills and the split adjustments of the owner in all accounts, oldest first."""
    async with connection.cursor(row_factory=class_row(LedgerFill)) as cursor:
        await cursor.execute(OWNER_FILLS_QUERY, {"owner_kind": owner.kind, "forward_test_id": owner.forward_test_id})
        return await cursor.fetchall()


def select_owner_fills_blocking(connection: psycopg.Connection, owner: Owner) -> list[LedgerFill]:
    """`select_owner_fills` for a synchronous connection, for example in a NautilusTrader DataActor."""
    with connection.cursor(row_factory=class_row(LedgerFill)) as cursor:
        cursor.execute(OWNER_FILLS_QUERY, {"owner_kind": owner.kind, "forward_test_id": owner.forward_test_id})
        return cursor.fetchall()


async def select_owner_account(connection: psycopg.AsyncConnection, owner: Owner) -> str | None:
    """The account of the first entry of the owner. None when the owner has no entry."""
    cursor = await connection.execute(
        """
        SELECT account FROM owner_ledger_entry
        WHERE owner_kind = %(owner_kind)s AND forward_test_id IS NOT DISTINCT FROM %(forward_test_id)s
        ORDER BY id LIMIT 1
        """,
        {"owner_kind": owner.kind, "forward_test_id": owner.forward_test_id},
    )
    row = await cursor.fetchone()
    return None if row is None else str(row[0])


TRANSFER_INSERT = """
    INSERT INTO owner_ledger_entry (
        owner_kind, forward_test_id, entry_kind, time_utc, account, symbol, exchange, currency, quantity_change, price,
        cash_change
    ) VALUES (%s, %s, 'transfer', %s, %s, %s, %s, %s, %s, %s, %s)
"""


async def insert_cash_transfer(  # noqa: PLR0913 readability-exception: one keyword argument per part of a transfer.
    connection: psycopg.AsyncConnection,
    *,
    account: str,
    source: Owner,
    target: Owner,
    cash_usd: Decimal,
    time_utc: datetime,
) -> None:
    """2 `transfer` cash rows: the source gives `cash_usd` to the target. The caller commits."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            TRANSFER_INSERT,
            [
                (owner.kind, owner.forward_test_id, time_utc, account, None, None, LEDGER_CASH_CURRENCY, 0, None, cash)
                for owner, cash in ((source, -cash_usd), (target, cash_usd))
            ],
        )


async def insert_position_transfer(  # noqa: PLR0913 readability-exception: one keyword argument per part of a transfer.
    connection: psycopg.AsyncConnection,
    *,
    account: str,
    source: Owner,
    target: Owner,
    position: OwnerPosition,
    time_utc: datetime,
) -> None:
    """2 `transfer` rows: the source gives the position to the target at its average cost. The caller commits."""
    instrument = position.instrument
    async with connection.cursor() as cursor:
        await cursor.executemany(
            TRANSFER_INSERT,
            [
                (
                    owner.kind,
                    owner.forward_test_id,
                    time_utc,
                    account,
                    instrument.symbol,
                    instrument.exchange,
                    instrument.currency,
                    quantity,
                    position.average_cost,
                    0,
                )
                for owner, quantity in ((source, -position.quantity), (target, position.quantity))
            ],
        )


def find_ledger_start_utc(entries: list[LedgerEntry]) -> datetime | None:
    starts = [entry.time_utc for entry in entries if entry.entry_kind == "ledger_start"]
    return min(starts) if starts else None


def sum_owner_cash_usd(entries: list[LedgerEntry], owner: Owner) -> Decimal:
    return sum((entry.cash_change for entry in entries if entry.owner == owner), Decimal(0))


def sum_owner_positions(entries: list[LedgerEntry]) -> list[OwnerPosition]:
    """The positions of all owners, in the order of their first entry. Positions of 0 shares are not in the list."""
    quantities: dict[tuple[Owner, Instrument], Decimal] = {}
    costs: dict[tuple[Owner, Instrument], Decimal] = {}
    for entry in entries:
        if entry.symbol is None or entry.exchange is None:
            continue
        key = (entry.owner, Instrument(symbol=entry.symbol, exchange=entry.exchange, currency=entry.currency))
        quantity = quantities.get(key, Decimal(0))
        cost = costs.get(key, Decimal(0))
        if entry.entry_kind == "split_adjustment" and entry.price is None:
            # A stock split keeps the total cost (section 11.11).
            pass
        elif entry.quantity_change > 0 and entry.price is not None:
            cost += entry.quantity_change * entry.price
        elif entry.quantity_change < 0 and quantity > 0:
            # A sale keeps the average cost: the cost goes down by the sold part.
            cost -= cost * min(-entry.quantity_change, quantity) / quantity
        quantities[key] = quantity + entry.quantity_change
        # A position of 0 shares has no cost, also after a reverse split with cash in lieu for all shares.
        costs[key] = cost if quantities[key] != 0 else Decimal(0)
    return [
        OwnerPosition(
            owner=owner,
            instrument=instrument,
            quantity=quantity,
            average_cost=costs[owner, instrument] / quantity if quantity > 0 else None,
        )
        for (owner, instrument), quantity in quantities.items()
        if quantity != 0
    ]
