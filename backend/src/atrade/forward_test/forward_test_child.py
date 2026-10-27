"""The body of one forward test child process: the wait for IB Gateway, the paper account check, the cancel of old
orders, the warm-up bars, the LiveNode run, and the stop steps (docs/architecture.md sections 12.5-12.7).

The child writes start_balance_usd, error_message, the status "waiting_for_gateway" and "running", and the
interruption rows of a wait for IB Gateway. The worker reads the exit code and writes the other states.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import psycopg

from atrade.backtest import find_look_back_length
from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.forward_test.forward_test_worker import (
    GATEWAY_UNREACHABLE_EXIT_CODE,
    PAPER_CHECK_FAILED_EXIT_CODE,
    ChildMode,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.clock import Clock, SystemClock
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import format_forward_test_order_tag
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.paper_trading import PaperAccountCheckError, PaperAccountMonitor, require_paper_account
from atrade.strategy import read_strategy_version

SUCCESS_EXIT_CODE = 0
FAILURE_EXIT_CODE = 1
# When IB Gateway is not reachable, the child tries again after this time (section 12.5).
GATEWAY_RETRY_SECONDS = 30.0

logger = logging.getLogger("atrade.forward_test_child")


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
    # The bars before the start that answer `request_bars` of the strategy, oldest first (section 12.15).
    warm_up_bars: tuple[Bar, ...]


# "ended": the stop request came, or the LiveNode ended by itself. "gateway_lost": the IB connection was lost for
# more than 5 minutes, and the LiveNode stopped (section 12.7).
type LiveNodeEnd = Literal["ended", "gateway_lost"]
# Runs the LiveNode until `stop_requested` is set, then stops it. It must not cancel orders or close positions.
type RunLiveNode = Callable[[LiveNodeInput, asyncio.Event], Awaitable[LiveNodeEnd]]
# Returns a new IB Gateway connection with the given client ID. The child connects it only for short steps.
type OpenGatewayConnection = Callable[[int], GatewayConnection]


@dataclass(frozen=True)
class IbkrAccess:
    """How the child reaches IB Gateway and waits for it. Tests pass fakes, a fixed clock, and a short retry time."""

    open_gateway_connection: OpenGatewayConnection
    run_live_node: RunLiveNode
    # For the interruption times that the child writes.
    clock: Clock = field(default_factory=SystemClock)
    gateway_retry_seconds: float = GATEWAY_RETRY_SECONDS


@dataclass(frozen=True)
class ChildJob:
    settings: Settings
    row: ForwardTestRow
    client_id: int
    ibkr_access: IbkrAccess


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
    warm_up_bars: tuple[Bar, ...]


async def save_start_balance(job: ChildJob, net_liquidation_usd: Decimal | None) -> Decimal | None:
    """Saves the balance at the first start and returns the saved value."""
    async with await psycopg.AsyncConnection.connect(job.settings.database_url, autocommit=True) as connection:
        if net_liquidation_usd is not None:
            await forward_test_store.write_start_balance(
                connection, forward_test_id=job.row.id, start_balance_usd=net_liquidation_usd
            )
        row = await forward_test_store.select_forward_test(connection, job.row.id)
    return None if row is None else row.start_balance_usd


async def read_warm_up_bars(job: ChildJob, gateway_connection: GatewayConnection) -> tuple[Bar, ...]:
    """The complete bars of the look-back length before now, the same length as a backtest look-back.

    `read_historical_bars` splits the range into requests of the IBKR step size of the bar period. A failed read
    gives no warm-up bars: the forward test starts, and the strategy gets an empty `request_bars` answer.
    """
    bar_period = BarPeriod(job.row.bar_period)
    end_utc = floor_to_bar_start(job.ibkr_access.clock.read_now_utc(), bar_period)
    time_range = TimeRange(start_utc=end_utc - find_look_back_length(bar_period), end_utc=end_utc)
    try:
        bars = await gateway_connection.read_historical_bars(
            forward_test_store.read_instrument(job.row), bar_period, time_range
        )
    except GatewayRequestError as error:
        logger.warning("Forward test %s: the warm-up bars were not read: %s", job.row.id, error)
        return ()
    return tuple(bars)


async def prepare_live_node_start(job: ChildJob) -> CheckedAccount | int:
    """Steps 1-3 of section 12.5 and restart step 1 of section 12.7, on one connection.

    Returns the checked account, or an exit code: GATEWAY_UNREACHABLE_EXIT_CODE means "try again later". The other
    exit codes end the child, after it wrote the reason.
    """
    gateway_connection = job.ibkr_access.open_gateway_connection(job.client_id)
    try:
        try:
            await gateway_connection.connect()
            account_id = require_paper_account(settings=job.settings, gateway_connection=gateway_connection)
            monitor = PaperAccountMonitor(settings=job.settings, gateway_connection=gateway_connection)
            balance = await monitor.read_balance()
        except GatewayRequestError as error:
            logger.warning("Forward test %s: IB Gateway is not reachable: %s", job.row.id, error)
            return GATEWAY_UNREACHABLE_EXIT_CODE
        except PaperAccountCheckError as error:
            await write_error_message(job, f"The paper account check failed: {error.check.message}")
            return PAPER_CHECK_FAILED_EXIT_CODE
        # The orders of an earlier child of this forward test can still be open. Cancel them before the start, so
        # that the strategy does not send them again (section 12.7).
        try:
            for order in await gateway_connection.read_own_open_orders():
                await gateway_connection.cancel_order_and_wait(order.order_id)
        except GatewayRequestError as error:
            await write_error_message(job, f"The open orders were not cancelled before the start: {error}")
            return FAILURE_EXIT_CODE
        warm_up_bars = await read_warm_up_bars(job, gateway_connection)
    finally:
        gateway_connection.disconnect()
    start_balance_usd = await save_start_balance(job, None if balance is None else balance.net_liquidation_usd)
    if start_balance_usd is None:
        # The equity of the records starts at the balance (section 12.8). This child sent no order.
        reason = None if balance is None else balance.message
        message = "The paper account has no NetLiquidation value in USD."
        await write_error_message(job, message if reason is None else f"{message} {reason}")
        return PAPER_CHECK_FAILED_EXIT_CODE
    return CheckedAccount(account_id=account_id, start_balance_usd=start_balance_usd, warm_up_bars=warm_up_bars)


async def write_waiting_for_gateway(job: ChildJob) -> None:
    async with await psycopg.AsyncConnection.connect(job.settings.database_url, autocommit=True) as connection:
        await forward_test_store.write_waiting_for_gateway(
            connection, forward_test_id=job.row.id, started_at_utc=job.ibkr_access.clock.read_now_utc()
        )


async def wait_until_ready(job: ChildJob, stop_requested: asyncio.Event) -> CheckedAccount | int:
    """Tries the start steps every `gateway_retry_seconds` of IbkrAccess while IB Gateway is not reachable (section 12.5).

    Returns the checked account, or an exit code. A stop request during the wait ends the wait with the stop steps.
    """
    while True:
        result = await prepare_live_node_start(job)
        if result != GATEWAY_UNREACHABLE_EXIT_CODE:
            return result
        await write_waiting_for_gateway(job)
        try:
            await asyncio.wait_for(stop_requested.wait(), job.ibkr_access.gateway_retry_seconds)
        except TimeoutError:
            continue
        return await cancel_open_orders(job)


async def cancel_open_orders(job: ChildJob) -> int:
    """Steps 2-4 of section 12.6: cancel each open order of the client ID and wait for each confirmation."""
    gateway_connection = job.ibkr_access.open_gateway_connection(job.client_id)
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
        warm_up_bars=checked_account.warm_up_bars,
    )


async def run_and_stop(job: ChildJob, stop_requested: asyncio.Event) -> int:
    checked_account = await wait_until_ready(job, stop_requested)
    if isinstance(checked_account, int):
        return checked_account
    live_node_input = await read_live_node_input(job, checked_account)
    async with await psycopg.AsyncConnection.connect(job.settings.database_url, autocommit=True) as connection:
        await forward_test_store.write_live_node_start(
            connection, forward_test_id=job.row.id, started_at_utc=job.ibkr_access.clock.read_now_utc()
        )
    live_node_end = await job.ibkr_access.run_live_node(live_node_input, stop_requested)
    if live_node_end == "gateway_lost" and not stop_requested.is_set():
        # The orders cannot be cancelled without IB Gateway. The next child cancels them before its start.
        return GATEWAY_UNREACHABLE_EXIT_CODE
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
        ibkr_access=ibkr_access,
    )
    if mode == "cancel_orders":
        return await cancel_open_orders(job)
    return await run_and_stop(job, stop_requested)
