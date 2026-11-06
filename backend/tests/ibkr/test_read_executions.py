"""`read_executions` on the real ib_async wrapper (docs/architecture/ibkr.md section on the order functions).

The fake connection returns finished `Execution` values, so it cannot show how the wrapper handles a fill. These tests
replace only the socket: IB Gateway messages go into the real `ib_async` wrapper.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ib_async import CommissionReport, Contract, Stock
from ib_async import Execution as IbExecution

from atrade.ibkr import gateway_connection as gateway_connection_module
from atrade.ibkr.gateway_connection import COMMISSION_REPORT_LIMIT, IbAsyncGatewayConnection

EXECUTION_ID = "0000e0d5.1"
LIVE_MESSAGE_REQUEST_ID = -1
# IBKR sends the contract of the execution: the exchange is the venue, and the primary exchange is not set.
EXECUTION_CONTRACT = Stock("AAPL", "ISLAND", "USD")
ORDER_REF = "O-20260102-030405-001-FT7-1"


def make_ib_execution(*, order_id: int = 8, client_id: int = 10, age: timedelta = timedelta(0)) -> IbExecution:
    return IbExecution(
        execId=EXECUTION_ID,
        time=datetime.now(UTC) - age,
        acctNumber="DU1234567",
        side="BOT",
        shares=10.0,
        price=20.5,
        orderId=order_id,
        clientId=client_id,
        orderRef=ORDER_REF,
    )


class GatewayMessages:
    """Takes the place of the IB Gateway socket and sends its messages to the real wrapper."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.connection = IbAsyncGatewayConnection(host="127.0.0.1", port=1, client_id=10)
        self.wrapper = self.connection.ib.wrapper
        self.contract: Contract = EXECUTION_CONTRACT
        self.execution = make_ib_execution()
        monkeypatch.setattr(self.connection.ib.client, "isReady", lambda: True)
        monkeypatch.setattr(self.connection.ib.client, "reqExecutions", self.answer_executions_request)

    def send_live_execution(self) -> None:
        self.wrapper.execDetails(LIVE_MESSAGE_REQUEST_ID, self.contract, self.execution)

    def send_commission_report(self, commission: float) -> None:
        self.wrapper.commissionReport(CommissionReport(execId=EXECUTION_ID, commission=commission, currency="USD"))

    def answer_executions_request(self, request_id: int, _execution_filter: object) -> None:
        self.wrapper.execDetails(request_id, self.contract, self.execution)
        self.wrapper.execDetailsEnd(request_id)


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> GatewayMessages:
    monkeypatch.setattr(gateway_connection_module, "COMMISSION_REPORT_WAIT_SECONDS", 0.05)
    return GatewayMessages(monkeypatch)


@pytest.mark.anyio
async def test_reads_the_commission_of_a_fill_that_the_connection_saw_live(gateway: GatewayMessages) -> None:
    gateway.send_live_execution()
    gateway.send_commission_report(1.25)

    [execution] = await gateway.connection.read_executions()

    assert execution.commission == Decimal("1.25")


@pytest.mark.anyio
async def test_holds_a_fill_until_its_commission_report_arrives(gateway: GatewayMessages) -> None:
    gateway.send_live_execution()

    held = await gateway.connection.read_executions()
    gateway.send_commission_report(1.25)
    released = await gateway.connection.read_executions()

    assert held == []
    assert [execution.commission for execution in released] == [Decimal("1.25")]


@pytest.mark.anyio
async def test_a_held_fill_gets_one_warning_and_stops_the_wait_of_later_reads(
    gateway: GatewayMessages, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    gateway.send_live_execution()
    await gateway.connection.read_executions()
    caplog.clear()
    monkeypatch.setattr(gateway_connection_module, "COMMISSION_REPORT_WAIT_SECONDS", 60.0)

    with caplog.at_level(logging.WARNING, logger="atrade.ibkr"):
        async with asyncio.timeout(1):
            await gateway.connection.read_executions()
            await gateway.connection.read_executions()

    assert caplog.messages == []
    gateway.send_commission_report(1.25)
    assert len(await gateway.connection.read_executions()) == 1


@pytest.mark.anyio
async def test_the_warning_of_a_held_fill_names_the_execution(
    gateway: GatewayMessages, caplog: pytest.LogCaptureFixture
) -> None:
    gateway.send_live_execution()

    with caplog.at_level(logging.WARNING, logger="atrade.ibkr"):
        await gateway.connection.read_executions()

    [message] = caplog.messages
    assert EXECUTION_ID in message


@pytest.mark.anyio
async def test_a_read_with_held_fills_returns_them_with_their_state(gateway: GatewayMessages) -> None:
    gateway.send_live_execution()

    [execution] = await gateway.connection.read_executions(include_held=True)

    assert execution.execution_id == EXECUTION_ID
    assert execution.is_held


@pytest.mark.anyio
async def test_a_held_fill_at_the_limit_comes_with_commission_0_and_one_warning(
    gateway: GatewayMessages, caplog: pytest.LogCaptureFixture
) -> None:
    gateway.execution = make_ib_execution(age=COMMISSION_REPORT_LIMIT)

    with caplog.at_level(logging.WARNING, logger="atrade.ibkr"):
        [execution] = await gateway.connection.read_executions()
        await gateway.connection.read_executions()

    assert (execution.commission, execution.is_held) == (0, False)
    assert len([message for message in caplog.messages if "commission 0" in message]) == 1


@pytest.mark.anyio
async def test_the_limit_also_counts_from_the_first_wait_when_the_execution_time_is_wrong(
    gateway: GatewayMessages, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A time without a zone: ib_async reads it as local time, so the time can be hours after now.
    gateway.execution = make_ib_execution(age=timedelta(hours=-5))
    monkeypatch.setattr(gateway_connection_module, "COMMISSION_REPORT_LIMIT", timedelta(milliseconds=100))

    held = await gateway.connection.read_executions()
    await asyncio.sleep(0.15)
    released = await gateway.connection.read_executions()

    assert held == []
    assert [execution.execution_id for execution in released] == [EXECUTION_ID]


@pytest.mark.anyio
async def test_a_report_with_commission_0_releases_the_fill(gateway: GatewayMessages) -> None:
    gateway.send_live_execution()
    gateway.send_commission_report(0.0)

    [execution] = await gateway.connection.read_executions()

    assert execution.commission == 0


@pytest.mark.anyio
async def test_a_new_connection_waits_for_the_reports_that_follow_the_executions(gateway: GatewayMessages) -> None:
    asyncio.get_running_loop().call_later(0.01, gateway.send_commission_report, 1.25)

    [execution] = await gateway.connection.read_executions()

    assert execution.commission == Decimal("1.25")


@pytest.mark.anyio
async def test_an_execution_has_the_order_ref_and_the_contract(gateway: GatewayMessages) -> None:
    gateway.send_live_execution()
    gateway.send_commission_report(1.25)

    [execution] = await gateway.connection.read_executions()

    assert (execution.order_ref, execution.symbol, execution.currency) == (ORDER_REF, "AAPL", "USD")
