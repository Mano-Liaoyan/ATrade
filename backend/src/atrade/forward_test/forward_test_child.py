"""The body of one forward test child process: the paper account check, the LiveNode run, and the stop steps
(docs/architecture.md sections 12.5 and 12.6).

The child writes only start_balance_usd and error_message. The worker reads the exit code and writes the state.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal

import psycopg

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.forward_test.forward_test_worker import PAPER_CHECK_FAILED_EXIT_CODE, ChildMode
from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.paper_trading import PaperAccountCheckError, PaperAccountMonitor, require_paper_account
from atrade.strategy import read_strategy_version

SUCCESS_EXIT_CODE = 0
FAILURE_EXIT_CODE = 1


@dataclass(frozen=True)
class LiveNodeInput:
    forward_test_id: int
    client_id: int
    # The checked paper account. The IB execution client gets it as account_id (section 12.5).
    account_id: str
    # NautilusTrader writes it into each ClientOrderId, and the IB execution client into orderRef (section 12.9).
    order_id_tag: str
    instrument: Instrument
    bar_period: BarPeriod
    strategy_code: str
    gateway_host: str
    gateway_port: int
    # The recorder DataActor writes the fills and the equity points (section 12.8).
    database_url: str
    # The balance at the first start. The equity of the records starts at this value.
    start_balance_usd: Decimal


# Runs the LiveNode until `stop_requested` is set, then stops it. It must not cancel orders or close positions.
type RunLiveNode = Callable[[LiveNodeInput, asyncio.Event], Awaitable[None]]
# Returns a new IB Gateway connection with the given client ID. The child connects it only for short steps.
type OpenGatewayConnection = Callable[[int], GatewayConnection]


@dataclass(frozen=True)
class IbkrAccess:
    """The 2 ways of the child to reach IB Gateway. Tests pass fakes."""

    open_gateway_connection: OpenGatewayConnection
    run_live_node: RunLiveNode


@dataclass(frozen=True)
class ChildJob:
    settings: Settings
    row: ForwardTestRow
    client_id: int
    open_gateway_connection: OpenGatewayConnection


async def write_error_message(job: ChildJob, error_message: str) -> None:
    async with await psycopg.AsyncConnection.connect(job.settings.database_url, autocommit=True) as connection:
        await forward_test_store.write_error_message(
            connection, forward_test_id=job.row.id, error_message=error_message
        )


@dataclass(frozen=True)
class CheckedAccount:
    account_id: str
    # The first start balance of the forward test. A restart keeps it (section 12.1).
    start_balance_usd: Decimal


async def save_start_balance(job: ChildJob, net_liquidation_usd: Decimal | None) -> Decimal | None:
    """Saves the balance at the first start and returns the saved value."""
    async with await psycopg.AsyncConnection.connect(job.settings.database_url, autocommit=True) as connection:
        if net_liquidation_usd is not None:
            await forward_test_store.write_start_balance(
                connection, forward_test_id=job.row.id, start_balance_usd=net_liquidation_usd
            )
        row = await forward_test_store.select_forward_test(connection, job.row.id)
    return None if row is None else row.start_balance_usd


async def check_paper_account(job: ChildJob) -> CheckedAccount | None:
    """Steps 1-3 of section 12.5. Returns the checked account, or None after it wrote the reason of the failure."""
    gateway_connection = job.open_gateway_connection(job.client_id)
    try:
        await gateway_connection.connect()
        account_id = require_paper_account(settings=job.settings, gateway_connection=gateway_connection)
        balance = PaperAccountMonitor(settings=job.settings, gateway_connection=gateway_connection).read_balance()
    except GatewayRequestError as error:
        await write_error_message(job, f"IB Gateway is not reachable: {error}")
        return None
    except PaperAccountCheckError as error:
        await write_error_message(job, f"The paper account check failed: {error.check.message}")
        return None
    finally:
        gateway_connection.disconnect()
    start_balance_usd = await save_start_balance(job, None if balance is None else balance.net_liquidation_usd)
    if start_balance_usd is None:
        await write_error_message(job, "The paper account has no NetLiquidation value in USD.")
        return None
    return CheckedAccount(account_id=account_id, start_balance_usd=start_balance_usd)


async def cancel_open_orders(job: ChildJob) -> int:
    """Steps 2-4 of section 12.6: cancel each open order of the client ID and wait for each confirmation."""
    gateway_connection = job.open_gateway_connection(job.client_id)
    try:
        await gateway_connection.connect()
        for order in await gateway_connection.read_own_open_orders():
            await gateway_connection.cancel_order_and_wait(order.order_id)
    except GatewayRequestError as error:
        await write_error_message(job, f"The open orders were not cancelled: {error}")
        return FAILURE_EXIT_CODE
    finally:
        gateway_connection.disconnect()
    return SUCCESS_EXIT_CODE


async def read_live_node_input(job: ChildJob, checked_account: CheckedAccount) -> LiveNodeInput:
    strategy_version = await read_strategy_version(
        database_url=job.settings.database_url, strategy_version_id=job.row.strategy_version_id
    )
    if strategy_version is None:
        message = f"Strategy version {job.row.strategy_version_id} does not exist."
        raise LookupError(message)
    return LiveNodeInput(
        forward_test_id=job.row.id,
        client_id=job.client_id,
        account_id=checked_account.account_id,
        order_id_tag=format_forward_test_order_tag(job.row.id),
        instrument=forward_test_store.read_instrument(job.row),
        bar_period=BarPeriod(job.row.bar_period),
        strategy_code=strategy_version.code,
        gateway_host=job.settings.ibkr_host,
        gateway_port=job.settings.ibkr_paper_port,
        database_url=job.settings.database_url,
        start_balance_usd=checked_account.start_balance_usd,
    )


async def run_and_stop(job: ChildJob, run_live_node: RunLiveNode, stop_requested: asyncio.Event) -> int:
    checked_account = await check_paper_account(job)
    if checked_account is None:
        return PAPER_CHECK_FAILED_EXIT_CODE
    await run_live_node(await read_live_node_input(job, checked_account), stop_requested)
    if not stop_requested.is_set():
        await write_error_message(job, "The LiveNode stopped without a stop request.")
        return FAILURE_EXIT_CODE
    return await cancel_open_orders(job)


async def run_forward_test_child(
    *,
    settings: Settings,
    forward_test_id: int,
    mode: ChildMode,
    ibkr_access: IbkrAccess,
    stop_requested: asyncio.Event,
) -> int:
    """Returns the exit code of the child process. An exception of the strategy or the LiveNode ends the child."""
    async with await psycopg.AsyncConnection.connect(settings.database_url) as connection:
        row = await forward_test_store.select_forward_test(connection, forward_test_id)
    if row is None or row.client_id is None:
        return FAILURE_EXIT_CODE
    job = ChildJob(
        settings=settings,
        row=row,
        client_id=row.client_id,
        open_gateway_connection=ibkr_access.open_gateway_connection,
    )
    if mode == "cancel_orders":
        return await cancel_open_orders(job)
    return await run_and_stop(job, ibkr_access.run_live_node, stop_requested)
