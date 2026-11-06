"""The real ib_async connection when no IB Gateway listens: it keeps trying and reports "not connected". Also the
IBKR link: IB Gateway accepts the API connection, but it has no connection to the IBKR servers."""

import asyncio
import logging
import socket
from contextlib import aclosing
from datetime import UTC, datetime

import anyio
import pytest
from ib_async import BarData, BarDataList, OrderStatus, RequestError

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayRequestError, IbAsyncGatewayConnection, OrderRequest
from atrade.ibkr import gateway_connection as gateway_connection_module
from atrade.market_data import LiveDailyBarHub

LOCAL_HOST = "127.0.0.1"
AAPL = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
AAPL_ORDER = OrderRequest(
    account="DU1234567",
    instrument=AAPL,
    side="BUY",
    quantity=1,
    order_type="MKT",
    limit_price=None,
    time_in_force="DAY",
    order_ref="ATRADE-BY-HAND",
)
ONE_DAY_RANGE = TimeRange(datetime(2026, 3, 2, tzinfo=UTC), datetime(2026, 3, 3, tzinfo=UTC))
# The tests make each historical data timeout this short.
SHORT_TIMEOUT_SECONDS = 0.05
SHORT_CHECK_SECONDS = 0.01
STREAM_END_WAIT_SECONDS = 2


def find_closed_local_port() -> int:
    with socket.socket() as probe:
        probe.bind((LOCAL_HOST, 0))
        port: int = probe.getsockname()[1]
    return port


@pytest.mark.anyio
async def test_a_silent_gateway_ends_the_exchange_rate_read_with_a_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def never_answer(*_contracts: object) -> list[object]:
        await anyio.sleep_forever()
        return []

    monkeypatch.setattr(gateway_connection_module, "CONTRACT_REQUEST_TIMEOUT_SECONDS", SHORT_TIMEOUT_SECONDS)
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=1)
    monkeypatch.setattr(connection.ib, "isConnected", lambda: True)
    monkeypatch.setattr(connection.ib, "qualifyContractsAsync", never_answer)

    with anyio.fail_after(STREAM_END_WAIT_SECONDS), pytest.raises(GatewayRequestError, match="HKDUSD"):
        await connection.read_exchange_rate("HKD", "USD")


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

    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.place_order(AAPL_ORDER)
    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.read_open_orders()
    with pytest.raises(GatewayRequestError, match="not connected"):
        await connection.cancel_order(1)


def ignore_message(*_args: object) -> None:
    pass


def make_connected_order_connection(monkeypatch: pytest.MonkeyPatch, order_id: int) -> IbAsyncGatewayConnection:
    """The real ib_async order state: the client only records the placeOrder message, and no IB Gateway answers."""
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=1)
    monkeypatch.setattr(connection.ib, "isConnected", lambda: True)
    monkeypatch.setattr(connection.ib.client, "getReqId", lambda: order_id)
    monkeypatch.setattr(connection.ib.client, "placeOrder", ignore_message)
    monkeypatch.setattr(gateway_connection_module, "ORDER_ANSWER_TIMEOUT_SECONDS", SHORT_TIMEOUT_SECONDS)
    monkeypatch.setattr(gateway_connection_module, "ORDER_ANSWER_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    return connection


@pytest.mark.anyio
async def test_place_order_and_wait_raises_the_ibkr_message_of_a_rejected_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = make_connected_order_connection(monkeypatch, 1042)
    asyncio.get_running_loop().call_soon(connection.ib.wrapper.error, 1042, 201, "Order rejected - reason: margin", "")

    with pytest.raises(GatewayRequestError, match="Order rejected - reason: margin"):
        await connection.place_order_and_wait(AAPL_ORDER)


@pytest.mark.anyio
async def test_place_order_and_wait_raises_when_ibkr_makes_the_order_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connected_order_connection(monkeypatch, 1046)

    def make_order_inactive() -> None:
        connection.ib.trades()[0].orderStatus.status = OrderStatus.Inactive

    asyncio.get_running_loop().call_soon(make_order_inactive)

    with pytest.raises(GatewayRequestError, match="Order 1046 has the status Inactive"):
        await connection.place_order_and_wait(AAPL_ORDER)


IBKR_WARNING_CODE = 399


@pytest.mark.anyio
async def test_place_order_and_wait_reports_a_rejection_after_an_ibkr_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connected_order_connection(monkeypatch, 1047)
    event_loop = asyncio.get_running_loop()
    event_loop.call_soon(connection.ib.wrapper.error, 1047, IBKR_WARNING_CODE, "The order is outside hours", "")
    event_loop.call_later(
        SHORT_TIMEOUT_SECONDS / 2, connection.ib.wrapper.error, 1047, 201, "Order rejected - reason: margin", ""
    )

    with pytest.raises(GatewayRequestError, match="Order rejected - reason: margin"):
        await connection.place_order_and_wait(AAPL_ORDER)


@pytest.mark.anyio
async def test_place_order_and_wait_returns_the_id_after_an_ibkr_warning_without_a_later_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = make_connected_order_connection(monkeypatch, 1048)
    asyncio.get_running_loop().call_soon(
        connection.ib.wrapper.error, 1048, IBKR_WARNING_CODE, "The order is outside hours", ""
    )

    assert await connection.place_order_and_wait(AAPL_ORDER) == 1048


@pytest.mark.anyio
async def test_place_order_and_wait_returns_the_id_when_ibkr_accepts_the_order(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connected_order_connection(monkeypatch, 1043)

    def accept_order() -> None:
        connection.ib.trades()[0].orderStatus.status = OrderStatus.Submitted

    asyncio.get_running_loop().call_soon(accept_order)

    assert await connection.place_order_and_wait(AAPL_ORDER) == 1043


@pytest.mark.anyio
async def test_place_order_and_wait_returns_the_id_when_ibkr_does_not_answer_in_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = make_connected_order_connection(monkeypatch, 1044)

    assert await connection.place_order_and_wait(AAPL_ORDER) == 1044


@pytest.mark.anyio
async def test_place_order_does_not_wait_for_the_answer_of_ibkr(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connected_order_connection(monkeypatch, 1045)
    monkeypatch.setattr(gateway_connection_module, "ORDER_ANSWER_TIMEOUT_SECONDS", 60.0)

    with anyio.fail_after(SHORT_TIMEOUT_SECONDS * 10):
        assert await connection.place_order(AAPL_ORDER) == 1045


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


@pytest.mark.anyio
async def test_reports_connected_only_after_the_startup_synchronization(monkeypatch: pytest.MonkeyPatch) -> None:
    # ib_async reports the API as ready before connectAsync has read the accounts, the orders and the balance.
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=1)
    api_ready = anyio.Event()
    synchronization_done = anyio.Event()

    async def connect_and_synchronize(*_args: object, **_kwargs: object) -> None:
        monkeypatch.setattr(connection.ib, "isConnected", lambda: True)
        api_ready.set()
        await synchronization_done.wait()

    monkeypatch.setattr(connection.ib, "connectAsync", connect_and_synchronize)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.try_to_connect)
        await api_ready.wait()
        assert not connection.is_connected()
        assert connection.read_connection_number() == 0
        synchronization_done.set()
        with anyio.fail_after(1):
            while not connection.is_connected():
                await anyio.sleep(0.01)
        assert connection.read_connection_number() == 1


@pytest.mark.anyio
async def test_a_request_error_in_the_startup_synchronization_is_a_failed_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # connectAsync reads the executions without return_exceptions, so a RequestError of IBKR leaves it.
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=1)

    async def fail_synchronization(*_args: object, **_kwargs: object) -> None:
        raise RequestError(1, 162, "Historical market data Service error message")

    monkeypatch.setattr(connection.ib, "connectAsync", fail_synchronization)

    await connection.try_to_connect()
    with pytest.raises(GatewayRequestError):
        await connection.connect()

    assert connection.read_status() == "unreachable"


class HistoricalDataGateway:
    """Replaces reqHistoricalDataAsync. `answers` false: each request waits for its timeout, then ib_async returns an
    empty list, like IB Gateway without a connection to IBKR."""

    def __init__(self) -> None:
        self.answers = True
        self.request_count = 0

    async def request(self, *_args: object, timeout: float, **_kwargs: object) -> list[object]:
        self.request_count += 1
        if not self.answers:
            await anyio.sleep(timeout)
        return []


def make_connected_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[IbAsyncGatewayConnection, HistoricalDataGateway]:
    monkeypatch.setattr(gateway_connection_module, "HISTORICAL_DATA_TIMEOUT_SECONDS", SHORT_TIMEOUT_SECONDS)
    monkeypatch.setattr(gateway_connection_module, "IBKR_LINK_CHECK_TIMEOUT_SECONDS", SHORT_TIMEOUT_SECONDS)
    connection = IbAsyncGatewayConnection(host=LOCAL_HOST, port=4004, client_id=1)
    historical_data_gateway = HistoricalDataGateway()
    monkeypatch.setattr(connection.ib, "isConnected", lambda: True)
    monkeypatch.setattr(connection.ib, "reqHistoricalDataAsync", historical_data_gateway.request)
    connection.synchronized = True
    return connection, historical_data_gateway


def test_reports_no_ibkr_connection_between_the_lost_and_the_restored_message(monkeypatch: pytest.MonkeyPatch) -> None:
    connection, _ = make_connected_connection(monkeypatch)
    assert connection.read_status() == "connected"

    connection.receive_error(-1, 1100, "Connectivity between IBKR and Trader Workstation has been lost.", None)

    assert connection.read_status() == "no_ibkr_connection"
    assert not connection.is_connected()

    connection.receive_error(-1, 1102, "Connectivity between IBKR and Trader Workstation has been restored.", None)

    assert connection.read_status() == "connected"


@pytest.mark.anyio
async def test_fails_at_once_after_a_historical_data_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    connection, historical_data_gateway = make_connected_connection(monkeypatch)
    historical_data_gateway.answers = False

    with pytest.raises(GatewayRequestError, match="in time"):
        await connection.read_historical_bars(AAPL, BarPeriod.ONE_DAY, ONE_DAY_RANGE)
    assert connection.read_status() == "no_ibkr_connection"

    with pytest.raises(GatewayRequestError, match="no connection to IBKR"):
        await connection.read_historical_bars(AAPL, BarPeriod.ONE_DAY, ONE_DAY_RANGE)
    assert historical_data_gateway.request_count == 1


class LiveBarGateway:
    """Replaces the keepUpToDate request. `answers` false: the request waits for its timeout. Then ib_async cancels it,
    keeps its subscriber, and returns an empty list."""

    def __init__(self) -> None:
        self.answers = True
        self.bars_data = BarDataList()
        self.cancel_count = 0

    async def request(self, *_args: object, timeout: float, **_kwargs: object) -> BarDataList:
        if self.answers:
            self.bars_data.append(BarData(date=ONE_DAY_RANGE.start_utc, open=1.0, high=2.0, low=1.0, close=2.0))
        else:
            await anyio.sleep(timeout)
        return self.bars_data

    def cancel(self, _bars_data: BarDataList) -> None:
        self.cancel_count += 1


def make_live_bar_connection(monkeypatch: pytest.MonkeyPatch) -> tuple[IbAsyncGatewayConnection, LiveBarGateway]:
    connection, _historical_data_gateway = make_connected_connection(monkeypatch)
    monkeypatch.setattr(gateway_connection_module, "LIVE_BAR_CONNECTION_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    live_bar_gateway = LiveBarGateway()
    monkeypatch.setattr(connection.ib, "reqHistoricalDataAsync", live_bar_gateway.request)
    monkeypatch.setattr(connection.ib, "cancelHistoricalData", live_bar_gateway.cancel)
    return connection, live_bar_gateway


async def read_live_bars_until_end(connection: IbAsyncGatewayConnection, *, is_losing_the_link: bool = False) -> None:
    with anyio.fail_after(STREAM_END_WAIT_SECONDS):
        async with aclosing(connection.stream_live_bars(AAPL, BarPeriod.ONE_DAY)) as live_bars:
            async for _bar in live_bars:
                if is_losing_the_link:
                    connection.mark_ibkr_link_lost("test")


@pytest.mark.anyio
async def test_a_timed_out_live_bar_subscription_raises_and_keeps_the_ibkr_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, live_bar_gateway = make_live_bar_connection(monkeypatch)
    live_bar_gateway.answers = False

    with pytest.raises(GatewayRequestError, match="in time"):
        await read_live_bars_until_end(connection)

    assert connection.read_status() == "connected"
    assert live_bar_gateway.cancel_count == 1


@pytest.mark.anyio
async def test_a_lost_ibkr_link_ends_the_live_bar_stream_and_its_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    connection, live_bar_gateway = make_live_bar_connection(monkeypatch)

    with pytest.raises(GatewayRequestError, match="no connection to IBKR"):
        await read_live_bars_until_end(connection, is_losing_the_link=True)

    assert live_bar_gateway.cancel_count == 1


@pytest.mark.anyio
async def test_the_hub_gets_a_live_bar_again_after_a_silent_subscription_and_a_lost_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, live_bar_gateway = make_live_bar_connection(monkeypatch)
    live_bar_gateway.answers = False
    hub = LiveDailyBarHub(connection, retry_delay_seconds=SHORT_CHECK_SECONDS)

    async def wait_for_live_bar(*, is_there: bool) -> None:
        with anyio.fail_after(STREAM_END_WAIT_SECONDS):
            while (hub.read_bar(AAPL) is not None) != is_there:
                await anyio.sleep(SHORT_CHECK_SECONDS)

    with hub.listen() as listener:
        listener.follow([AAPL])
        await anyio.sleep(SHORT_TIMEOUT_SECONDS * 2)
        assert hub.read_bar(AAPL) is None

        live_bar_gateway.answers = True
        await wait_for_live_bar(is_there=True)

        connection.mark_ibkr_link_lost("test")
        await wait_for_live_bar(is_there=False)

        connection.mark_ibkr_link_restored()
        await wait_for_live_bar(is_there=True)
        hub.stop()


@pytest.mark.anyio
async def test_a_request_after_the_retry_wait_finds_the_link_that_came_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gateway_connection_module, "IBKR_LINK_CHECK_WHILE_LOST_SECONDS", 0.0)
    connection, historical_data_gateway = make_connected_connection(monkeypatch)
    connection.receive_error(-1, 2110, "Connectivity between Trader Workstation and server is broken.", None)

    await connection.read_historical_bars(AAPL, BarPeriod.ONE_DAY, ONE_DAY_RANGE)

    assert historical_data_gateway.request_count == 1
    assert connection.read_status() == "connected"


@pytest.mark.anyio
async def test_the_ibkr_link_check_marks_the_link_lost_and_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    connection, historical_data_gateway = make_connected_connection(monkeypatch)
    historical_data_gateway.answers = False

    await connection.check_ibkr_link()

    assert connection.read_status() == "no_ibkr_connection"

    historical_data_gateway.answers = True
    await connection.check_ibkr_link()

    assert connection.read_status() == "connected"
