"""Web entry point: builds the FastAPI app, runs the migrations, and starts uvicorn with 1 worker.

Run with `python -m atrade.app.web`. The Compose service `web` runs this module.
"""

import asyncio
import logging
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

import psycopg
import uvicorn
from fastapi import FastAPI
from pydantic import ValidationError

from atrade.app.access_session_routes import create_access_session_router
from atrade.app.backtest_process import BACKTEST_PROCESS_COMMAND
from atrade.app.database_migrations import upgrade_database
from atrade.app.frontend_files import create_frontend_router
from atrade.app.health_routes import create_health_router
from atrade.assistant import AssistantService, AssistantServiceClient, create_assistant_router
from atrade.backtest import BacktestRunner, create_backtest_router
from atrade.forward_test import (
    create_forward_test_comparison_router,
    create_forward_test_router,
    find_forward_test_on_instrument,
)
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection, create_ibkr_router
from atrade.market_data import ExchangeRateReader, InstrumentLookup, create_market_data_router
from atrade.paper_trading import BlockingForwardTest, PaperAccountMonitor, create_paper_trading_router
from atrade.screen import create_screen_router
from atrade.strategy import create_strategy_language_server_router, create_strategy_router
from atrade.watchlist import create_watchlist_router

# The container must accept connections from the Compose network.
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8000
# The Compose volume of PostgreSQL (deploy/compose.yaml). The start message names it.
POSTGRES_VOLUME_NAME = "atrade-postgres18-data"
PASSWORD_REFUSED_TEXT = "password authentication failed"
DATABASE_CHECK_TIMEOUT_SECONDS = 10

logger = logging.getLogger("atrade.web")


def create_blocking_forward_test_finder(
    database_url: str,
) -> Callable[[Instrument], Awaitable[BlockingForwardTest | None]]:
    """paper_trading does not import forward_test (docs/architecture.md section 6.2), so app/ connects them."""

    async def find_blocking_forward_test(instrument: Instrument) -> BlockingForwardTest | None:
        forward_test = await find_forward_test_on_instrument(database_url=database_url, instrument=instrument)
        if forward_test is None:
            return None
        return BlockingForwardTest(forward_test_id=forward_test.forward_test_id, label=forward_test.label)

    return find_blocking_forward_test


def create_web_app(
    *,
    settings: Settings,
    clock: Clock,
    gateway_connection: GatewayConnection,
    assistant_service: AssistantService | None = None,
) -> FastAPI:
    """assistant_service: the connection to the assistant service. Default: HTTP to the Compose service assistant."""
    paper_account_monitor = PaperAccountMonitor(settings=settings, gateway_connection=gateway_connection)
    backtest_runner = BacktestRunner(
        database_url=settings.database_url,
        clock=clock,
        process_command=BACKTEST_PROCESS_COMMAND,
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
    app.include_router(create_access_session_router())
    app.include_router(
        create_ibkr_router(
            gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
        )
    )
    app.include_router(
        create_paper_trading_router(
            paper_account_monitor=paper_account_monitor,
            database_url=settings.database_url,
            clock=clock,
            find_blocking_forward_test=create_blocking_forward_test_finder(settings.database_url),
        )
    )
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
    exchange_rate_reader = ExchangeRateReader(
        database_url=settings.database_url, clock=clock, gateway_connection=gateway_connection
    )
    app.include_router(
        create_backtest_router(
            database_url=settings.database_url, clock=clock, exchange_rate_reader=exchange_rate_reader
        )
    )
    app.include_router(
        create_forward_test_router(
            database_url=settings.database_url,
            clock=clock,
            client_ids=range(settings.forward_test_client_id_first, settings.forward_test_client_id_last + 1),
        )
    )
    app.include_router(create_forward_test_comparison_router(database_url=settings.database_url, clock=clock))
    instrument_lookup = InstrumentLookup(
        gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
    )
    app.include_router(create_screen_router(database_url=settings.database_url, clock=clock))
    app.include_router(
        create_watchlist_router(database_url=settings.database_url, clock=clock, instrument_lookup=instrument_lookup)
    )
    app.include_router(
        create_assistant_router(
            database_url=settings.database_url,
            clock=clock,
            assistant_service=assistant_service or AssistantServiceClient(),
        )
    )
    # The frontend router matches every path, so it is mounted last.
    app.include_router(create_frontend_router(settings.frontend_build_dir))
    return app


def check_database_password(database_url: str) -> str | None:
    """The reason when PostgreSQL refuses the password, else None. Other connection errors stop in the migrations."""
    try:
        with psycopg.connect(database_url, connect_timeout=DATABASE_CHECK_TIMEOUT_SECONDS):
            return None
    except psycopg.OperationalError as error:
        if PASSWORD_REFUSED_TEXT not in str(error):
            return None
    return (
        "PostgreSQL refused the password in ATRADE_POSTGRES_PASSWORD. PostgreSQL keeps the password of the first "
        f"start in its volume ({POSTGRES_VOLUME_NAME}), and a changed ATRADE_POSTGRES_PASSWORD does not change it. "
        "Set the first password again in .env, or see README.md section 'First start'."
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("ATrade does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    refusal = check_database_password(settings.database_url)
    if refusal is not None:
        logger.error("ATrade does not start. %s", refusal)
        sys.exit(1)
    upgrade_database(settings.database_url)
    gateway_connection = IbAsyncGatewayConnection(
        host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=settings.ibkr_web_client_id
    )
    app = create_web_app(settings=settings, clock=SystemClock(), gateway_connection=gateway_connection)
    uvicorn.run(app, host=LISTEN_HOST, port=LISTEN_PORT, workers=1)


if __name__ == "__main__":
    main()
