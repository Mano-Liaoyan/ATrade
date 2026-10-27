"""SQL for the manual_order table. Only paper_trading reads or writes it. The table has no order status."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class NewManualOrder:
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


@dataclass(frozen=True)
class ManualOrderRecord:
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


MANUAL_ORDER_COLUMNS = """
    id, created_at_utc, account, symbol, exchange, currency, side, quantity, order_type, limit_price,
    time_in_force, ibkr_order_id
"""


async def insert_manual_order(connection: psycopg.AsyncConnection, order: NewManualOrder) -> ManualOrderRecord:
    async with connection.cursor(row_factory=class_row(ManualOrderRecord)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO manual_order (
                created_at_utc, account, symbol, exchange, currency, side, quantity, order_type, limit_price,
                time_in_force, ibkr_order_id
            ) VALUES (
                %(created_at_utc)s, %(account)s, %(symbol)s, %(exchange)s, %(currency)s, %(side)s, %(quantity)s,
                %(order_type)s, %(limit_price)s, %(time_in_force)s, %(ibkr_order_id)s
            )
            RETURNING {MANUAL_ORDER_COLUMNS}
            """,
            {
                "created_at_utc": order.created_at_utc,
                "account": order.account,
                "symbol": order.symbol,
                "exchange": order.exchange,
                "currency": order.currency,
                "side": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "limit_price": order.limit_price,
                "time_in_force": order.time_in_force,
                "ibkr_order_id": order.ibkr_order_id,
            },
        )
        record = await cursor.fetchone()
    if record is None:
        message = "INSERT ... RETURNING returned no row."
        raise RuntimeError(message)
    return record


async def select_manual_orders(connection: psycopg.AsyncConnection) -> list[ManualOrderRecord]:
    async with connection.cursor(row_factory=class_row(ManualOrderRecord)) as cursor:
        await cursor.execute(f"SELECT {MANUAL_ORDER_COLUMNS} FROM manual_order ORDER BY id")
        return await cursor.fetchall()


async def has_manual_order(connection: psycopg.AsyncConnection, *, account: str, ibkr_order_id: int) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM manual_order WHERE account = %(account)s AND ibkr_order_id = %(ibkr_order_id)s LIMIT 1",
        {"account": account, "ibkr_order_id": ibkr_order_id},
    )
    return await cursor.fetchone() is not None
