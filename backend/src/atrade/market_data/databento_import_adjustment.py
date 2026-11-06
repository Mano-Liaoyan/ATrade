"""Symbol change links and stock split adjustment of the Databento import (docs/architecture/market_data.md sections
8.8.3 and 8.8.4).

Both steps change the bars of the import in the temporary table `databento_import_bar`, before the import saves them
in databento_bar.
"""

from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import groupby
from typing import Literal

import psycopg

from atrade.foundation.instrument import Instrument
from atrade.market_data import databento_import_sql
from atrade.market_data.ibkr_split_check import record_split_checks
from atrade.market_data.ibkr_split_report import MATCH_RATIO_TOLERANCE
from atrade.market_data.stock_split_detection import DailyPrices, FoundSplit, find_splits_by_detection_rule

IMPORT_PRICES_CURSOR = "databento_import_prices"

# How the import finds the stock splits of the instruments that still trade (section 8.8.3). `ibkr_check`: the import
# does not look for them. It records each such instrument for the IBKR stock split check program. `detection_rule`:
# the detection rule finds them, like the stock splits of the instruments that stopped trading. The quarterly
# universe update uses it, because no program checks its instruments.
type StillTradingSplitRule = Literal["ibkr_check", "detection_rule"]


@dataclass(frozen=True)
class DetectedSplit:
    """`confirmation` is None when the stock split waits for the user check."""

    instrument: Instrument
    ex_date: date
    split_ratio: Decimal
    confirmation: str | None


@dataclass(frozen=True)
class SymbolLink:
    old_symbol: str
    new_symbol: str
    exchange: str
    change_day: date


def link_symbols(connection: psycopg.Connection) -> list[SymbolLink]:
    """Finds the symbol changes, saves the history of each old symbol under its new symbol, and records the links.
    The links go in the order of their change day, so a chain of 2 changes ends at the last symbol."""
    rows = connection.execute(databento_import_sql.SELECT_SYMBOL_LINKS).fetchall()
    links: list[SymbolLink] = []
    for old_symbol, new_symbol, exchange, change_start_utc in rows:
        link = SymbolLink(str(old_symbol), str(new_symbol), str(exchange), change_start_utc.date())
        parameters = {
            "old_symbol": link.old_symbol,
            "new_symbol": link.new_symbol,
            "exchange": link.exchange,
            "change_day": link.change_day,
        }
        for query in (databento_import_sql.MOVE_TO_NEW_SYMBOL, *databento_import_sql.MOVE_SAVED_ROWS_TO_NEW_SYMBOL):
            connection.execute(query, {**parameters, "change_start_utc": change_start_utc})
        connection.execute(databento_import_sql.INSERT_SYMBOL_LINK, parameters)
        links.append(link)
    return links


def read_instrument_prices(connection: psycopg.Connection) -> Iterator[tuple[Instrument, list[DailyPrices]]]:
    """The daily prices of the import, one instrument at a time. A server-side cursor keeps memory small."""
    with connection.cursor(name=IMPORT_PRICES_CURSOR) as cursor:
        cursor.execute(databento_import_sql.SELECT_IMPORT_PRICES)
        for (symbol, exchange, currency), rows in groupby(cursor, key=lambda row: (row[0], row[1], row[2])):
            instrument = Instrument(symbol=str(symbol), exchange=str(exchange), currency=str(currency))
            prices = [DailyPrices(day=row[3].date(), open=row[4], close=row[5], volume=row[6]) for row in rows]
            yield instrument, prices


def to_utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def to_detected(instrument: Instrument, splits: list[FoundSplit], confirmation: str | None) -> list[DetectedSplit]:
    return [DetectedSplit(instrument, split.ex_date, split.split_ratio, confirmation) for split in splits]


@dataclass(frozen=True)
class FoundImportSplits:
    """The stock splits of the detection rule, and the instruments that wait for the IBKR stock split check."""

    splits: list[DetectedSplit]
    still_trading_instruments: list[Instrument]


def detect_stock_splits(
    connection: psycopg.Connection, still_trading_rule: StillTradingSplitRule, last_day: date
) -> FoundImportSplits:
    """An instrument still trades when it has a bar on the last day of the import."""
    splits: list[DetectedSplit] = []
    still_trading_instruments: list[Instrument] = []
    for instrument, prices in read_instrument_prices(connection):
        if still_trading_rule == "ibkr_check" and prices[-1].day == last_day:
            still_trading_instruments.append(instrument)
        else:
            splits += to_detected(instrument, find_splits_by_detection_rule(prices), None)
    return FoundImportSplits(splits=splits, still_trading_instruments=still_trading_instruments)


def record_stock_splits(connection: psycopg.Connection, splits: list[DetectedSplit]) -> list[DetectedSplit]:
    """Returns the stock splits that got a new row. A stock split that is in `stock_split` already keeps its row, also
    its confirmation by the user."""
    inserted_splits: list[DetectedSplit] = []
    for split in splits:
        inserted = connection.execute(
            databento_import_sql.INSERT_STOCK_SPLIT,
            {
                "symbol": split.instrument.symbol,
                "exchange": split.instrument.exchange,
                "currency": split.instrument.currency,
                "ex_date_utc": to_utc_day(split.ex_date),
                "split_ratio": split.split_ratio,
                "ratio_tolerance": MATCH_RATIO_TOLERANCE,
                "confirmation": split.confirmation,
            },
        )
        if inserted.rowcount == 1:
            inserted_splits.append(split)
    return inserted_splits


def adjust_import_bars(connection: psycopg.Connection) -> None:
    """Saves the bars in the IBKR TRADES form: each confirmed stock split divides the prices before its ex-date by the
    split ratio and multiplies the volume by the split ratio."""
    rows = connection.execute(databento_import_sql.SELECT_APPLIED_SPLITS_OF_IMPORT).fetchall()
    for symbol, exchange, currency, ex_date_utc, split_ratio in rows:
        connection.execute(
            databento_import_sql.ADJUST_IMPORT_BARS,
            {
                "symbol": symbol,
                "exchange": exchange,
                "currency": currency,
                "ex_date_utc": ex_date_utc,
                "split_ratio": split_ratio,
            },
        )


def link_and_detect_splits(
    connection: psycopg.Connection, still_trading_rule: StillTradingSplitRule
) -> tuple[list[SymbolLink], FoundImportSplits]:
    """Links the symbols, records the stock splits of the daily bars, and records the instruments for the IBKR stock
    split check. `adjust_import_bars` then changes the bars with the confirmed stock splits. The result has only the
    stock splits that got a new row."""
    links = link_symbols(connection)
    last_row = connection.execute(databento_import_sql.SELECT_LAST_IMPORT_DAY).fetchone()
    if last_row is None or last_row[0] is None:
        return links, FoundImportSplits(splits=[], still_trading_instruments=[])
    last_day: date = last_row[0].date()
    found_splits = detect_stock_splits(connection, still_trading_rule, last_day)
    inserted_splits = record_stock_splits(connection, found_splits.splits)
    check_end_utc = to_utc_day(last_day + timedelta(days=1))
    record_split_checks(connection, found_splits.still_trading_instruments, check_end_utc)
    return links, replace(found_splits, splits=inserted_splits)
