"""SQL for the record tables of a forward test: forward_test_fill and forward_test_equity_point (section 12.8), and
forward_test_same_period_backtest (section 12.10).

The DataActor in the child process writes them with a synchronous connection, because NautilusTrader calls `on_bar`
synchronously. The Web process reads them with an asynchronous connection.
"""

from dataclasses import dataclass
from typing import Final

import psycopg
from psycopg.rows import class_row

from atrade.backtest import BacktestTrade, EquityPoint


@dataclass(frozen=True)
class RecordedFill:
    # The NautilusTrader TradeId. The same fill can come from the cache again after a restart.
    trade_id: str
    trade: BacktestTrade


FILL_COLUMNS: Final = "time_utc, side, quantity_shares, price_usd, commission_usd"


def select_recorded_fills(connection: psycopg.Connection, forward_test_id: int) -> list[RecordedFill]:
    rows = connection.execute(
        f"""
        SELECT trade_id, {FILL_COLUMNS} FROM forward_test_fill
        WHERE forward_test_id = %(forward_test_id)s ORDER BY time_utc, trade_id
        """,
        {"forward_test_id": forward_test_id},
    ).fetchall()
    return [
        RecordedFill(
            trade_id=row[0],
            trade=BacktestTrade(
                time_utc=row[1], side=row[2], quantity_shares=row[3], price_usd=row[4], commission_usd=row[5]
            ),
        )
        for row in rows
    ]


def save_bar_records(
    connection: psycopg.Connection, *, forward_test_id: int, new_fills: list[RecordedFill], equity_point: EquityPoint
) -> None:
    """One transaction. A fill or a bar that a restart reads again adds no row (ON CONFLICT DO NOTHING)."""
    with connection.transaction(), connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO forward_test_fill (forward_test_id, trade_id, time_utc, side, quantity_shares, price_usd,
                commission_usd)
            VALUES (%(forward_test_id)s, %(trade_id)s, %(time_utc)s, %(side)s, %(quantity_shares)s, %(price_usd)s,
                %(commission_usd)s)
            ON CONFLICT DO NOTHING
            """,
            [
                {
                    "forward_test_id": forward_test_id,
                    "trade_id": fill.trade_id,
                    "time_utc": fill.trade.time_utc,
                    "side": fill.trade.side,
                    "quantity_shares": fill.trade.quantity_shares,
                    "price_usd": fill.trade.price_usd,
                    "commission_usd": fill.trade.commission_usd,
                }
                for fill in new_fills
            ],
        )
        cursor.execute(
            """
            INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd)
            VALUES (%(forward_test_id)s, %(time_utc)s, %(equity_usd)s)
            ON CONFLICT DO NOTHING
            """,
            {
                "forward_test_id": forward_test_id,
                "time_utc": equity_point.time_utc,
                "equity_usd": equity_point.equity_usd,
            },
        )


async def select_fills(connection: psycopg.AsyncConnection, forward_test_id: int) -> list[BacktestTrade]:
    async with connection.cursor(row_factory=class_row(BacktestTrade)) as cursor:
        await cursor.execute(
            f"""
            SELECT {FILL_COLUMNS} FROM forward_test_fill
            WHERE forward_test_id = %(forward_test_id)s ORDER BY time_utc, trade_id
            """,
            {"forward_test_id": forward_test_id},
        )
        return await cursor.fetchall()


async def select_equity_curve(connection: psycopg.AsyncConnection, forward_test_id: int) -> list[EquityPoint]:
    async with connection.cursor(row_factory=class_row(EquityPoint)) as cursor:
        await cursor.execute(
            """
            SELECT time_utc, equity_usd FROM forward_test_equity_point
            WHERE forward_test_id = %(forward_test_id)s ORDER BY time_utc
            """,
            {"forward_test_id": forward_test_id},
        )
        return await cursor.fetchall()


async def insert_same_period_backtest(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, backtest_id: int
) -> None:
    await connection.execute(
        """
        INSERT INTO forward_test_same_period_backtest (forward_test_id, backtest_id)
        VALUES (%(forward_test_id)s, %(backtest_id)s)
        """,
        {"forward_test_id": forward_test_id, "backtest_id": backtest_id},
    )


async def select_same_period_backtest_ids(connection: psycopg.AsyncConnection, forward_test_id: int) -> list[int]:
    """The backtests of "Backtest the same period" for the forward test, newest first."""
    cursor = await connection.execute(
        """
        SELECT backtest_id FROM forward_test_same_period_backtest
        WHERE forward_test_id = %(forward_test_id)s ORDER BY backtest_id DESC
        """,
        {"forward_test_id": forward_test_id},
    )
    return [int(row[0]) for row in await cursor.fetchall()]
