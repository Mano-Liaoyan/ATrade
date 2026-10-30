"""HTTP routes of the strategy capability: create, list, open, save, and delete strategies and strategy versions."""

from datetime import datetime
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints, model_validator

from atrade.foundation.assistant_conversation import ConversationCheck, create_conversation_dependency
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.strategy import strategy_store
from atrade.strategy.code_checks import CodeProblem
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.version_saving import save_ai_assistant_version, save_checked_version

MAX_STRATEGY_NAME_LENGTH = 100
FIRST_VERSION_NUMBER = 1

StrategyName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_STRATEGY_NAME_LENGTH)
]


class CreateStrategyRequest(BaseModel):
    name: StrategyName


class SaveVersionRequest(BaseModel):
    """Exactly one of `code` and `rules` (section 9.6)."""

    code: str | None = None
    rules: StrategyRules | None = None

    @model_validator(mode="after")
    def check_one_of_code_and_rules(self) -> SaveVersionRequest:
        if (self.code is None) == (self.rules is None):
            message = "The body must have exactly one of code and rules."
            raise ValueError(message)
        return self

    def to_content(self) -> strategy_store.VersionContent:
        if self.rules is None:
            return strategy_store.VersionContent(code=self.code or "", source="user", rules=None)
        rules = self.rules.model_dump(mode="json")
        return strategy_store.VersionContent(code=make_rules_code(self.rules), source="rule_builder", rules=rules)


class SaveCodeRequest(BaseModel):
    """The save body of port 8001: the AI assistant saves code only (docs/architecture/assistant.md 25.5)."""

    code: str


class RulesCodeRequest(BaseModel):
    rules: StrategyRules


class RulesCodeResponse(BaseModel):
    code: str


class StrategyVersionSummary(BaseModel):
    id: int
    version_number: int
    code_sha256: str
    created_at_utc: datetime
    source: strategy_store.VersionSource
    conversation_id: int | None
    discarded: bool


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
    conversation_id: int | None
    discarded: bool


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
        conversation_id=version.conversation_id,
        discarded=version.discarded,
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
            conversation_id=version.conversation_id,
            discarded=version.discarded,
        )
        for version in versions
    ]
    return StrategyResponse(
        id=strategy.id, name=strategy.name, created_at_utc=strategy.created_at_utc, versions=version_summaries
    )


def to_save_response(
    saved: strategy_store.SavedVersion | list[CodeProblem] | None, response: Response
) -> StrategyVersionResponse | JSONResponse:
    if isinstance(saved, list):
        problem_responses = [CodeProblemResponse(line=problem.line, message=problem.message) for problem in saved]
        failure = CodeCheckFailedResponse(problems=problem_responses)
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found.")
    if not saved.is_new_version:
        response.status_code = status.HTTP_200_OK
    return to_version_response(saved.version)


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
        """Checks the code first. Then it appends a version, or returns the latest version when the code is the same.

        A `rules` body makes the code from the rules, and the latest version is the same only when the rules are too.
        """
        saved = await save_checked_version(
            database_url=self.database_url,
            strategy_id=strategy_id,
            content=request.to_content(),
            created_at_utc=self.clock.read_now_utc(),
        )
        return to_save_response(saved, response)

    async def save_ai_assistant_version(
        self, strategy_id: int, request: SaveCodeRequest, response: Response, conversation_id: int
    ) -> StrategyVersionResponse | JSONResponse:
        """The save of port 8001: the source ai_assistant and the conversation (docs/architecture/assistant.md 25.5)."""
        saved = await save_ai_assistant_version(
            database_url=self.database_url,
            strategy_id=strategy_id,
            code=request.code,
            conversation_id=conversation_id,
            created_at_utc=self.clock.read_now_utc(),
        )
        return to_save_response(saved, response)

    async def discard_version(self, strategy_id: int, version_number: int) -> StrategyVersionResponse:
        """Adds the discarded mark to a version that the AI assistant saved (docs/architecture/assistant.md 25.5)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            result = await strategy_store.discard_version(
                connection,
                strategy_id=strategy_id,
                version_number=version_number,
                discarded_at_utc=self.clock.read_now_utc(),
            )
            await connection.commit()
        if result == strategy_store.DiscardResult.NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy version not found.")
        if result == strategy_store.DiscardResult.NOT_AI_ASSISTANT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a strategy version that the AI assistant saved can be discarded.",
            )
        return await self.read_version(strategy_id, version_number)

    async def make_code(self, request: RulesCodeRequest) -> RulesCodeResponse:
        """Makes the code from the rules and saves nothing (section 9.8.3)."""
        return RulesCodeResponse(code=make_rules_code(request.rules))

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


NOT_FOUND: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
SAVE_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": StrategyVersionResponse,
        "description": (
            "The code (and, for a rules body, the rules) is the same as the latest version. No new version is made."
        ),
    },
    **NOT_FOUND,
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": CodeCheckFailedResponse},
}


def add_shared_routes(router: APIRouter, routes: StrategyRoutes) -> None:
    """The routes of port 8000 that port 8001 also has without a change (docs/architecture/assistant.md 25.3.3)."""
    router.add_api_route(
        "",
        routes.create_strategy,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        responses={status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    router.add_api_route("", routes.list_strategies, methods=["GET"])
    router.add_api_route("/{strategy_id}", routes.read_strategy, methods=["GET"], responses=NOT_FOUND)
    router.add_api_route(
        "/{strategy_id}/versions/{version_number}", routes.read_version, methods=["GET"], responses=NOT_FOUND
    )


def create_strategy_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = StrategyRoutes(database_url=database_url, clock=clock)
    router = APIRouter()
    router.add_api_route("/api/strategy-rules/code", routes.make_code, methods=["POST"])
    router.include_router(create_strategies_router(routes))
    return router


def create_strategies_router(routes: StrategyRoutes) -> APIRouter:
    router = APIRouter(prefix="/api/strategies")
    add_shared_routes(router, routes)
    router.add_api_route(
        "/{strategy_id}",
        routes.delete_strategy,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={**NOT_FOUND, status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    router.add_api_route(
        "/{strategy_id}/versions/{version_number}/discard",
        routes.discard_version,
        methods=["POST"],
        responses={**NOT_FOUND, status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    router.add_api_route(
        "/{strategy_id}/versions",
        routes.save_version,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=StrategyVersionResponse,
        responses=SAVE_RESPONSES,
    )
    return router


def create_strategy_assistant_router(
    *, database_url: str, clock: Clock, conversation_exists: ConversationCheck
) -> APIRouter:
    """The strategy routes of port 8001 (docs/architecture/assistant.md 25.3.3). No delete, no discard."""
    routes = StrategyRoutes(database_url=database_url, clock=clock)
    read_conversation_id = create_conversation_dependency(conversation_exists)

    async def save_ai_assistant_version(
        strategy_id: int,
        request: SaveCodeRequest,
        response: Response,
        conversation_id: Annotated[int, Depends(read_conversation_id)],
    ) -> StrategyVersionResponse | JSONResponse:
        return await routes.save_ai_assistant_version(strategy_id, request, response, conversation_id)

    router = APIRouter(prefix="/api/strategies")
    add_shared_routes(router, routes)
    router.add_api_route(
        "/{strategy_id}/versions",
        save_ai_assistant_version,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=StrategyVersionResponse,
        responses=SAVE_RESPONSES,
    )
    return router
