"""Test helper: hand-made daily bars for the quarterly US universe (docs/architecture/market_data.md section 8.9)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.instrument import Instrument


def utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def weekdays(first: date, last: date) -> list[date]:
    """The test data has a bar on each weekday. The universe counts the days with bars, not a calendar."""
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    return [day for day in days if day.weekday() < 5]


def create_bar_rows(instrument: Instrument, days: list[date], close: str, volume: int) -> list[dict[str, object]]:
    """Daily bars with open = high = low = close."""
    return [
        {
            "symbol": instrument.symbol,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "start_utc": utc_day(day),
            "close": Decimal(close),
            "volume": volume,
        }
        for day in days
    ]


def insert_bar_rows(database_url: str, bar_table: LiteralString, rows: list[dict[str, object]]) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            f"""
            INSERT INTO {bar_table} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES (%(symbol)s, %(exchange)s, %(currency)s, '1-DAY', %(start_utc)s, %(close)s, %(close)s, %(close)s,
                %(close)s, %(volume)s)
            """,
            rows,
        )


def insert_daily_bars(database_url: str, instrument: Instrument, days: list[date], close: str, volume: int) -> None:
    """Databento daily bars."""
    insert_bar_rows(database_url, "databento_bar", create_bar_rows(instrument, days, close, volume))


def nyse(symbol: str) -> Instrument:
    return Instrument(symbol=symbol, exchange="NYSE", currency="USD")


def nasdaq(symbol: str) -> Instrument:
    return Instrument(symbol=symbol, exchange="NASDAQ", currency="USD")
