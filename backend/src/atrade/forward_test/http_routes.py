"""HTTP routes of forward_test: start, stop, and list forward tests, and /ws/forward-tests with their actual state.

The Web process writes only `desired_state` after the start. The forward-test worker writes the actual state
(docs/architecture.md section 12.3). The socket reads the table every 2 seconds and sends the list after a change.
"""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, HTTPException, WebSocket, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import (
    NO_FREE_CLIENT_ID_MESSAGE,
    DesiredState,
    ForwardTestRequest,
    ForwardTestRow,
    ForwardTestStatus,
    InterruptionReason,
    StartRefusal,
    UniverseKind,
)
from atrade.forward_test.forward_test_universe import (
    find_calendar_quarter_start_utc,
    find_current_us_universe_quarter,
    read_us_universe_instruments,
)
from atrade.foundation.bar import BarPeriod
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.socket_push import ChangedMessageSender, HeartbeatMessage, serve_until_disconnect
from atrade.paper_trading import ManualOrderLedger, PaperAccountCheckError, PaperAccountMonitor
from atrade.strategy import StrategyVersion, read_strategy_version, read_strategy_versions
from atrade.watchlist import read_watchlist_instruments

MAX_INSTRUMENT_FIELD_LENGTH = 32
# The largest top N of a rule universe (section 12.17).
MAX_UNIVERSE_TOP_N = 500
# A multi-instrument forward test uses daily bars only (section 12.17).
MULTI_INSTRUMENT_BAR_PERIOD = BarPeriod.ONE_DAY
STATE_READ_INTERVAL_SECONDS = 2.0

# The bar periods of IB live bars (section 12.1). Every period that ATrade offers (BarPeriod) is in the list.
# https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_barsize
LIVE_BAR_PERIODS = frozenset(BarPeriod)

InstrumentField = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_INSTRUMENT_FIELD_LENGTH)
]


class UniverseBody(BaseModel):
    """`single` needs `symbol`, `exchange`, and `currency`, `rule` needs `top_n`, `list` needs nothing: the members
    are the watchlist at the start (section 12.17)."""

    kind: UniverseKind
    symbol: InstrumentField | None = None
    exchange: InstrumentField | None = None
    currency: InstrumentField | None = None
    top_n: Annotated[int, Field(ge=1, le=MAX_UNIVERSE_TOP_N)] | None = None


class StartForwardTestRequest(BaseModel):
    """The universe comes in `universe`, or for a single instrument in `symbol`, `exchange`, and `currency`."""

    strategy_version_id: int
    symbol: InstrumentField | None = None
    exchange: InstrumentField | None = None
    currency: InstrumentField | None = None
    universe: UniverseBody | None = None
    bar_period: BarPeriod
    # The capital of the forward test in USD (section 12.18). It cannot change after the start.
    allocated_capital_usd: Annotated[Decimal, Field(gt=0)]
    # Optional. The worker stops the forward test at this time (section 12.1). It cannot change after the start.
    end_time_utc: AwareDatetime | None = None

    @field_validator("bar_period")
    @classmethod
    def require_live_bar_period(cls, bar_period: BarPeriod) -> BarPeriod:
        if bar_period not in LIVE_BAR_PERIODS:
            message = f"IB live bars do not support the bar period {bar_period.value}."
            raise ValueError(message)
        return bar_period


class InterruptionResponse(BaseModel):
    reason: InterruptionReason
    started_at_utc: datetime
    ended_at_utc: datetime | None


class ForwardTestResponse(BaseModel):
    id: int
    strategy_version_id: int
    strategy_id: int
    strategy_name: str
    version_number: int
    # Null unless `universe_kind` is "single".
    symbol: str | None
    exchange: str | None
    currency: str | None
    universe_kind: UniverseKind
    # Null unless `universe_kind` is "rule".
    universe_top_n: int | None
    bar_period: BarPeriod
    desired_state: DesiredState
    status: ForwardTestStatus
    client_id: int | None
    start_balance_usd: Decimal | None
    error_message: str | None
    created_at_utc: datetime
    stopped_at_utc: datetime | None
    end_time_utc: datetime | None
    # The crashes in a row. At 3 the status is "failed" and the worker stops the restarts (section 12.7).
    crash_count: int
    interruptions: list[InterruptionResponse]
    # None for a forward test of the time before the allocated capital (section 12.18).
    allocated_capital_usd: Decimal | None


class StartRefusedResponse(BaseModel):
    """The start was refused. `unallocated_usd` is set when the allocated capital is too large (section 12.18)."""

    detail: str
    # Always None since the forward tests share the instruments (section 12.2). The field stays for the clients.
    forward_test_id: int | None = None
    unallocated_usd: Decimal | None = None


class ForwardTestCapitalResponse(BaseModel):
    """The capital of the paper account in USD (section 12.18). All 3 are None when the paper account check did not
    pass or IBKR has no NetLiquidation value in USD."""

    net_liquidation_usd: Decimal | None
    allocated_usd: Decimal | None
    unallocated_usd: Decimal | None


class ForwardTestsMessage(BaseModel):
    type: Literal["forward_tests"] = "forward_tests"
    forward_tests: list[ForwardTestResponse]


# The messages of /ws/forward-tests. The OpenAPI document adds their JSON Schema for the frontend types.
FORWARD_TEST_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [ForwardTestsMessage, HeartbeatMessage]


async def to_forward_test_response(database_url: str, row: ForwardTestRow) -> ForwardTestResponse:
    [response] = await to_forward_test_responses(database_url, [row])
    return response


async def to_forward_test_responses(database_url: str, rows: list[ForwardTestRow]) -> list[ForwardTestResponse]:
    """Reads the interruptions and the strategy versions of all rows with 2 connections, not 2 for each row.

    /ws/forward-tests reads the list every 2 seconds for each open page, so the connections of each row slowed the
    first message of a page by many seconds while other pages and backtest children used the database.
    """
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        interruptions = await forward_test_store.select_interruptions_of_forward_tests(
            connection, [row.id for row in rows]
        )
    strategy_versions = await read_strategy_versions(
        database_url=database_url, strategy_version_ids=sorted({row.strategy_version_id for row in rows})
    )
    return [build_forward_test_response(row, strategy_versions, interruptions[row.id]) for row in rows]


def build_forward_test_response(
    row: ForwardTestRow,
    strategy_versions: dict[int, StrategyVersion],
    interruptions: list[forward_test_store.ForwardTestInterruption],
) -> ForwardTestResponse:
    strategy_version = strategy_versions.get(row.strategy_version_id)
    if strategy_version is None:
        message = f"Forward test {row.id} refers to strategy version {row.strategy_version_id}, which is missing."
        raise RuntimeError(message)
    return ForwardTestResponse(
        id=row.id,
        strategy_version_id=row.strategy_version_id,
        strategy_id=strategy_version.strategy_id,
        strategy_name=strategy_version.strategy_name,
        version_number=strategy_version.version_number,
        symbol=row.symbol,
        exchange=row.exchange,
        currency=row.currency,
        universe_kind=row.universe_kind,
        universe_top_n=row.universe_top_n,
        bar_period=BarPeriod(row.bar_period),
        desired_state=row.desired_state,
        status=row.status,
        client_id=row.client_id,
        start_balance_usd=row.start_balance_usd,
        error_message=row.error_message,
        created_at_utc=row.created_at_utc,
        stopped_at_utc=row.stopped_at_utc,
        end_time_utc=row.end_time_utc,
        crash_count=row.crash_count,
        allocated_capital_usd=row.allocated_capital_usd,
        interruptions=[
            InterruptionResponse(reason=item.reason, started_at_utc=item.started_at_utc, ended_at_utc=item.ended_at_utc)
            for item in interruptions
        ],
    )


async def list_forward_tests(database_url: str) -> list[ForwardTestResponse]:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        rows = await forward_test_store.select_forward_tests(connection)
    return await to_forward_test_responses(database_url, rows)


def format_usd(amount: Decimal) -> str:
    return f"{amount:,.2f} USD"


def describe_refusal(refusal: StartRefusal, allocated_capital_usd: Decimal) -> str:
    if refusal.unallocated_usd is None:
        return NO_FREE_CLIENT_ID_MESSAGE
    return (
        f"The allocated capital {format_usd(allocated_capital_usd)} is larger than the unallocated "
        f"{format_usd(refusal.unallocated_usd)}."
    )


def refuse_start(detail: str, unallocated_usd: Decimal | None = None) -> JSONResponse:
    refused = StartRefusedResponse(detail=detail, unallocated_usd=unallocated_usd)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=refused.model_dump(mode="json"))


async def describe_forward_test(*, database_url: str, forward_test_id: int) -> str:
    """A label like "Forward test 3 (Bar count v1)" for messages."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        row = await forward_test_store.select_forward_test(connection, forward_test_id)
    if row is None:
        return f"Forward test {forward_test_id}"
    response = await to_forward_test_response(database_url, row)
    return f"Forward test {response.id} ({response.strategy_name} v{response.version_number})"


def refuse_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def read_universe_body(request: StartForwardTestRequest) -> UniverseBody:
    """The universe of the request. The flat `symbol`, `exchange`, and `currency` are a single instrument."""
    has_flat_fields = request.symbol is not None or request.exchange is not None or request.currency is not None
    if request.universe is None:
        return UniverseBody(kind="single", symbol=request.symbol, exchange=request.exchange, currency=request.currency)
    if has_flat_fields:
        raise refuse_request("Send symbol, exchange, and currency in universe or outside it, not in both.")
    return request.universe


class ForwardTestRoutes:
    """The route functions. They share the database URL, the clock, the client ID range, and the paper account."""

    def __init__(
        self, *, database_url: str, clock: Clock, client_ids: range, paper_account_monitor: PaperAccountMonitor
    ) -> None:
        self.database_url = database_url
        self.clock = clock
        self.client_ids = client_ids
        self.paper_account_monitor = paper_account_monitor
        self.ledger = ManualOrderLedger(
            paper_account_monitor=paper_account_monitor, database_url=database_url, clock=clock
        )

    async def read_net_liquidation_usd(self) -> tuple[str, Decimal] | str:
        """The checked account and its NetLiquidation in USD, or the reason why they are not known."""
        try:
            account = self.paper_account_monitor.require_checked_paper_account()
        except PaperAccountCheckError as error:
            return f"The paper account check failed: {error.check.message}"
        balance = await self.paper_account_monitor.read_balance()
        if balance is None or balance.net_liquidation_usd is None:
            reason = None if balance is None else balance.message
            message = "The paper account has no NetLiquidation value in USD."
            return message if reason is None else f"{message} {reason}"
        return account, balance.net_liquidation_usd

    async def read_capital(self) -> ForwardTestCapitalResponse:
        net_liquidation = await self.read_net_liquidation_usd()
        if isinstance(net_liquidation, str):
            return ForwardTestCapitalResponse(net_liquidation_usd=None, allocated_usd=None, unallocated_usd=None)
        _, net_liquidation_usd = net_liquidation
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            allocated_usd = await forward_test_store.select_allocated_usd(connection)
        return ForwardTestCapitalResponse(
            net_liquidation_usd=net_liquidation_usd,
            allocated_usd=allocated_usd,
            unallocated_usd=net_liquidation_usd - allocated_usd,
        )

    async def start_forward_test(self, request: StartForwardTestRequest) -> ForwardTestResponse | JSONResponse:
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=request.strategy_version_id
        )
        if strategy_version is None:
            detail = f"Strategy version {request.strategy_version_id} does not exist."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        if request.end_time_utc is not None and request.end_time_utc <= self.clock.read_now_utc():
            detail = "The end time must be later than now."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        forward_test_request = await self.make_forward_test_request(request)
        net_liquidation = await self.read_net_liquidation_usd()
        if isinstance(net_liquidation, str):
            return refuse_start(net_liquidation)
        account, net_liquidation_usd = net_liquidation
        # The allocated capital moves from the cash of "By hand", so the owner ledger must have its start.
        if await self.ledger.read_entries(account) is None:
            return refuse_start("The owner ledger has no start: the paper account has no cash value in USD yet.")
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            result = await forward_test_store.start_forward_test(
                connection,
                request=forward_test_request,
                client_ids=self.client_ids,
                created_at_utc=self.clock.read_now_utc(),
                net_liquidation_usd=net_liquidation_usd,
                account=account,
            )
        if isinstance(result, StartRefusal):
            return refuse_start(describe_refusal(result, request.allocated_capital_usd), result.unallocated_usd)
        return await to_forward_test_response(self.database_url, result)

    async def make_forward_test_request(self, request: StartForwardTestRequest) -> ForwardTestRequest:
        """The forward test request with its universe. Raises a 422 HTTPException for a wrong universe."""
        universe = read_universe_body(request)
        forward_test_request = ForwardTestRequest(
            strategy_version_id=request.strategy_version_id,
            instrument=None,
            bar_period=request.bar_period,
            allocated_capital_usd=request.allocated_capital_usd,
            end_time_utc=request.end_time_utc,
            universe_kind=universe.kind,
        )
        if universe.kind == "single":
            if universe.symbol is None or universe.exchange is None or universe.currency is None or universe.top_n:
                raise refuse_request("A single-instrument forward test needs symbol, exchange, and currency only.")
            instrument = Instrument(symbol=universe.symbol, exchange=universe.exchange, currency=universe.currency)
            return replace(forward_test_request, instrument=instrument)
        if universe.symbol is not None or universe.exchange is not None or universe.currency is not None:
            raise refuse_request(f"A {universe.kind} universe does not take symbol, exchange, or currency.")
        if request.bar_period != MULTI_INSTRUMENT_BAR_PERIOD:
            raise refuse_request("A multi-instrument forward test needs the bar period 1-DAY.")
        now_utc = self.clock.read_now_utc()
        calendar_quarter_start_utc = find_calendar_quarter_start_utc(now_utc)
        quarter_start_utc = calendar_quarter_start_utc
        if universe.kind == "rule":
            if universe.top_n is None:
                raise refuse_request("A rule universe needs top_n.")
            current_quarter_utc = await find_current_us_universe_quarter(
                database_url=self.database_url, now_utc=now_utc
            )
            if current_quarter_utc is None:
                raise refuse_request(
                    f"The US universe has no saved members for the quarter from {calendar_quarter_start_utc:%Y-%m-%d}."
                )
            quarter_start_utc = current_quarter_utc
            members = await read_us_universe_instruments(
                database_url=self.database_url, quarter_start_utc=quarter_start_utc, top_n=universe.top_n
            )
        else:
            if universe.top_n is not None:
                raise refuse_request("A list universe does not take top_n.")
            members = await read_watchlist_instruments(database_url=self.database_url)
            if not members:
                raise refuse_request("The watchlist has no instrument.")
        return replace(
            forward_test_request,
            universe_top_n=universe.top_n,
            quarter_start_utc=quarter_start_utc,
            members=tuple(members),
        )

    async def list_forward_tests(self) -> list[ForwardTestResponse]:
        return await list_forward_tests(self.database_url)

    async def stop_forward_test(self, forward_test_id: int) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            is_found = await forward_test_store.write_desired_state(
                connection, forward_test_id=forward_test_id, desired_state="stopped"
            )
        if not is_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forward test not found.")


async def push_forward_test_changes(websocket: WebSocket, database_url: str) -> None:
    sender = ChangedMessageSender(websocket)
    while True:
        await sender.send_if_changed(ForwardTestsMessage(forward_tests=await list_forward_tests(database_url)))
        await sender.wait(STATE_READ_INTERVAL_SECONDS)


def create_forward_test_router(
    *, database_url: str, clock: Clock, client_ids: range, paper_account_monitor: PaperAccountMonitor
) -> APIRouter:
    routes = ForwardTestRoutes(
        database_url=database_url, clock=clock, client_ids=client_ids, paper_account_monitor=paper_account_monitor
    )
    router = APIRouter()
    # Before /api/forward-tests/{forward_test_id} routes of the comparison router.
    router.add_api_route("/api/forward-tests/capital", routes.read_capital, methods=["GET"])
    router.add_api_route(
        "/api/forward-tests",
        routes.start_forward_test,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ForwardTestResponse,
        responses={status.HTTP_409_CONFLICT: {"model": StartRefusedResponse}},
    )
    router.add_api_route("/api/forward-tests", routes.list_forward_tests, methods=["GET"])
    router.add_api_route(
        "/api/forward-tests/{forward_test_id}/stop",
        routes.stop_forward_test,
        methods=["POST"],
        status_code=status.HTTP_202_ACCEPTED,
        response_model=None,
    )

    @router.websocket("/ws/forward-tests")
    async def stream_forward_tests(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        await serve_until_disconnect(websocket, lambda: push_forward_test_changes(websocket, database_url))

    return router
