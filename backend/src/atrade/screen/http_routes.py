"""HTTP routes of the screen capability: list, read, create, change, delete, and run screens, and read screen results
(screen.md section 24.7)."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, JsonValue

from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.screen import screen_store
from atrade.screen.screen_check import ScreenProblem, check_screen
from atrade.screen.screen_run import name_indicator
from atrade.screen.screen_running import run_saved_screen

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

type Market = Literal["US", "HK"]


class CreateScreenRequest(BaseModel):
    # The check of section 24.6 checks the market and the definition, so a problem gives its location.
    name: str
    market: str
    definition: JsonValue


class RunScreenRequest(BaseModel):
    """A run of a changed screen (section 24.13). The run does not change the saved screen."""

    market: str
    definition: JsonValue


class ChangeScreenRequest(BaseModel):
    name: str
    definition: JsonValue


class ScreenListItemResponse(BaseModel):
    id: int
    name: str
    market: Market
    kept: bool
    updated_at_utc: datetime


class ScreenResultSummaryResponse(BaseModel):
    id: int
    run_at_utc: datetime
    result_count: int


class ScreenResponse(BaseModel):
    id: int
    name: str
    market: Market
    definition: dict[str, Any]
    kept: bool
    assistant_conversation_id: int | None
    created_at_utc: datetime
    updated_at_utc: datetime
    # The last 10 screen results, the last run first.
    recent_screen_results: list[ScreenResultSummaryResponse]


class ScreenProblemResponse(BaseModel):
    # The path in the request body, for example ["definition", "indicator_conditions", 0, "operator"].
    location: list[str | int]
    message: str


class ScreenCheckFailedResponse(BaseModel):
    problems: list[ScreenProblemResponse]


class ExclusionCountResponse(BaseModel):
    reason: str
    count: int


class ScreenRunSummaryResponse(BaseModel):
    # The count of all rows. `rows` has one page of them.
    row_count: int
    start_count: int
    after_filters_count: int
    after_indicator_conditions_count: int
    result_count: int
    # The count of each exclusion reason, the most frequent reason first.
    exclusion_counts: list[ExclusionCountResponse]
    # The date of the last daily bar that the run used. Null when no start instrument has daily bars.
    daily_bars_date: date | None
    run_at_utc: datetime
    run_seconds: float


class ScreenResultRowResponse(BaseModel):
    position: int
    symbol: str
    exchange: str
    currency: str
    last_price: Decimal
    average_trading_value_20: float | None
    # The value of each indicator of a condition or of the order, by its name, for example "RSI(14)".
    indicator_values: dict[str, float]
    # The percentile of each rank condition, by the name of its indicator.
    percentiles: dict[str, float]


class ScreenResultExclusionResponse(BaseModel):
    symbol: str
    exchange: str
    currency: str
    # "<location>: <condition>", "No value: <indicator>", or "No daily bars".
    reason: str


class ScreenIndicatorNamesResponse(BaseModel):
    """The UI names of the indicators of the definition, for example "RSI(14)" (screen.md section 24.7)."""

    # One name for each indicator condition, in the order of the definition.
    indicator_conditions: list[str]
    order: str


def name_definition_indicators(definition: dict[str, Any]) -> ScreenIndicatorNamesResponse:
    return ScreenIndicatorNamesResponse(
        indicator_conditions=[
            name_indicator(condition["indicator"]) for condition in definition["indicator_conditions"]
        ],
        order=name_indicator(definition["order"]["indicator"]),
    )


class ScreenResultResponse(BaseModel):
    id: int
    screen_id: int
    market: Market
    assistant_conversation_id: int | None
    summary: ScreenRunSummaryResponse
    # The copy of the screen definition at the run.
    definition: dict[str, Any]
    indicator_names: ScreenIndicatorNamesResponse
    rows: list[ScreenResultRowResponse]
    exclusions: list[ScreenResultExclusionResponse]


def to_row_response(row: screen_store.ScreenResultRowRecord) -> ScreenResultRowResponse:
    return ScreenResultRowResponse(
        position=row.position, symbol=row.symbol, exchange=row.exchange, currency=row.currency, **row.values
    )


async def read_screen_result_response(
    connection: psycopg.AsyncConnection, screen_result_id: int, *, offset: int, limit: int
) -> ScreenResultResponse | None:
    result = await screen_store.select_screen_result(connection, screen_result_id)
    if result is None:
        return None
    rows = await screen_store.select_screen_result_rows(connection, screen_result_id, offset=offset, limit=limit)
    exclusions = await screen_store.select_screen_result_exclusions(connection, screen_result_id)
    counts = await screen_store.select_exclusion_counts(connection, screen_result_id)
    summary = ScreenRunSummaryResponse(
        row_count=result.result_count,
        start_count=result.start_count,
        after_filters_count=result.after_filters_count,
        after_indicator_conditions_count=result.after_indicator_conditions_count,
        result_count=result.result_count,
        exclusion_counts=[ExclusionCountResponse(reason=count.reason, count=count.count) for count in counts],
        daily_bars_date=result.daily_bars_date,
        run_at_utc=result.run_at_utc,
        run_seconds=result.run_seconds,
    )
    return ScreenResultResponse(
        id=result.id,
        screen_id=result.screen_id,
        market=result.market,  # pyright: ignore[reportArgumentType] - the CHECK constraint holds US or HK
        assistant_conversation_id=result.assistant_conversation_id,
        summary=summary,
        definition=result.definition,
        indicator_names=name_definition_indicators(result.definition),
        rows=[to_row_response(row) for row in rows],
        exclusions=[
            ScreenResultExclusionResponse(
                symbol=exclusion.symbol,
                exchange=exclusion.exchange,
                currency=exclusion.currency,
                reason=exclusion.reason,
            )
            for exclusion in exclusions
        ],
    )


def to_screen_response(
    screen: screen_store.ScreenRecord, results: list[screen_store.ScreenResultSummaryRecord]
) -> ScreenResponse:
    return ScreenResponse(
        id=screen.id,
        name=screen.name,
        market=screen.market,  # pyright: ignore[reportArgumentType] - the CHECK constraint holds US or HK
        definition=screen.definition,
        kept=screen.kept,
        assistant_conversation_id=screen.assistant_conversation_id,
        created_at_utc=screen.created_at_utc,
        updated_at_utc=screen.updated_at_utc,
        recent_screen_results=[
            ScreenResultSummaryResponse(id=result.id, run_at_utc=result.run_at_utc, result_count=result.result_count)
            for result in results
        ],
    )


def check_failed(problems: list[ScreenProblem]) -> JSONResponse:
    failure = ScreenCheckFailedResponse(
        problems=[
            ScreenProblemResponse(location=list(problem.location), message=problem.message) for problem in problems
        ]
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())


def name_in_use(name: str) -> JSONResponse:
    return check_failed([ScreenProblem(("name",), f"A screen with the name {name!r} exists.")])


def screen_not_found(screen_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"The screen {screen_id} does not exist.")


def screen_result_not_found(screen_result_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"The screen result {screen_result_id} does not exist.")


class ScreenRoutes:
    """The route functions. They share the database URL and the clock."""

    def __init__(self, *, database_url: str, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock

    async def list_screens(self) -> list[ScreenListItemResponse]:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            screens = await screen_store.select_screens(connection)
        return [
            ScreenListItemResponse(
                id=screen.id,
                name=screen.name,
                market=screen.market,  # pyright: ignore[reportArgumentType] - the CHECK constraint holds US or HK
                kept=screen.kept,
                updated_at_utc=screen.updated_at_utc,
            )
            for screen in screens
        ]

    async def read_screen(self, screen_id: int) -> ScreenResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            screen = await screen_store.select_screen(connection, screen_id)
            if screen is None:
                raise screen_not_found(screen_id)
            results = await screen_store.select_recent_screen_results(connection, screen_id)
        return to_screen_response(screen, results)

    async def create_screen(self, request: CreateScreenRequest) -> ScreenResponse | JSONResponse:
        problems = check_screen(name=request.name, market=request.market, definition=request.definition)
        if problems:
            return check_failed(problems)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            try:
                screen = await screen_store.insert_screen(
                    connection,
                    name=request.name,
                    market=request.market,
                    definition=request.definition,
                    now_utc=self.clock.read_now_utc(),
                )
            except screen_store.NameInUseError:
                return name_in_use(request.name)
            await connection.commit()
        return to_screen_response(screen, [])

    async def change_screen(self, screen_id: int, request: ChangeScreenRequest) -> ScreenResponse | JSONResponse:
        """Overwrites the name and the definition. A screen has no versions (section 24.1)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            screen = await screen_store.select_screen(connection, screen_id)
            if screen is None:
                raise screen_not_found(screen_id)
            problems = check_screen(name=request.name, market=screen.market, definition=request.definition)
            if problems:
                return check_failed(problems)
            try:
                changed = await screen_store.update_screen(
                    connection,
                    screen_id=screen_id,
                    name=request.name,
                    definition=request.definition,
                    now_utc=self.clock.read_now_utc(),
                )
            except screen_store.NameInUseError:
                return name_in_use(request.name)
            if changed is None:
                raise screen_not_found(screen_id)
            results = await screen_store.select_recent_screen_results(connection, screen_id)
            await connection.commit()
        return to_screen_response(changed, results)

    async def delete_screen(self, screen_id: int) -> None:
        """Also deletes the screen results of the screen. A backtest keeps its own copy of the screen."""
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            is_deleted = await screen_store.delete_screen(connection, screen_id)
        if not is_deleted:
            raise screen_not_found(screen_id)

    async def run_screen(
        self, screen_id: int, request: RunScreenRequest | None = None
    ) -> ScreenResultResponse | JSONResponse:
        """Runs the saved screen and saves 1 screen result (section 24.5). With a body, runs that market and
        definition in place of the saved ones and keeps the saved screen (section 24.13)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            screen = await screen_store.select_screen(connection, screen_id)
        if screen is None:
            raise screen_not_found(screen_id)
        if request is not None:
            problems = check_screen(name=screen.name, market=request.market, definition=request.definition)
            if problems:
                return check_failed(problems)
            screen = replace(screen, market=request.market, definition=request.definition)
        problems = check_screen(name=screen.name, market=screen.market, definition=screen.definition)
        if problems:
            return check_failed(problems)
        screen_result_id = await run_saved_screen(database_url=self.database_url, clock=self.clock, screen=screen)
        return await self.read_screen_result(screen_result_id)

    async def read_screen_result(
        self,
        screen_result_id: int,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    ) -> ScreenResultResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            response = await read_screen_result_response(connection, screen_result_id, offset=offset, limit=limit)
        if response is None:
            raise screen_result_not_found(screen_result_id)
        return response


def create_screen_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = ScreenRoutes(database_url=database_url, clock=clock)
    router = APIRouter()
    not_found: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
    check_failed_response: dict[int | str, dict[str, Any]] = {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ScreenCheckFailedResponse}
    }
    router.add_api_route("/api/screens", routes.list_screens, methods=["GET"])
    router.add_api_route(
        "/api/screens",
        routes.create_screen,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ScreenResponse,
        responses=check_failed_response,
    )
    router.add_api_route("/api/screens/{screen_id}", routes.read_screen, methods=["GET"], responses=not_found)
    router.add_api_route(
        "/api/screens/{screen_id}",
        routes.change_screen,
        methods=["PUT"],
        response_model=ScreenResponse,
        responses={**not_found, **check_failed_response},
    )
    router.add_api_route(
        "/api/screens/{screen_id}",
        routes.delete_screen,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses=not_found,
    )
    router.add_api_route(
        "/api/screens/{screen_id}/runs",
        routes.run_screen,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ScreenResultResponse,
        responses={**not_found, **check_failed_response},
    )
    router.add_api_route(
        "/api/screen-results/{screen_result_id}", routes.read_screen_result, methods=["GET"], responses=not_found
    )
    return router
