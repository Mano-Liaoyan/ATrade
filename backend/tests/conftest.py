"""Shared fixtures: the test database, the fixed clock, and the HTTP client of the Web app.

Fixtures are only for the database connection, fakes, and the clock (docs/architecture.md section 17.2).
"""

import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
import pytest
from psycopg import sql

from atrade.app.database_migrations import upgrade_database
from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values

TEST_DATABASE_URL_VARIABLE = "ATRADE_TEST_DATABASE_URL"
FAKE_ACCOUNT_ID = "DU1234567"
FAKE_NET_LIQUIDATION_USD = "100000"
FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    database_url = os.environ.get(TEST_DATABASE_URL_VARIABLE)
    if database_url is None:
        pytest.skip(f"{TEST_DATABASE_URL_VARIABLE} is not set. Run ./scripts/check, which starts PostgreSQL.")
    upgrade_database(database_url)
    return database_url


@pytest.fixture
def database_url(migrated_database_url: str) -> Iterator[str]:
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        table_rows = connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        ).fetchall()
        table_names = [str(row[0]) for row in table_rows]
        if table_names:
            table_identifiers = [sql.Identifier(name) for name in table_names]
            table_list = sql.SQL(", ").join(table_identifiers)
            connection.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(table_list))
    yield migrated_database_url


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(FIXED_NOW_UTC)


@pytest.fixture
def frontend_build_dir(tmp_path: Path) -> Path:
    build_dir = tmp_path / "frontend-build"
    (build_dir / "_app").mkdir(parents=True)
    (build_dir / "200.html").write_text("<!doctype html><title>ATrade</title><div id=app-shell></div>")
    (build_dir / "_app" / "start.js").write_text("console.log('start');")
    (tmp_path / "secret.txt").write_text("outside the build directory")
    return build_dir


@pytest.fixture
async def web_client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> AsyncIterator[httpx.AsyncClient]:
    """The paper account check passes. The account has 100000 USD NetLiquidation and cash, for forward test starts."""
    settings = Settings(
        database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=FAKE_ACCOUNT_ID
    )
    gateway_connection = FakeGatewayConnection(managed_accounts=[FAKE_ACCOUNT_ID])
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(
        FAKE_ACCOUNT_ID, net_liquidation_usd=FAKE_NET_LIQUIDATION_USD, cash_usd=FAKE_NET_LIQUIDATION_USD
    )
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
