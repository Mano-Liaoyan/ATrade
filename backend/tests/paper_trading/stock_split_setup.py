"""Test data of the stock split tests: owner positions in the owner ledger, an evidence A candidate, and a stored
daily close before the ex-date. Real PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import psycopg

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, StockSplitCandidate, save_received_bars

ACCOUNT_ID = "DU1234567"
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
EX_DATE_UTC = datetime(2026, 1, 2, tzinfo=UTC)
DAY_BEFORE_UTC = EX_DATE_UTC - timedelta(days=1)


def write_ledger_start(database_url: str, *, cash_usd: str = "10000") -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (
                owner_kind, entry_kind, time_utc, account, currency, quantity_change, cash_change
            ) VALUES ('by_hand', 'ledger_start', %s, %s, 'USD', 0, %s)
            """,
            (DAY_BEFORE_UTC, ACCOUNT_ID, Decimal(cash_usd)),
        )


def write_owner_fill(
    database_url: str, *, forward_test_id: int | None, quantity: int, price: str, instrument: Instrument = APPLE
) -> None:
    """A buy fill of a forward test, or of "By hand" for None."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (
                owner_kind, forward_test_id, entry_kind, time_utc, account, symbol, exchange, currency,
                quantity_change, price, cash_change, ibkr_execution_id
            ) VALUES (%s, %s, 'fill', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "by_hand" if forward_test_id is None else "forward_test",
                forward_test_id,
                DAY_BEFORE_UTC,
                ACCOUNT_ID,
                instrument.symbol,
                instrument.exchange,
                instrument.currency,
                quantity,
                Decimal(price),
                -quantity * Decimal(price),
                f"exec-{instrument.symbol}-{forward_test_id}-{quantity}",
            ),
        )


def write_candidate(database_url: str, split_ratio: str, instrument: Instrument = APPLE) -> StockSplitCandidate:
    """An evidence A candidate of `market_data` (docs/architecture/market_data.md section 8.13.2)."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        row = connection.execute(
            """
            INSERT INTO stock_split (symbol, exchange, currency, ex_date_utc, split_ratio, source, recorded_at_utc)
            VALUES (%s, %s, %s, %s, %s, 'ibkr_evidence', %s) RETURNING id
            """,
            (
                instrument.symbol,
                instrument.exchange,
                instrument.currency,
                EX_DATE_UTC,
                Decimal(split_ratio),
                EX_DATE_UTC,
            ),
        ).fetchone()
    assert row is not None
    return StockSplitCandidate(
        id=int(row[0]), instrument=instrument, ex_date_utc=EX_DATE_UTC, split_ratio=Decimal(split_ratio)
    )


async def save_close_before_ex_date(database_url: str, close: str, instrument: Instrument = APPLE) -> None:
    price = Decimal(close)
    bar = Bar(start_utc=DAY_BEFORE_UTC, open=price, high=price, low=price, close=price, volume=Decimal(1000))
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(instrument, BarPeriod.ONE_DAY, TimeRange(DAY_BEFORE_UTC, EX_DATE_UTC)),
        bars=[bar],
    )


def read_split_checks(database_url: str) -> list[tuple[str, str, str]]:
    """(symbol, evidence, status) of each split_check row."""
    with psycopg.connect(database_url) as connection:
        rows = connection.execute("SELECT symbol, evidence, status FROM split_check ORDER BY id").fetchall()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]
