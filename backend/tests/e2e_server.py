"""Backend server for the Playwright tests: the real app with fakes and a real PostgreSQL.

Production code has no fake mode. Playwright starts this file (frontend/playwright.config.ts).
Environment: ATRADE_TEST_DATABASE_URL, ATRADE_E2E_FRONTEND_BUILD_DIR, ATRADE_E2E_PORT.
"""

import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
import uvicorn

from atrade.app.database_migrations import upgrade_database
from atrade.app.web import create_web_app
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
E2E_CASH_USD = "25000.00"
E2E_UNATTRIBUTED_POSITION_NUMBER = 5
E2E_SHORT_LEDGER_QUANTITY = 5
E2E_FORWARD_TEST_ID = 42
E2E_FORWARD_TEST_CLIENT_ID = 10
E2E_FORWARD_TEST_STRATEGY_NAME = "E2E stopped forward tests"
E2E_STOPPED_FORWARD_TEST_COUNT = 30
# The stopped forward tests never run, so their strategy version needs no real code.
E2E_FORWARD_TEST_STRATEGY_CODE = "# The strategy version of the stopped e2e forward tests.\n"
FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
# A stopped forward test with records, for the comparison with a backtest of the same period (forward_test.md 12.10).
E2E_COMPARED_STRATEGY_NAME = "E2E compared forward test"
E2E_COMPARED_STRATEGY_FILE = Path(__file__).parent / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
E2E_COMPARED_SYMBOL = "FTCMP"
E2E_COMPARED_BAR_COUNT = 45
E2E_COMPARED_FIRST_BAR_START_UTC = datetime(2026, 3, 2, tzinfo=UTC)
# Enough forward test fills to overflow the fill table, so that the e2e tests can check its scroll track.
E2E_COMPARED_FILL_COUNT = 40
# An interruption over these bars: no equity points, and the chart marks them grey.
E2E_COMPARED_INTERRUPTED_BAR_NUMBERS = range(20, 23)
E2E_COMPARED_INTERRUPTION_OFFSET = timedelta(hours=1)
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


def insert_strategy_version(connection: psycopg.Connection, *, name: str, code: str) -> int | None:
    """Returns None when the strategy is already there: the e2e database is not cleared between runs."""
    strategy_row = connection.execute(
        """
        INSERT INTO strategy (name, created_at_utc) VALUES (%(name)s, %(now)s)
        ON CONFLICT (name) DO NOTHING RETURNING id
        """,
        {"name": name, "now": FIXED_NOW_UTC},
    ).fetchone()
    if strategy_row is None:
        return None
    version_row = connection.execute(
        """
        INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
        VALUES (%(strategy_id)s, 1, %(code)s, %(code_sha256)s, %(now)s) RETURNING id
        """,
        {
            "strategy_id": strategy_row[0],
            "code": code,
            "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "now": FIXED_NOW_UTC,
        },
    ).fetchone()
    assert version_row is not None
    return int(version_row[0])


def add_stopped_forward_tests(database_url: str) -> None:
    """Enough stopped forward tests to overflow the forward test list, so that the e2e tests can check its scroll
    track. The e2e database is not cleared, so the rows are added only one time."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        version_id = insert_strategy_version(
            connection, name=E2E_FORWARD_TEST_STRATEGY_NAME, code=E2E_FORWARD_TEST_STRATEGY_CODE
        )
        if version_id is None:
            return
        for number in range(1, E2E_STOPPED_FORWARD_TEST_COUNT + 1):
            connection.execute(
                """
                INSERT INTO forward_test (
                    strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status,
                    created_at_utc, stopped_at_utc
                ) VALUES (%(version_id)s, %(symbol)s, 'ARCA', 'USD', '1-MINUTE', 'stopped', 'stopped', %(now)s, %(now)s)
                """,
                {"version_id": version_id, "symbol": f"FTS{number:02d}", "now": FIXED_NOW_UTC},
            )


def make_compared_close_usd(bar_number: int) -> Decimal:
    # Up for 10 bars, then down for 10 bars, so the bar count strategy wins and loses.
    return Decimal(100) + Decimal(abs((bar_number + 10) % 20 - 10))


def add_compared_bars(connection: psycopg.Connection) -> None:
    """Saved daily bars: the backtest of the same period reads only saved bars."""
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES (%(symbol)s, 'ARCA', 'USD', '1-DAY', %(start_utc)s, %(close)s, %(high)s, %(low)s, %(close)s, 1000)
            ON CONFLICT DO NOTHING
            """,
            [
                {
                    "symbol": E2E_COMPARED_SYMBOL,
                    "start_utc": E2E_COMPARED_FIRST_BAR_START_UTC + timedelta(days=bar_number - 1),
                    "close": make_compared_close_usd(bar_number),
                    "high": make_compared_close_usd(bar_number) + 1,
                    "low": make_compared_close_usd(bar_number) - 1,
                }
                for bar_number in range(1, E2E_COMPARED_BAR_COUNT + 1)
            ],
        )


def add_compared_records(connection: psycopg.Connection, forward_test_id: int) -> None:
    """Rows like the DataActor writes them: 1 fill after each bar end and 1 equity point at each bar end. And 1
    interruption like the worker writes it."""
    bar_ends_utc = {
        bar_number: E2E_COMPARED_FIRST_BAR_START_UTC + timedelta(days=bar_number)
        for bar_number in range(1, E2E_COMPARED_BAR_COUNT + 1)
    }
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO forward_test_fill (forward_test_id, trade_id, time_utc, side, quantity_shares, price_usd,
                commission_usd)
            VALUES (%(id)s, %(trade_id)s, %(time_utc)s, %(side)s, 1, %(price_usd)s, 0)
            """,
            [
                {
                    "id": forward_test_id,
                    "trade_id": f"E2E-{bar_number}",
                    "time_utc": bar_ends_utc[bar_number] + timedelta(seconds=1),
                    "side": "BUY" if bar_number % 2 == 1 else "SELL",
                    "price_usd": make_compared_close_usd(bar_number) + Decimal("0.01"),
                }
                for bar_number in range(1, E2E_COMPARED_FILL_COUNT + 1)
            ],
        )
        cursor.executemany(
            """
            INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd)
            VALUES (%(id)s, %(time_utc)s, %(equity_usd)s)
            """,
            [
                {"id": forward_test_id, "time_utc": bar_end_utc, "equity_usd": Decimal(10000) + bar_number}
                for bar_number, bar_end_utc in bar_ends_utc.items()
                if bar_number not in E2E_COMPARED_INTERRUPTED_BAR_NUMBERS
            ],
        )
        cursor.execute(
            """
            INSERT INTO forward_test_interruption (forward_test_id, reason, started_at_utc, ended_at_utc)
            VALUES (%(id)s, 'crash', %(started_at_utc)s, %(ended_at_utc)s)
            """,
            {
                "id": forward_test_id,
                "started_at_utc": bar_ends_utc[E2E_COMPARED_INTERRUPTED_BAR_NUMBERS.start - 1]
                + E2E_COMPARED_INTERRUPTION_OFFSET,
                "ended_at_utc": bar_ends_utc[E2E_COMPARED_INTERRUPTED_BAR_NUMBERS.stop - 1]
                + E2E_COMPARED_INTERRUPTION_OFFSET,
            },
        )


def add_compared_forward_test(database_url: str) -> None:
    """A stopped forward test with a start balance, fills, and equity points, and the saved bars of its period."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        version_id = insert_strategy_version(
            connection, name=E2E_COMPARED_STRATEGY_NAME, code=E2E_COMPARED_STRATEGY_FILE.read_text()
        )
        if version_id is None:
            return
        add_compared_bars(connection)
        forward_test_row = connection.execute(
            """
            INSERT INTO forward_test (strategy_version_id, symbol, exchange, currency, bar_period, desired_state,
                status, start_balance_usd, created_at_utc, stopped_at_utc)
            VALUES (%(version_id)s, %(symbol)s, 'ARCA', 'USD', '1-DAY', 'stopped', 'stopped', 10000, %(start_utc)s,
                %(stopped_utc)s)
            RETURNING id
            """,
            {
                "version_id": version_id,
                "symbol": E2E_COMPARED_SYMBOL,
                "start_utc": E2E_COMPARED_FIRST_BAR_START_UTC,
                "stopped_utc": E2E_COMPARED_FIRST_BAR_START_UTC + timedelta(days=E2E_COMPARED_BAR_COUNT),
            },
        ).fetchone()
        assert forward_test_row is not None
        add_compared_records(connection, int(forward_test_row[0]))


async def serve_with_forward_test_worker(server: uvicorn.Server, worker: ForwardTestWorker) -> None:
    # The forward-test service of Compose runs the worker. Here it runs in the same process, with fake children.
    worker_task = asyncio.create_task(worker.keep_comparing())
    try:
        await server.serve()
    finally:
        worker_task.cancel()


def add_owner_ledger_start(database_url: str) -> None:
    """The owner ledger of "By hand" starts with 10 shares of each TEST position and the account cash, but only 5
    shares of TEST05. So the Positions table shows "Unattributed: 5" for TEST05 (section 11.7)."""
    rows = [
        (f"TEST{number:02d}", Decimal(E2E_SHORT_LEDGER_QUANTITY if number == E2E_UNATTRIBUTED_POSITION_NUMBER else 10))
        for number in range(1, E2E_POSITION_COUNT + 1)
    ]
    with psycopg.connect(database_url) as connection:
        if connection.execute("SELECT 1 FROM owner_ledger_entry LIMIT 1").fetchone() is not None:
            return
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO owner_ledger_entry (
                    owner_kind, entry_kind, time_utc, account, symbol, exchange, currency, quantity_change, price,
                    cash_change
                ) VALUES ('by_hand', 'ledger_start', %s, %s, %s, 'NASDAQ', 'USD', %s, 100, 0)
                """,
                [(FIXED_NOW_UTC, FAKE_ACCOUNT_ID, symbol, quantity) for symbol, quantity in rows],
            )
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (
                owner_kind, entry_kind, time_utc, account, currency, quantity_change, cash_change
            ) VALUES ('by_hand', 'ledger_start', %s, %s, 'USD', 0, %s)
            """,
            (FIXED_NOW_UTC, FAKE_ACCOUNT_ID, Decimal(E2E_CASH_USD)),
        )


def main() -> None:
    database_url = os.environ["ATRADE_TEST_DATABASE_URL"]
    frontend_build_dir = Path(os.environ["ATRADE_E2E_FRONTEND_BUILD_DIR"])
    port = int(os.environ["ATRADE_E2E_PORT"])
    upgrade_database(database_url)
    add_stopped_forward_tests(database_url)
    add_compared_forward_test(database_url)
    add_owner_ledger_start(database_url)
    settings = Settings(
        database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=FAKE_ACCOUNT_ID
    )
    gateway_connection = FakeGatewayConnection(
        managed_accounts=[FAKE_ACCOUNT_ID], instruments=[*SAMPLE_INSTRUMENTS, *WATCHLIST_INSTRUMENTS]
    )
    gateway_connection.account_values = make_balance_values(
        FAKE_ACCOUNT_ID, net_liquidation_usd="101234.50", cash_usd=E2E_CASH_USD
    )
    # Rule 2 of the owner ledger converts the amount of a buy order of 700 / SEHK to USD.
    gateway_connection.exchange_rates[("HKD", "USD")] = Decimal("0.128")
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
