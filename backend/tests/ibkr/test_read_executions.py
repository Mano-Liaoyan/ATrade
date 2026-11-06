"""`read_executions` on the real ib_async wrapper (docs/architecture/ibkr.md section on the order functions).

The fake connection returns finished `Execution` values, so it cannot show how the wrapper handles a fill. These tests
replace only the socket: IB Gateway messages go into the real `ib_async` wrapper.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ib_async import CommissionReport, Contract, Stock
from ib_async import Execution as IbExecution

from atrade.ibkr import gateway_connection as gateway_connection_module
from atrade.ibkr.gateway_connection import IbAsyncGatewayConnection

EXECUTION_ID = "0000e0d5.1"
LIVE_MESSAGE_REQUEST_ID = -1
# IBKR sends the contract of the execution: the exchange is the venue, and the primary exchange is not set.
EXECUTION_CONTRACT = Stock("AAPL", "ISLAND", "USD")
ORDER_REF = "O-20260102-030405-001-FT7-1"


def make_ib_execution() -> IbExecution:
    return IbExecution(
        execId=EXECUTION_ID,
        time=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        acctNumber="DU1234567",
        side="BOT",
        shares=10.0,
        price=20.5,
        orderId=8,
        clientId=10,
        orderRef=ORDER_REF,
    )


class GatewayMessages:
    """Takes the place of the IB Gateway socket and sends its messages to the real wrapper."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.connection = IbAsyncGatewayConnection(host="127.0.0.1", port=1, client_id=10)
        self.wrapper = self.connection.ib.wrapper
        self.contract: Contract = EXECUTION_CONTRACT
        monkeypatch.setattr(self.connection.ib.client, "isReady", lambda: True)
        monkeypatch.setattr(self.connection.ib.client, "reqExecutions", self.answer_executions_request)

    def send_live_execution(self) -> None:
        self.wrapper.execDetails(LIVE_MESSAGE_REQUEST_ID, self.contract, make_ib_execution())

    def send_commission_report(self, commission: float) -> None:
        self.wrapper.commissionReport(CommissionReport(execId=EXECUTION_ID, commission=commission, currency="USD"))

    def answer_executions_request(self, request_id: int, _execution_filter: object) -> None:
        self.wrapper.execDetails(request_id, self.contract, make_ib_execution())
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
