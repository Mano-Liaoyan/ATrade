"""Web entry point: builds the FastAPI app, runs the migrations, and starts uvicorn with 1 worker.

Run with `python -m atrade.app.web`. The Compose service `web` runs this module.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from pydantic import ValidationError

from atrade.app.backtest_process import BACKTEST_PROCESS_COMMAND
from atrade.app.database_migrations import upgrade_database
from atrade.app.frontend_files import create_frontend_router
from atrade.app.health_routes import create_health_router
from atrade.backtest import BacktestRunner, create_backtest_router
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection, create_ibkr_router
from atrade.market_data import InstrumentLookup, create_market_data_router
from atrade.paper_trading import PaperAccountMonitor, create_paper_trading_router
from atrade.strategy import create_strategy_language_server_router, create_strategy_router
from atrade.watchlist import create_watchlist_router

# The container must accept connections from the Compose network.
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8000

# Defaults of docs/architecture.md section 10. Issue #71 stores them in PostgreSQL and lets the user change them.
BACKTEST_TIMEOUT_SECONDS = 120 * 60
BACKTEST_CONCURRENCY = 1

logger = logging.getLogger("atrade.web")


def create_web_app(*, settings: Settings, clock: Clock, gateway_connection: GatewayConnection) -> FastAPI:
    paper_account_monitor = PaperAccountMonitor(settings=settings, gateway_connection=gateway_connection)
    backtest_runner = BacktestRunner(
        database_url=settings.database_url,
        clock=clock,
        process_command=BACKTEST_PROCESS_COMMAND,
        timeout_seconds=BACKTEST_TIMEOUT_SECONDS,
        concurrency=BACKTEST_CONCURRENCY,
    )

    @asynccontextmanager
    async def keep_gateway_connected(_app: FastAPI) -> AsyncGenerator[None]:
        # The Web process starts without IB Gateway. The connection task connects again after each loss.
        connection_task = asyncio.create_task(gateway_connection.keep_connected())
        # The paper account check runs after each connection, also when no browser is open.
        check_task = asyncio.create_task(paper_account_monitor.keep_checking())
        backtest_task = asyncio.create_task(backtest_runner.keep_running())
        yield
        for task in (backtest_task, check_task, connection_task):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        gateway_connection.disconnect()

    app = FastAPI(title="ATrade", lifespan=keep_gateway_connected)
    app.include_router(create_health_router(database_url=settings.database_url, clock=clock))
    app.include_router(
        create_ibkr_router(
            gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
        )
    )
    app.include_router(create_paper_trading_router(paper_account_monitor=paper_account_monitor))
    app.include_router(
        create_market_data_router(
            gateway_connection=gateway_connection,
            host=settings.ibkr_host,
            port=settings.ibkr_paper_port,
            database_url=settings.database_url,
            clock=clock,
        )
    )
    app.include_router(create_strategy_router(database_url=settings.database_url, clock=clock))
    app.include_router(create_strategy_language_server_router())
    app.include_router(create_backtest_router(database_url=settings.database_url, clock=clock))
    instrument_lookup = InstrumentLookup(
        gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
    )
    app.include_router(
        create_watchlist_router(database_url=settings.database_url, clock=clock, instrument_lookup=instrument_lookup)
    )
    # The frontend router matches every path, so it is mounted last.
    app.include_router(create_frontend_router(settings.frontend_build_dir))
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("ATrade does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    upgrade_database(settings.database_url)
    gateway_connection = IbAsyncGatewayConnection(
        host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=settings.ibkr_web_client_id
    )
    app = create_web_app(settings=settings, clock=SystemClock(), gateway_connection=gateway_connection)
    uvicorn.run(app, host=LISTEN_HOST, port=LISTEN_PORT, workers=1)


if __name__ == "__main__":
    main()
