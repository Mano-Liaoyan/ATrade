"""HTTP routes of forward_test: start, stop, and list forward tests, and /ws/forward-tests with their actual state.

The Web process writes only `desired_state` after the start. The forward-test worker writes the actual state
(docs/architecture.md section 12.3). The socket reads the table every 2 seconds and sends the list after a change.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, HTTPException, WebSocket, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, StringConstraints, field_validator

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import (
    NO_FREE_CLIENT_ID_MESSAGE,
    DesiredState,
    ForwardTestRequest,
    ForwardTestRow,
    ForwardTestStatus,
    InterruptionReason,
    StartRefusal,
)
from atrade.foundation.bar import BarPeriod
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.socket_push import ChangedMessageSender, HeartbeatMessage, serve_until_disconnect
from atrade.strategy import read_strategy_version

MAX_INSTRUMENT_FIELD_LENGTH = 32
STATE_READ_INTERVAL_SECONDS = 2.0

# The bar periods of IB live bars (section 12.1). Every period that ATrade offers (BarPeriod) is in the list.
# https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_barsize
LIVE_BAR_PERIODS = frozenset(BarPeriod)

InstrumentField = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_INSTRUMENT_FIELD_LENGTH)
]


class StartForwardTestRequest(BaseModel):
    strategy_version_id: int
    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    bar_period: BarPeriod
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
    symbol: str
    exchange: str
    currency: str
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


class StartRefusedResponse(BaseModel):
    """The start was refused. `forward_test_id` is the forward test that already runs on the instrument."""

    detail: str
    forward_test_id: int | None


class ForwardTestsMessage(BaseModel):
    type: Literal["forward_tests"] = "forward_tests"
    forward_tests: list[ForwardTestResponse]


# The messages of /ws/forward-tests. The OpenAPI document adds their JSON Schema for the frontend types.
FORWARD_TEST_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [ForwardTestsMessage, HeartbeatMessage]


async def to_forward_test_response(database_url: str, row: ForwardTestRow) -> ForwardTestResponse:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        interruptions = await forward_test_store.select_interruptions(connection, row.id)
    strategy_version = await read_strategy_version(
        database_url=database_url, strategy_version_id=row.strategy_version_id
    )
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
        interruptions=[
            InterruptionResponse(reason=item.reason, started_at_utc=item.started_at_utc, ended_at_utc=item.ended_at_utc)
            for item in interruptions
        ],
    )


async def list_forward_tests(database_url: str) -> list[ForwardTestResponse]:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        rows = await forward_test_store.select_forward_tests(connection)
    return [await to_forward_test_response(database_url, row) for row in rows]


async def describe_refusal(database_url: str, refusal: StartRefusal, instrument: Instrument) -> str:
    if refusal.forward_test_id is None:
        return NO_FREE_CLIENT_ID_MESSAGE
    label = await describe_forward_test(database_url=database_url, forward_test_id=refusal.forward_test_id)
    return f"{label} already runs on {instrument.symbol} / {instrument.exchange}."


async def describe_forward_test(*, database_url: str, forward_test_id: int) -> str:
    """A label like "Forward test 3 (Bar count v1)" for messages."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        row = await forward_test_store.select_forward_test(connection, forward_test_id)
    if row is None:
        return f"Forward test {forward_test_id}"
    response = await to_forward_test_response(database_url, row)
    return f"Forward test {response.id} ({response.strategy_name} v{response.version_number})"


@dataclass(frozen=True)
class ForwardTestOnInstrument:
    forward_test_id: int
    label: str


async def find_forward_test_on_instrument(
    *, database_url: str, instrument: Instrument
) -> ForwardTestOnInstrument | None:
    """The forward test that holds a client ID on the instrument. Paper orders by hand on it are refused (12.2)."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        row = await forward_test_store.select_forward_test_on_instrument(connection, instrument)
    if row is None:
        return None
    label = await describe_forward_test(database_url=database_url, forward_test_id=row.id)
    return ForwardTestOnInstrument(forward_test_id=row.id, label=label)


class ForwardTestRoutes:
    """The route functions. They share the database URL, the clock, and the client ID range."""

    def __init__(self, *, database_url: str, clock: Clock, client_ids: range) -> None:
        self.database_url = database_url
        self.clock = clock
        self.client_ids = client_ids

    async def start_forward_test(self, request: StartForwardTestRequest) -> ForwardTestResponse | JSONResponse:
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=request.strategy_version_id
        )
        if strategy_version is None:
            detail = f"Strategy version {request.strategy_version_id} does not exist."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        instrument = Instrument(symbol=request.symbol, exchange=request.exchange, currency=request.currency)
        if request.end_time_utc is not None and request.end_time_utc <= self.clock.read_now_utc():
            detail = "The end time must be later than now."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        forward_test_request = ForwardTestRequest(
            strategy_version_id=request.strategy_version_id,
            instrument=instrument,
            bar_period=request.bar_period,
            end_time_utc=request.end_time_utc,
        )
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            result = await forward_test_store.start_forward_test(
                connection,
                request=forward_test_request,
                client_ids=self.client_ids,
                created_at_utc=self.clock.read_now_utc(),
            )
        if isinstance(result, StartRefusal):
            refused = StartRefusedResponse(
                detail=await describe_refusal(self.database_url, result, instrument),
                forward_test_id=result.forward_test_id,
            )
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=refused.model_dump())
        return await to_forward_test_response(self.database_url, result)

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


def create_forward_test_router(*, database_url: str, clock: Clock, client_ids: range) -> APIRouter:
    routes = ForwardTestRoutes(database_url=database_url, clock=clock, client_ids=client_ids)
    router = APIRouter()
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
