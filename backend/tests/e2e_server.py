"""Backend server for the Playwright tests: the real app with fakes and a real PostgreSQL.

Production code has no fake mode. Playwright starts this file (frontend/playwright.config.ts).
Environment: ATRADE_TEST_DATABASE_URL, ATRADE_E2E_FRONTEND_BUILD_DIR, ATRADE_E2E_PORT.
"""

import asyncio
import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import uvicorn

from atrade.app import create_web_app, upgrade_database
from atrade.forward_test import ForwardTestWorker
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.forward_test_child import FakeChildStarter
from tests.fakes.ibkr import (
    SAMPLE_INSTRUMENTS,
    FakeGatewayConnection,
    make_balance_values,
    make_forward_test_order,
    make_stock_position,
)

FAKE_ACCOUNT_ID = "DU1234567"
E2E_POSITION_COUNT = 40
E2E_FORWARD_TEST_ORDER_COUNT = 30
E2E_FORWARD_TEST_ID = 42
E2E_FORWARD_TEST_CLIENT_ID = 10
E2E_FORWARD_TEST_STRATEGY_NAME = "E2E stopped forward tests"
E2E_STOPPED_FORWARD_TEST_COUNT = 30
# The stopped forward tests never run, so their strategy version needs no real code.
E2E_FORWARD_TEST_STRATEGY_CODE = "# The strategy version of the stopped e2e forward tests.\n"
FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
LISTEN_HOST = "127.0.0.1"
# The Playwright projects run at the same time against one database. The watchlist holds each instrument once,
# so each project gets its own watchlist instruments: <PROJECT NAME>01 ... <PROJECT NAME>25 (frontend/e2e/watchlist.spec.ts).
PLAYWRIGHT_PROJECT_NAMES = ["chromium", "firefox", "webkit", "msedge"]
WATCHLIST_INSTRUMENTS_PER_PROJECT = 25
WATCHLIST_INSTRUMENTS = [
    Instrument(symbol=f"{project_name.upper()}{number:02d}", exchange="ARCA", currency="USD")
    for project_name in PLAYWRIGHT_PROJECT_NAMES
    for number in range(1, WATCHLIST_INSTRUMENTS_PER_PROJECT + 1)
]


def add_stopped_forward_tests(database_url: str) -> None:
    """Enough stopped forward tests to overflow the forward test list, so that the e2e tests can check its scroll
    track. The e2e database is not cleared, so the rows are added only one time."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        strategy_row = connection.execute(
            """
            INSERT INTO strategy (name, created_at_utc) VALUES (%(name)s, %(now)s)
            ON CONFLICT (name) DO NOTHING RETURNING id
            """,
            {"name": E2E_FORWARD_TEST_STRATEGY_NAME, "now": FIXED_NOW_UTC},
        ).fetchone()
        if strategy_row is None:
            return
        version_row = connection.execute(
            """
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
            VALUES (%(strategy_id)s, 1, %(code)s, %(code_sha256)s, %(now)s) RETURNING id
            """,
            {
                "strategy_id": strategy_row[0],
                "code": E2E_FORWARD_TEST_STRATEGY_CODE,
                "code_sha256": hashlib.sha256(E2E_FORWARD_TEST_STRATEGY_CODE.encode()).hexdigest(),
                "now": FIXED_NOW_UTC,
            },
        ).fetchone()
        assert version_row is not None
        for number in range(1, E2E_STOPPED_FORWARD_TEST_COUNT + 1):
            connection.execute(
                """
                INSERT INTO forward_test (
                    strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status,
                    created_at_utc, stopped_at_utc
                ) VALUES (%(version_id)s, %(symbol)s, 'ARCA', 'USD', '1-MINUTE', 'stopped', 'stopped', %(now)s, %(now)s)
                """,
                {"version_id": version_row[0], "symbol": f"FTS{number:02d}", "now": FIXED_NOW_UTC},
            )


async def serve_with_forward_test_worker(server: uvicorn.Server, worker: ForwardTestWorker) -> None:
    # The forward-test service of Compose runs the worker. Here it runs in the same process, with fake children.
    worker_task = asyncio.create_task(worker.keep_comparing())
    try:
        await server.serve()
    finally:
        worker_task.cancel()


def main() -> None:
    database_url = os.environ["ATRADE_TEST_DATABASE_URL"]
    frontend_build_dir = Path(os.environ["ATRADE_E2E_FRONTEND_BUILD_DIR"])
    port = int(os.environ["ATRADE_E2E_PORT"])
    upgrade_database(database_url)
    add_stopped_forward_tests(database_url)
    settings = Settings(
        database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=FAKE_ACCOUNT_ID
    )
    gateway_connection = FakeGatewayConnection(
        managed_accounts=[FAKE_ACCOUNT_ID], instruments=[*SAMPLE_INSTRUMENTS, *WATCHLIST_INSTRUMENTS]
    )
    gateway_connection.account_values = make_balance_values(
        FAKE_ACCOUNT_ID, net_liquidation_usd="101234.50", cash_usd="25000.00"
    )
    # Enough positions to overflow the position table, so that the e2e tests can check its scroll track.
    gateway_connection.portfolio = [
        make_stock_position(FAKE_ACCOUNT_ID, symbol=f"TEST{number:02d}", quantity="10", market_price="100")
        for number in range(1, E2E_POSITION_COUNT + 1)
    ]
    # Enough forward test orders to overflow the order list, so that the e2e tests can check its scroll track.
    gateway_connection.open_orders = [
        make_forward_test_order(
            FAKE_ACCOUNT_ID,
            forward_test_id=E2E_FORWARD_TEST_ID,
            order_id=number,
            client_id=E2E_FORWARD_TEST_CLIENT_ID,
            symbol=f"FTO{number:02d}",
        )
        for number in range(1, E2E_FORWARD_TEST_ORDER_COUNT + 1)
    ]
    clock = FixedClock(FIXED_NOW_UTC)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    # Each fake child stops at once, like a stop that cancelled all orders (section 17.5).
    child_starter = FakeChildStarter(is_ending_children_at_once=True)
    worker = ForwardTestWorker(database_url=database_url, clock=clock, start_child=child_starter.start_child)
    server = uvicorn.Server(uvicorn.Config(app, host=LISTEN_HOST, port=port, workers=1))
    asyncio.run(serve_with_forward_test_worker(server, worker))


if __name__ == "__main__":
    main()
