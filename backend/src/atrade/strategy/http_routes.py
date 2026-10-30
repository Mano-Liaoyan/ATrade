"""HTTP routes of the strategy capability: create, list, open, save, and delete strategies and strategy versions."""

from datetime import datetime
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints

from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.strategy import strategy_store
from atrade.strategy.code_checks import check_strategy_code
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE

MAX_STRATEGY_NAME_LENGTH = 100
FIRST_VERSION_NUMBER = 1

StrategyName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_STRATEGY_NAME_LENGTH)
]


class CreateStrategyRequest(BaseModel):
    name: StrategyName


class SaveVersionRequest(BaseModel):
    code: str


class StrategyVersionSummary(BaseModel):
    id: int
    version_number: int
    code_sha256: str
    created_at_utc: datetime
    source: strategy_store.VersionSource


class StrategyResponse(BaseModel):
    id: int
    name: str
    created_at_utc: datetime
    versions: list[StrategyVersionSummary]


class StrategyListItem(BaseModel):
    id: int
    name: str
    latest_version_number: int


class StrategyVersionResponse(BaseModel):
    id: int
    strategy_id: int
    version_number: int
    code: str
    code_sha256: str
    created_at_utc: datetime
    source: strategy_store.VersionSource
    rules: dict[str, Any] | None


class CodeProblemResponse(BaseModel):
    line: int
    message: str


class CodeCheckFailedResponse(BaseModel):
    problems: list[CodeProblemResponse]


def to_version_response(version: strategy_store.StrategyVersionRecord) -> StrategyVersionResponse:
    return StrategyVersionResponse(
        id=version.id,
        strategy_id=version.strategy_id,
        version_number=version.version_number,
        code=version.code,
        code_sha256=version.code_sha256,
        created_at_utc=version.created_at_utc,
        source=version.source,
        rules=version.rules,
    )


async def read_strategy_response(connection: psycopg.AsyncConnection, strategy_id: int) -> StrategyResponse:
    strategy = await strategy_store.select_strategy(connection, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    versions = await strategy_store.select_versions(connection, strategy_id)
    version_summaries = [
        StrategyVersionSummary(
            id=version.id,
            version_number=version.version_number,
            code_sha256=version.code_sha256,
            created_at_utc=version.created_at_utc,
            source=version.source,
        )
        for version in versions
    ]
    return StrategyResponse(
        id=strategy.id, name=strategy.name, created_at_utc=strategy.created_at_utc, versions=version_summaries
    )


class StrategyRoutes:
    """The route functions. They share the database URL and the clock."""

    def __init__(self, *, database_url: str, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock

    async def create_strategy(self, request: CreateStrategyRequest) -> StrategyResponse:
        created_at_utc = self.clock.read_now_utc()
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            strategy = await strategy_store.insert_strategy(
                connection, name=request.name, created_at_utc=created_at_utc
            )
            if strategy is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A strategy with this name exists.")
            await strategy_store.insert_version(
                connection,
                strategy_id=strategy.id,
                version_number=FIRST_VERSION_NUMBER,
                content=strategy_store.VersionContent(code=STRATEGY_TEMPLATE, source="user", rules=None),
                created_at_utc=created_at_utc,
            )
            await connection.commit()
            return await read_strategy_response(connection, strategy.id)

    async def list_strategies(self) -> list[StrategyListItem]:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            rows = await strategy_store.select_strategies(connection)
        return [
            StrategyListItem(id=row.id, name=row.name, latest_version_number=row.latest_version_number) for row in rows
        ]

    async def read_strategy(self, strategy_id: int) -> StrategyResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            return await read_strategy_response(connection, strategy_id)

    async def read_version(self, strategy_id: int, version_number: int) -> StrategyVersionResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            version = await strategy_store.select_version(
                connection, strategy_id=strategy_id, version_number=version_number
            )
        if version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy version not found.")
        return to_version_response(version)

    async def save_version(
        self, strategy_id: int, request: SaveVersionRequest, response: Response
    ) -> StrategyVersionResponse | JSONResponse:
        """Checks the code first. Then it appends a version, or returns the latest version when the code is the same."""
        problems = await check_strategy_code(request.code)
        if problems:
            problem_responses = [
                CodeProblemResponse(line=problem.line, message=problem.message) for problem in problems
            ]
            failure = CodeCheckFailedResponse(problems=problem_responses)
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            saved = await strategy_store.save_version(
                connection, strategy_id=strategy_id, code=request.code, created_at_utc=self.clock.read_now_utc()
            )
            await connection.commit()
        if saved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
        if not saved.is_new_version:
            response.status_code = status.HTTP_200_OK
        return to_version_response(saved.version)

    async def delete_strategy(self, strategy_id: int) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            result = await strategy_store.delete_strategy(connection, strategy_id)
        if result == strategy_store.DeleteResult.NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
        if result == strategy_store.DeleteResult.IN_USE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A backtest or forward test uses a version of this strategy. It cannot be deleted.",
            )


def create_strategy_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = StrategyRoutes(database_url=database_url, clock=clock)
    router = APIRouter(prefix="/api/strategies")
    not_found: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
    router.add_api_route(
        "",
        routes.create_strategy,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        responses={status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    router.add_api_route("", routes.list_strategies, methods=["GET"])
    router.add_api_route("/{strategy_id}", routes.read_strategy, methods=["GET"], responses=not_found)
    router.add_api_route(
        "/{strategy_id}",
        routes.delete_strategy,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={**not_found, status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    router.add_api_route(
        "/{strategy_id}/versions/{version_number}", routes.read_version, methods=["GET"], responses=not_found
    )
    router.add_api_route(
        "/{strategy_id}/versions",
        routes.save_version,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=StrategyVersionResponse,
        responses={
            status.HTTP_200_OK: {
                "model": StrategyVersionResponse,
                "description": "The code is the same as the latest version. No new version is made.",
            },
            **not_found,
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": CodeCheckFailedResponse},
        },
    )
    return router
