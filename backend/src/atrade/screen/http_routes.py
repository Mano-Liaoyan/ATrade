"""HTTP routes of the screen capability: list, read, create, change, and delete screens (screen.md section 24.7)."""

from datetime import datetime
from typing import Any, Literal

import psycopg
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, JsonValue

from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.screen import screen_store
from atrade.screen.screen_check import ScreenProblem, check_screen

type Market = Literal["US", "HK"]


class CreateScreenRequest(BaseModel):
    # The check of section 24.6 checks the market and the definition, so a problem gives its location.
    name: str
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


def create_screen_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = ScreenRoutes(database_url=database_url, clock=clock)
    router = APIRouter(prefix="/api/screens")
    not_found: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
    check_failed_response: dict[int | str, dict[str, Any]] = {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ScreenCheckFailedResponse}
    }
    router.add_api_route("", routes.list_screens, methods=["GET"])
    router.add_api_route(
        "",
        routes.create_screen,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ScreenResponse,
        responses=check_failed_response,
    )
    router.add_api_route("/{screen_id}", routes.read_screen, methods=["GET"], responses=not_found)
    router.add_api_route(
        "/{screen_id}",
        routes.change_screen,
        methods=["PUT"],
        response_model=ScreenResponse,
        responses={**not_found, **check_failed_response},
    )
    router.add_api_route(
        "/{screen_id}",
        routes.delete_screen,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses=not_found,
    )
    return router
