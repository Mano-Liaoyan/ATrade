"""The user check of the Databento import: the stock splits that the detection rule found and the symbol change links
(docs/architecture/market_data.md sections 8.8.3 and 8.8.4).

A detected stock split waits for the check and does not change the bars. The check confirms it and changes the stored
bars before the ex-date and the daily bar summary in place (section 8.13.3), or the user rejects it. A rejected stock split keeps its row, so
the next import does not find it again. The check also records `checked_at_utc` on each link.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.instrument import Instrument
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries_blocking
from atrade.market_data.stock_split_change import StockSplitChange, change_stored_bars_blocking

SELECT_WAITING_SPLITS: LiteralString = """
    SELECT id, symbol, exchange, currency, ex_date_utc, split_ratio FROM stock_split
    WHERE source = 'databento_import' AND confirmation IS NULL
    ORDER BY symbol, ex_date_utc
"""
SELECT_UNCHECKED_LINKS: LiteralString = """
    SELECT id, old_symbol, new_symbol, exchange, change_day FROM databento_symbol_link
    WHERE checked_at_utc IS NULL
    ORDER BY change_day, old_symbol
"""
SET_CONFIRMATION: LiteralString = "UPDATE stock_split SET confirmation = %(confirmation)s WHERE id = %(id)s"
CHECK_LINKS: LiteralString = """
    UPDATE databento_symbol_link SET checked_at_utc = %(checked_at_utc)s WHERE checked_at_utc IS NULL
"""
IMPORT_CHECK = "import_check"
IMPORT_REJECTED = "import_rejected"


class ImportCheckError(Exception):
    """The check changed nothing. The message tells why."""


@dataclass(frozen=True)
class WaitingSplit:
    id: int
    instrument: Instrument
    ex_date_utc: datetime
    split_ratio: Decimal


@dataclass(frozen=True)
class UncheckedLink:
    id: int
    old_symbol: str
    new_symbol: str
    exchange: str
    change_day: date


@dataclass(frozen=True)
class ImportDetections:
    stock_splits: list[WaitingSplit]
    symbol_links: list[UncheckedLink]


def read_detections(connection: psycopg.Connection) -> ImportDetections:
    splits = [
        WaitingSplit(
            id=int(row[0]),
            instrument=Instrument(symbol=str(row[1]), exchange=str(row[2]), currency=str(row[3])),
            ex_date_utc=row[4],
            split_ratio=row[5],
        )
        for row in connection.execute(SELECT_WAITING_SPLITS).fetchall()
    ]
    links = [
        UncheckedLink(
            id=int(row[0]), old_symbol=str(row[1]), new_symbol=str(row[2]), exchange=str(row[3]), change_day=row[4]
        )
        for row in connection.execute(SELECT_UNCHECKED_LINKS).fetchall()
    ]
    return ImportDetections(stock_splits=splits, symbol_links=links)


def read_unchecked_import_detections(*, database_url: str) -> ImportDetections:
    with psycopg.connect(database_url) as connection:
        return read_detections(connection)


def check_import_detections(
    *, database_url: str, rejected_split_ids: set[int], checked_at_utc: datetime
) -> ImportDetections:
    """Confirms all waiting stock splits except the rejected ones, and checks all links, in one transaction.
    Returns the stock splits and links that were waiting."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        detections = read_detections(connection)
        unknown_ids = rejected_split_ids - {split.id for split in detections.stock_splits}
        if unknown_ids:
            names = ", ".join(str(split_id) for split_id in sorted(unknown_ids))
            message = f"No detected stock split waits for the check with the ID {names}."
            raise ImportCheckError(message)
        for split in detections.stock_splits:
            rejected = split.id in rejected_split_ids
            confirmation = IMPORT_REJECTED if rejected else IMPORT_CHECK
            connection.execute(SET_CONFIRMATION, {"confirmation": confirmation, "id": split.id})
            if not rejected:
                change_stored_bars_blocking(
                    connection, StockSplitChange(split.instrument, split.ex_date_utc, split.split_ratio)
                )
        confirmed_instruments = {
            split.instrument for split in detections.stock_splits if split.id not in rejected_split_ids
        }
        update_daily_bar_summaries_blocking(connection, sorted(confirmed_instruments, key=str))
        connection.execute(CHECK_LINKS, {"checked_at_utc": checked_at_utc})
    return detections
