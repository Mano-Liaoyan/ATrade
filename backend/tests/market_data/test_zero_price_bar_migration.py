"""The migration that removes the Databento daily bars with price 0 (docs/architecture/market_data.md section 8.8.2)."""

import uuid
from collections.abc import Iterator
from urllib.parse import urlsplit

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql

from atrade.app.database_migrations import MIGRATIONS_DIR

REVISION_BEFORE = "c4e8a1f7b2d6"
ZERO_PRICE_REVISION = "f2a6d9c41e73"
INSERT_BARS = """
    INSERT INTO databento_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT %(symbol)s, 'NASDAQ', 'USD', '1-DAY', '2026-01-01T00:00:00Z'::timestamptz + day * interval '1 day',
        price, price, price, price, 100
    FROM unnest(%(prices)s::numeric[]) WITH ORDINALITY AS bar (price, day)
"""
INSERT_SAVED_RANGE = """
    INSERT INTO databento_bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
    VALUES (%(symbol)s, 'NASDAQ', 'USD', '1-DAY', '2026-01-01T00:00:00Z', '2026-12-31T00:00:00Z')
"""
INSERT_SUMMARY = """
    INSERT INTO daily_bar_summary (symbol, exchange, currency, last_day_start_utc, last_close, average_trading_value_20)
    VALUES (%(symbol)s, 'NASDAQ', 'USD', %(last_day)s, %(last_close)s, %(average)s)
"""


@pytest.fixture
def empty_database_url(migrated_database_url: str) -> Iterator[str]:
    """A new empty database on the server of the test database."""
    database_name = f"atrade_zero_price_migration_{uuid.uuid4().hex}"
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    yield urlsplit(migrated_database_url)._replace(path=f"/{database_name}").geturl()
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))


def upgrade_to(database_url: str, revision: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, revision)


def save_bars(connection: psycopg.Connection, symbol: str, prices: list[int]) -> None:
    connection.execute(INSERT_BARS, {"symbol": symbol, "prices": prices})
    connection.execute(INSERT_SAVED_RANGE, {"symbol": symbol})


def test_the_migration_removes_the_bars_with_price_0_and_calculates_their_summary_again(
    empty_database_url: str,
) -> None:
    upgrade_to(empty_database_url, REVISION_BEFORE)
    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        # The last bar has price 0, and 20 of the 21 bars have a price.
        save_bars(connection, "LASTZERO", [10] * 20 + [0])
        save_bars(connection, "MIDZERO", [10, 0, 12])
        save_bars(connection, "CLEAN", [20, 21])
        for symbol, last_day, last_close, average in (
            ("LASTZERO", "2026-01-22T00:00:00Z", 0, 950),
            ("MIDZERO", "2026-01-04T00:00:00Z", 12, None),
            ("CLEAN", "2026-01-03T00:00:00Z", 21, 7),
        ):
            parameters = {"symbol": symbol, "last_day": last_day, "last_close": last_close, "average": average}
            connection.execute(INSERT_SUMMARY, parameters)

    upgrade_to(empty_database_url, ZERO_PRICE_REVISION)

    with psycopg.connect(empty_database_url) as connection:
        zero_bars = connection.execute("SELECT count(*) FROM databento_bar WHERE close <= 0").fetchone()
        bar_rows = connection.execute("SELECT count(*) FROM databento_bar").fetchone()
        summaries = connection.execute("""
            SELECT symbol, last_day_start_utc::date::text, last_close::float, average_trading_value_20
            FROM daily_bar_summary ORDER BY symbol
        """).fetchall()
    assert zero_bars == (0,)
    assert bar_rows == (24,)
    assert summaries == [
        # A summary without a bar with price 0 does not change: the migration does not read it.
        ("CLEAN", "2026-01-03", 21.0, 7.0),
        ("LASTZERO", "2026-01-21", 10.0, 1000.0),
        ("MIDZERO", "2026-01-04", 12.0, None),
    ]


def test_a_bar_with_price_0_cannot_be_saved_after_the_migration(empty_database_url: str) -> None:
    upgrade_to(empty_database_url, ZERO_PRICE_REVISION)
    with (
        psycopg.connect(empty_database_url) as connection,
        pytest.raises(psycopg.errors.CheckViolation, match="databento_bar_close_is_positive"),
    ):
        connection.execute(INSERT_BARS, {"symbol": "ZERO", "prices": [0]})
