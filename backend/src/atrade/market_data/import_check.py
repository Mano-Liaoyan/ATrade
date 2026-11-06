"""The user check of the Databento import: the stock splits that the detection rule found and the symbol change links
(docs/architecture/market_data.md sections 8.8.3 and 8.8.4).

A detected stock split waits for the check and does not change the bars. The check confirms it and changes the stored
bars before the ex-date and the daily bar summary in place (section 8.13.3), or the user rejects it. A rejected stock split keeps its row, so
the next import does not find it again. The check also records `checked_at_utc` on each link. A link that waits moves
its saved rows to the new symbol, or the user rejects it.
"""

from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.instrument import Instrument
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries_blocking
from atrade.market_data.databento_import_sql import MOVE_SAVED_ROWS_TO_NEW_SYMBOL
from atrade.market_data.stock_split_change import StockSplitChange, change_stored_bars_blocking

SELECT_WAITING_SPLITS: LiteralString = """
    SELECT id, symbol, exchange, currency, ex_date_utc, split_ratio FROM stock_split
    WHERE source = 'databento_import' AND confirmation IS NULL
    ORDER BY symbol, ex_date_utc
"""
SELECT_UNCHECKED_LINKS: LiteralString = """
    SELECT id, old_symbol, new_symbol, exchange, change_day, state FROM databento_symbol_link
    WHERE checked_at_utc IS NULL
    ORDER BY change_day, old_symbol
"""
SET_CONFIRMATION: LiteralString = "UPDATE stock_split SET confirmation = %(confirmation)s WHERE id = %(id)s"
SET_LINK_STATE: LiteralString = "UPDATE databento_symbol_link SET state = %(state)s WHERE id = %(id)s"
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
    is_waiting: bool


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
            id=int(row[0]),
            old_symbol=str(row[1]),
            new_symbol=str(row[2]),
            exchange=str(row[3]),
            change_day=row[4],
            is_waiting=row[5] == "waiting",
        )
        for row in connection.execute(SELECT_UNCHECKED_LINKS).fetchall()
    ]
    return ImportDetections(stock_splits=splits, symbol_links=links)


def read_unchecked_import_detections(*, database_url: str) -> ImportDetections:
    with psycopg.connect(database_url) as connection:
        return read_detections(connection)


def move_link_rows(connection: psycopg.Connection, link: UncheckedLink) -> None:
    parameters = {
        "old_symbol": link.old_symbol,
        "new_symbol": link.new_symbol,
        "exchange": link.exchange,
        "change_start_utc": datetime.combine(link.change_day, time(), UTC),
    }
    for query in MOVE_SAVED_ROWS_TO_NEW_SYMBOL:
        connection.execute(query, parameters)


def check_ids(known_ids: set[int], rejected_ids: AbstractSet[int], description: str) -> None:
    unknown_ids = rejected_ids - known_ids
    if unknown_ids:
        names = ", ".join(str(unknown_id) for unknown_id in sorted(unknown_ids))
        message = f"No {description} waits for the check with the ID {names}."
        raise ImportCheckError(message)


def check_import_detections(
    *,
    database_url: str,
    rejected_split_ids: set[int],
    checked_at_utc: datetime,
    rejected_link_ids: AbstractSet[int] = frozenset(),
) -> ImportDetections:
    """Confirms all waiting stock splits except the rejected ones, moves the saved rows of all waiting links except the
    rejected ones, and checks all links, in one transaction. Returns the stock splits and links that were waiting."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        detections = read_detections(connection)
        waiting_links = [link for link in detections.symbol_links if link.is_waiting]
        check_ids({split.id for split in detections.stock_splits}, rejected_split_ids, "detected stock split")
        check_ids({link.id for link in waiting_links}, rejected_link_ids, "symbol link")
        for split in detections.stock_splits:
            rejected = split.id in rejected_split_ids
            confirmation = IMPORT_REJECTED if rejected else IMPORT_CHECK
            connection.execute(SET_CONFIRMATION, {"confirmation": confirmation, "id": split.id})
            if not rejected:
                change_stored_bars_blocking(
                    connection, StockSplitChange(split.instrument, split.ex_date_utc, split.split_ratio)
                )
        changed_instruments = {
            split.instrument for split in detections.stock_splits if split.id not in rejected_split_ids
        }
        for link in waiting_links:
            rejected = link.id in rejected_link_ids
            connection.execute(SET_LINK_STATE, {"state": "rejected" if rejected else "moved", "id": link.id})
            if not rejected:
                move_link_rows(connection, link)
                changed_instruments.add(Instrument(symbol=link.new_symbol, exchange=link.exchange, currency="USD"))
        update_daily_bar_summaries_blocking(connection, sorted(changed_instruments, key=str))
        connection.execute(CHECK_LINKS, {"checked_at_utc": checked_at_utc})
    return detections
