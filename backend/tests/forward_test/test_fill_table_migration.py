"""The migration that drops forward_test_fill and gives the old forward tests an allocated capital (section 12.24)."""

import uuid
from collections.abc import Iterator
from decimal import Decimal
from urllib.parse import urlsplit

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql

from atrade.app.database_migrations import MIGRATIONS_DIR

REVISION_BEFORE = "c4a8e1d7f362"
DROP_REVISION = "d7b2f4a9c613"
INSERT_FORWARD_TEST = """
    INSERT INTO forward_test (strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status,
        client_id, start_balance_usd, allocated_capital_usd, created_at_utc)
    VALUES (%(version_id)s, %(symbol)s, 'NASDAQ', 'USD', '1-DAY', 'stopped', 'stopped',
        %(client_id)s, %(start_balance_usd)s, %(allocated_capital_usd)s, now())
"""


@pytest.fixture
def empty_database_url(migrated_database_url: str) -> Iterator[str]:
    """A new empty database on the server of the test database."""
    database_name = f"atrade_fill_table_migration_{uuid.uuid4().hex}"
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    yield urlsplit(migrated_database_url)._replace(path=f"/{database_name}").geturl()
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))


def make_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    return config


def insert_forward_tests(connection: psycopg.Connection) -> None:
    strategy = connection.execute(
        "INSERT INTO strategy (name, created_at_utc) VALUES ('Old', now()) RETURNING id"
    ).fetchone()
    assert strategy is not None
    version = connection.execute(
        """
        INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
        VALUES (%(strategy_id)s, 1, '', '', now()) RETURNING id
        """,
        {"strategy_id": strategy[0]},
    ).fetchone()
    assert version is not None
    for symbol, client_id, start_balance_usd, allocated_capital_usd in (
        ("OLD", None, 5000, None),
        ("HELD", 7, 6000, None),
        ("NEW", None, None, 7000),
    ):
        connection.execute(
            INSERT_FORWARD_TEST,
            {
                "version_id": version[0],
                "symbol": symbol,
                "client_id": client_id,
                "start_balance_usd": start_balance_usd,
                "allocated_capital_usd": allocated_capital_usd,
            },
        )


def read_allocated_capital(connection: psycopg.Connection) -> dict[str, Decimal | None]:
    rows = connection.execute("SELECT symbol, allocated_capital_usd FROM forward_test").fetchall()
    return dict(rows)


def read_fill_table(connection: psycopg.Connection) -> str | None:
    row = connection.execute("SELECT to_regclass('forward_test_fill')::text").fetchone()
    assert row is not None
    return row[0]


def test_the_migration_drops_the_fill_table_and_downgrade_restores_the_old_rows(empty_database_url: str) -> None:
    config = make_config(empty_database_url)
    command.upgrade(config, REVISION_BEFORE)
    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        insert_forward_tests(connection)

    command.upgrade(config, DROP_REVISION)

    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        assert read_fill_table(connection) is None
        assert read_allocated_capital(connection) == {"OLD": Decimal(5000), "HELD": None, "NEW": Decimal(7000)}

    command.downgrade(config, REVISION_BEFORE)

    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        assert read_fill_table(connection) == "forward_test_fill"
        assert read_allocated_capital(connection) == {"OLD": None, "HELD": None, "NEW": Decimal(7000)}
