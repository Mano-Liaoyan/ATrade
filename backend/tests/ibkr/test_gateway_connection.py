"""The real ib_async connection when no IB Gateway listens: it keeps trying and reports "not connected"."""

import logging
import socket

import anyio
import pytest

from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayRequestError, IbAsyncGatewayConnection, OrderRequest

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
async def test_sends_reads_and_cancels_no_order_without_a_connection() -> None:
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=find_closed_local_port(), client_id=1)
    order_request = OrderRequest(
        account="DU1234567",
        instrument=Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD"),
        side="BUY",
        quantity=1,
        order_type="MKT",
        limit_price=None,
        time_in_force="DAY",
        order_ref="ATRADE-BY-HAND",
    )

    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.place_order(order_request)
    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.read_open_orders()
    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.cancel_order(1)


def test_refuses_client_id_0() -> None:
    with pytest.raises(ValueError, match="client ID 0"):
        IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=0)
