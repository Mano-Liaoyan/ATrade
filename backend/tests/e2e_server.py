"""Backend server for the Playwright tests: the real app with fakes and a real PostgreSQL.

Production code has no fake mode. Playwright starts this file (frontend/playwright.config.ts).
Environment: ATRADE_TEST_DATABASE_URL, ATRADE_E2E_FRONTEND_BUILD_DIR, ATRADE_E2E_PORT.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import uvicorn

from atrade.app import create_web_app, upgrade_database
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import (
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
FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
LISTEN_HOST = "127.0.0.1"


def main() -> None:
    database_url = os.environ["ATRADE_TEST_DATABASE_URL"]
    frontend_build_dir = Path(os.environ["ATRADE_E2E_FRONTEND_BUILD_DIR"])
    port = int(os.environ["ATRADE_E2E_PORT"])
    upgrade_database(database_url)
    settings = Settings(
        database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=FAKE_ACCOUNT_ID
    )
    gateway_connection = FakeGatewayConnection(managed_accounts=[FAKE_ACCOUNT_ID])
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
    app = create_web_app(settings=settings, clock=FixedClock(FIXED_NOW_UTC), gateway_connection=gateway_connection)
    uvicorn.run(app, host=LISTEN_HOST, port=port, workers=1)


if __name__ == "__main__":
    main()
