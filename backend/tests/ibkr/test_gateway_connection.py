"""The real ib_async connection when no IB Gateway listens: it keeps trying and reports "not connected"."""

import logging
import socket
from datetime import UTC, datetime

import anyio
import pytest

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayRequestError, IbAsyncGatewayConnection

LOCAL_HOST = "127.0.0.1"


def find_closed_local_port() -> int:
    with socket.socket() as probe:
        probe.bind((LOCAL_HOST, 0))
        port: int = probe.getsockname()[1]
    return port


@pytest.mark.anyio
async def test_keeps_trying_to_connect_while_the_gateway_is_not_reachable(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="atrade.ibkr")
    connection = IbAsyncGatewayConnection(
        host=LOCAL_HOST, port=find_closed_local_port(), client_id=1, retry_seconds=0.01
    )

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await anyio.sleep(0.2)
        assert not connection.is_connected()
        task_group.cancel_scope.cancel()

    failed_attempts = [record for record in caplog.records if "IB Gateway is not reachable" in record.getMessage()]
    assert len(failed_attempts) > 1
    assert connection.read_managed_accounts() == []


@pytest.mark.anyio
async def test_reports_a_failed_instrument_search_without_a_connection() -> None:
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=find_closed_local_port(), client_id=1)

    with pytest.raises(GatewayRequestError, match="Not connected"):
        await connection.search_instruments("AAPL")


@pytest.mark.anyio
async def test_reports_failed_historical_bars_without_a_connection() -> None:
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=find_closed_local_port(), client_id=1)
    time_range = TimeRange(datetime(2026, 3, 2, tzinfo=UTC), datetime(2026, 3, 3, tzinfo=UTC))

    with pytest.raises(GatewayRequestError, match="Not connected"):
        await connection.read_historical_bars(
            Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD"), BarPeriod.ONE_HOUR, time_range
        )


def test_refuses_client_id_0() -> None:
    with pytest.raises(ValueError, match="client ID 0"):
        IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=0)
