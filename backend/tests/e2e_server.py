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

FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
LISTEN_HOST = "127.0.0.1"


def main() -> None:
    database_url = os.environ["ATRADE_TEST_DATABASE_URL"]
    frontend_build_dir = Path(os.environ["ATRADE_E2E_FRONTEND_BUILD_DIR"])
    port = int(os.environ["ATRADE_E2E_PORT"])
    upgrade_database(database_url)
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=FixedClock(FIXED_NOW_UTC))
    uvicorn.run(app, host=LISTEN_HOST, port=port, workers=1)


if __name__ == "__main__":
    main()
