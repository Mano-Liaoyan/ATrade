"""The lifespan of the Web process: a background task that dies writes a log, and the shutdown still disconnects."""

import asyncio
import logging
from pathlib import Path

import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection


class DyingGatewayConnection(FakeGatewayConnection):
    async def keep_connected(self) -> None:
        message = "The connection task dies."
        raise RuntimeError(message)


@pytest.mark.anyio
async def test_a_dead_task_writes_a_log_and_the_shutdown_disconnects_the_gateway(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    gateway_connection = DyingGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    caplog.set_level(logging.ERROR)

    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)

    assert "The connection task dies." in caplog.text
    assert not gateway_connection.connected
