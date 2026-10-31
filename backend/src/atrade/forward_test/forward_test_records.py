"""SQL for the record tables of a forward test: forward_test_fill and forward_test_equity_point (section 12.8), and
forward_test_same_period_backtest (section 12.10). The fills of a new forward test are in the owner ledger of
`paper_trading`. forward_test_fill keeps only the fills of the forward tests before the owner ledger (section 12.24).

The DataActor in the child process writes them with a synchronous connection, because NautilusTrader calls `on_bar`
synchronously. The Web process reads them with an asynchronous connection.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal

import psycopg
from psycopg.rows import class_row

from atrade.backtest import BacktestTrade, EquityPoint
from atrade.foundation.instrument import Instrument
from atrade.paper_trading import LedgerFill, read_forward_test_fills, read_forward_test_fills_blocking

FILL_COLUMNS: Final = "time_utc, side, quantity_shares, price_usd, commission_usd"


def save_equity_point(connection: psycopg.Connection, *, forward_test_id: int, equity_point: EquityPoint) -> None:
    """A bar that a restart reads again adds no row (ON CONFLICT DO NOTHING)."""
    connection.execute(
        """
        INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd)
        VALUES (%(forward_test_id)s, %(time_utc)s, %(equity_usd)s)
        ON CONFLICT DO NOTHING
        """,
        {"forward_test_id": forward_test_id, "time_utc": equity_point.time_utc, "equity_usd": equity_point.equity_usd},
    )


async def save_equity_points(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, equity_points: list[EquityPoint]
) -> None:
    """The equity points of a multi-instrument forward test. A point that is saved already stays."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd)
            VALUES (%(forward_test_id)s, %(time_utc)s, %(equity_usd)s)
            ON CONFLICT DO NOTHING
            """,
            [
                {"forward_test_id": forward_test_id, "time_utc": point.time_utc, "equity_usd": point.equity_usd}
                for point in equity_points
            ],
        )


@dataclass(frozen=True)
class ForwardTestFill:
    """A fill, or a stock split adjustment (section 12.8). The trade of a split adjustment has the price 0 and the cash
    in lieu as a negative commission, so the equity curve adds the shares and the cash in lieu."""

    instrument: Instrument
    trade: BacktestTrade
    kind: Literal["fill", "split_adjustment"] = "fill"
    split_ratio: Decimal | None = None
    cash_in_lieu_usd: Decimal | None = None


def convert_ledger_fill(fill: LedgerFill) -> ForwardTestFill:
    """A ledger fill as a trade: the sign of the quantity change gives the side."""
    is_split = fill.entry_kind == "split_adjustment"
    return ForwardTestFill(
        instrument=Instrument(symbol=fill.symbol, exchange=fill.exchange, currency=fill.currency),
        trade=BacktestTrade(
            time_utc=fill.time_utc,
            side="BUY" if fill.quantity_change > 0 else "SELL",
            quantity_shares=abs(fill.quantity_change),
            price_usd=Decimal(0) if fill.price is None else fill.price,
            commission_usd=-fill.cash_change if is_split else fill.commission,
            symbol=fill.symbol,
            exchange=fill.exchange,
        ),
        kind=fill.entry_kind,
        split_ratio=fill.split_ratio,
        cash_in_lieu_usd=fill.cash_change if is_split else None,
    )


def list_trades(fills: list[ForwardTestFill]) -> list[BacktestTrade]:
    """The trades of the fills, without the split adjustments: the metrics and the comparison count fills only."""
    return [fill.trade for fill in fills if fill.kind == "fill"]


def select_ledger_fills_blocking(connection: psycopg.Connection, forward_test_id: int) -> list[ForwardTestFill]:
    return [convert_ledger_fill(fill) for fill in read_forward_test_fills_blocking(connection, forward_test_id)]


async def select_forward_test_fills(
    connection: psycopg.AsyncConnection,
    *,
    forward_test_id: int,
    instrument: Instrument | None,
    uses_owner_ledger: bool,
) -> list[ForwardTestFill]:
    """The fills from the owner ledger (section 12.8). A forward test of the time before the owner ledger keeps its
    fills in forward_test_fill, on its one instrument (section 12.24). A multi-instrument forward test (instrument
    None) always uses the owner ledger."""
    if uses_owner_ledger or instrument is None:
        return [convert_ledger_fill(fill) for fill in await read_forward_test_fills(connection, forward_test_id)]
    return [ForwardTestFill(instrument, trade) for trade in await select_fills(connection, forward_test_id)]


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
