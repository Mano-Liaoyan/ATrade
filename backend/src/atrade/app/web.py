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

from atrade.app.database_migrations import upgrade_database
from atrade.app.frontend_files import create_frontend_router
from atrade.app.health_routes import create_health_router
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection, create_ibkr_router
from atrade.market_data import create_market_data_router

# The container must accept connections from the Compose network.
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8000

logger = logging.getLogger("atrade.web")


def create_web_app(*, settings: Settings, clock: Clock, gateway_connection: GatewayConnection) -> FastAPI:
    @asynccontextmanager
    async def keep_gateway_connected(_app: FastAPI) -> AsyncGenerator[None]:
        # The Web process starts without IB Gateway. The connection task connects again after each loss.
        connection_task = asyncio.create_task(gateway_connection.keep_connected())
        yield
        connection_task.cancel()
        with suppress(asyncio.CancelledError):
            await connection_task
        gateway_connection.disconnect()

    app = FastAPI(title="ATrade", lifespan=keep_gateway_connected)
    app.include_router(create_health_router(database_url=settings.database_url, clock=clock))
    app.include_router(
        create_ibkr_router(
            gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
        )
    )
    app.include_router(
        create_market_data_router(
            gateway_connection=gateway_connection, host=settings.ibkr_host, port=settings.ibkr_paper_port
        )
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
