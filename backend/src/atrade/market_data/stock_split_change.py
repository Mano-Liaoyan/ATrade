"""The change of the stored bars at a confirmed stock split (docs/architecture/market_data.md section 8.13.3).

The change sends no request to IBKR and does not delete bars or saved ranges. The saved results of earlier backtests
do not change, because a backtest saves its results and does not read the bars again.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, LiteralString

import psycopg
from psycopg import sql

from atrade.foundation.instrument import Instrument
from atrade.market_data.bar_source import BarSource, bar_table
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries

# The confirmations of a stock split from IBKR evidence (section 8.13.1).
type SplitConfirmation = Literal["both_evidences", "bar_evidence", "user_apply"]

# A candidate of evidence A gets the confirmation. A stock split that is confirmed already, or a Databento import split
# (it waits for the import check), gives no row, so the bars are not divided 2 times.
WRITE_STOCK_SPLIT: LiteralString = """
    INSERT INTO stock_split (
        symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc
    )
    VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(ex_date_utc)s, %(split_ratio)s, 'ibkr_evidence',
        %(confirmation)s, %(recorded_at_utc)s)
    ON CONFLICT (symbol, exchange, currency, ex_date_utc) DO UPDATE SET
        split_ratio = excluded.split_ratio, confirmation = excluded.confirmation,
        recorded_at_utc = excluded.recorded_at_utc
    WHERE stock_split.confirmation IS NULL AND stock_split.source = 'ibkr_evidence'
    RETURNING id
"""
CHANGE_BARS_TEMPLATE = sql.SQL("""
    UPDATE {bar_table}
    SET open = open / %(split_ratio)s, high = high / %(split_ratio)s, low = low / %(split_ratio)s,
        close = close / %(split_ratio)s, volume = volume * %(split_ratio)s
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s AND start_utc < %(ex_date_utc)s
""")
# The bar tables of all bar sources. Each table holds all bar periods.
CHANGE_BARS_QUERIES = [CHANGE_BARS_TEMPLATE.format(bar_table=bar_table(bar_source)) for bar_source in BarSource]


class StockSplitConfirmedError(Exception):
    """The stock split is confirmed already, or is a Databento import split. Nothing changed."""


@dataclass(frozen=True)
class StockSplitChange:
    """`ex_date_utc` is 00:00 UTC of the ex-date. `split_ratio` is the count of new shares for 1 old share."""

    instrument: Instrument
    ex_date_utc: datetime
    split_ratio: Decimal


def create_change_parameters(change: StockSplitChange) -> dict[str, object]:
    return {
        "symbol": change.instrument.symbol,
        "exchange": change.instrument.exchange,
        "currency": change.instrument.currency,
        "ex_date_utc": change.ex_date_utc,
        "split_ratio": change.split_ratio,
    }


def change_stored_bars_blocking(connection: psycopg.Connection, change: StockSplitChange) -> None:
    """Step 2 of section 8.13.3 in the transaction of the caller: the Databento import check. The caller updates
    the daily bar summaries of all its instruments after the changes."""
    for query in CHANGE_BARS_QUERIES:
        connection.execute(query, create_change_parameters(change))


async def apply_stock_split(
    *, database_url: str, change: StockSplitChange, confirmation: SplitConfirmation, recorded_at_utc: datetime
) -> None:
    """Confirms a stock split from IBKR evidence and changes the stored bars, in one transaction: writes the
    `stock_split` row, changes the bars before the ex-date in all bar tables and bar periods, and updates the daily
    bar summary of the instrument. No IBKR call.

    Raises StockSplitConfirmedError when the stock split of the instrument and the ex-date is confirmed already, or is a
    Databento import split.
    """
    async with await psycopg.AsyncConnection.connect(database_url) as connection, connection.transaction():
        parameters = create_change_parameters(change)
        cursor = await connection.execute(
            WRITE_STOCK_SPLIT, {**parameters, "confirmation": confirmation, "recorded_at_utc": recorded_at_utc}
        )
        if await cursor.fetchone() is None:
            message = (
                f"The stock split of {change.instrument.symbol} on {change.ex_date_utc:%Y-%m-%d} is confirmed "
                "already or waits for the import check."
            )
            raise StockSplitConfirmedError(message)
        for query in CHANGE_BARS_QUERIES:
            await connection.execute(query, parameters)
        await update_daily_bar_summaries(connection, [change.instrument])
