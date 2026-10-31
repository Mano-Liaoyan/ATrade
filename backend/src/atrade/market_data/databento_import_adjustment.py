"""Symbol change links and stock split adjustment of the Databento import (docs/architecture/market_data.md sections
8.8.3 and 8.8.4).

Both steps change the bars of the import in the temporary table `databento_import_bar`, before the import saves them
in databento_bar.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import groupby

import psycopg

from atrade.foundation.bar import Bar, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import databento_import_sql
from atrade.market_data.stock_split_detection import (
    DailyPrices,
    FoundSplit,
    find_splits_by_detection_rule,
    find_splits_from_ibkr_closes,
)

# Reads the IBKR TRADES daily bars of an instrument in a time range. An empty list: IBKR has no bars of it.
type IbkrDailyBarReader = Callable[[Instrument, TimeRange], list[Bar]]

# The confirmation of a stock split that the IBKR closes show. The detection rule gives no confirmation: the stock
# split waits for the user check (section 8.13.1).
BAR_EVIDENCE = "bar_evidence"
IMPORT_PRICES_CURSOR = "databento_import_prices"


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
        connection.execute(
            databento_import_sql.MOVE_TO_NEW_SYMBOL, {**parameters, "change_start_utc": change_start_utc}
        )
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


def find_instrument_splits(
    instrument: Instrument, prices: list[DailyPrices], last_day: date, read_ibkr_daily_bars: IbkrDailyBarReader | None
) -> list[DetectedSplit]:
    """An instrument with a bar on the last day of the import still trades: the IBKR closes show its stock splits.
    The detection rule finds the stock splits of the other instruments, and of instruments that IBKR does not have."""
    if read_ibkr_daily_bars is not None and prices[-1].day == last_day:
        time_range = TimeRange(to_utc_day(prices[0].day), to_utc_day(last_day + timedelta(days=1)))
        ibkr_bars = read_ibkr_daily_bars(instrument, time_range)
        if ibkr_bars:
            ibkr_closes = {bar.start_utc.date(): bar.close for bar in ibkr_bars}
            return to_detected(instrument, find_splits_from_ibkr_closes(prices, ibkr_closes), BAR_EVIDENCE)
    return to_detected(instrument, find_splits_by_detection_rule(prices), None)


def to_detected(instrument: Instrument, splits: list[FoundSplit], confirmation: str | None) -> list[DetectedSplit]:
    return [DetectedSplit(instrument, split.ex_date, split.split_ratio, confirmation) for split in splits]


def detect_stock_splits(
    connection: psycopg.Connection, read_ibkr_daily_bars: IbkrDailyBarReader | None
) -> list[DetectedSplit]:
    last_row = connection.execute(databento_import_sql.SELECT_LAST_IMPORT_DAY).fetchone()
    if last_row is None or last_row[0] is None:
        return []
    last_day: date = last_row[0].date()
    splits: list[DetectedSplit] = []
    for instrument, prices in read_instrument_prices(connection):
        splits += find_instrument_splits(instrument, prices, last_day, read_ibkr_daily_bars)
    return splits


def record_stock_splits(connection: psycopg.Connection, splits: list[DetectedSplit]) -> None:
    """A stock split that is in `stock_split` already keeps its row, also its confirmation by the user."""
    with connection.cursor() as cursor:
        cursor.executemany(
            databento_import_sql.INSERT_STOCK_SPLIT,
            [
                {
                    "symbol": split.instrument.symbol,
                    "exchange": split.instrument.exchange,
                    "currency": split.instrument.currency,
                    "ex_date_utc": to_utc_day(split.ex_date),
                    "split_ratio": split.split_ratio,
                    "confirmation": split.confirmation,
                }
                for split in splits
            ],
        )


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
    connection: psycopg.Connection, read_ibkr_daily_bars: IbkrDailyBarReader | None
) -> tuple[list[SymbolLink], list[DetectedSplit]]:
    """Links the symbols and records the stock splits of the daily bars. `adjust_import_bars` then changes the bars."""
    links = link_symbols(connection)
    splits = detect_stock_splits(connection, read_ibkr_daily_bars)
    record_stock_splits(connection, splits)
    return links, splits
