"""The migration that adds the out-of-sample split columns keeps the existing backtests without a split."""

from collections.abc import Iterator
from urllib.parse import urlsplit

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql

from atrade.app.database_migrations import MIGRATIONS_DIR

REVISION_BEFORE_THE_SPLIT = "969360e99893"
SPLIT_REVISION = "2f6a9c1e4d85"
EMPTY_DATABASE_NAME = "atrade_split_migration_test"


@pytest.fixture
def empty_database_url(migrated_database_url: str) -> Iterator[str]:
    """A new empty database on the server of the test database."""
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(EMPTY_DATABASE_NAME)))
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(EMPTY_DATABASE_NAME)))
    yield urlsplit(migrated_database_url)._replace(path=f"/{EMPTY_DATABASE_NAME}").geturl()
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(EMPTY_DATABASE_NAME)))


def upgrade_to(database_url: str, revision: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, revision)


def test_existing_backtest_gets_a_share_of_0_and_no_split_time(empty_database_url: str) -> None:
    upgrade_to(empty_database_url, REVISION_BEFORE_THE_SPLIT)
    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        connection.execute("""
            INSERT INTO strategy (name, created_at_utc) VALUES ('Old', '2026-01-01T00:00:00Z');
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
                VALUES (1, 1, '', '', '2026-01-01T00:00:00Z');
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, status, created_at_utc)
                VALUES (1, 'BTEST', 'ARCA', 'USD', '1-DAY', '2026-03-01T00:00:00Z', '2026-04-01T00:00:00Z', 10000,
                'finished', '2026-01-01T00:00:00Z');
        """)

    upgrade_to(empty_database_url, SPLIT_REVISION)

    with psycopg.connect(empty_database_url) as connection:
        assert connection.execute("SELECT out_of_sample_share, split_time_utc FROM backtest").fetchall() == [(0, None)]
