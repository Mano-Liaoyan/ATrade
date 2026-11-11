"""Custom indicators: the table, the check, the routes, and the catalog (docs/architecture/indicator.md section 23.10).

The routes are methods of `CustomIndicatorRoutes`, so port 8000 and port 8001 use the same handlers (section 23.10.6).
"""

from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from atrade.foundation.assistant_conversation import ConversationCheck, create_conversation_dependency
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.foundation.table_changes import ChangeSocket
from atrade.indicator import (
    CUSTOM_KEY_PREFIX,
    FormulaParameterBody,
    IndicatorProblem,
    check_chart_placement,
    check_expression_with_parameters,
    check_name,
    count_formula_bars,
    has_unstorable_character,
)
from atrade.market_data.indicator_series import (
    IndicatorCheckFailedResponse,
    IndicatorFormulaBody,
    IndicatorProblemResponse,
    IndicatorResponse,
    list_built_in_indicators,
    make_parameter_responses,
)

# The Settings page reads the list again after a change, also after a change of the AI assistant.
CUSTOM_INDICATOR_CHANGE_SOCKET = ChangeSocket(path="/ws/custom-indicators", tables=frozenset({"custom_indicator"}))

MAX_VALUE_DESCRIPTION_LENGTH = 1000
SELECT_FIELDS = (
    "custom_indicator_id, name, expression, chart_placement, value_description, kept, assistant_conversation_id, "
    "parameters"
)
NOT_FOUND: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
NAME_IN_USE: dict[int | str, dict[str, Any]] = {status.HTTP_409_CONFLICT: ERROR_RESPONSE}
CHECK_FAILED: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": IndicatorCheckFailedResponse}
}


class CustomIndicatorBody(BaseModel):
    """The route checks the values, so each problem has its location."""

    name: str
    expression: str
    chart_placement: str
    # The meaning, the range, and the unit of the value, as in the catalog.
    value_description: str
    # The parameters that the expression uses as numbers (section 23.10.1). Each reference holds its own values.
    parameters: list[FormulaParameterBody] = Field(default_factory=list[FormulaParameterBody])

    def read_parameters(self) -> list[dict[str, Any]]:
        return [parameter.model_dump() for parameter in self.parameters]


class CustomIndicatorResponse(CustomIndicatorBody):
    custom_indicator_id: int
    # The catalog key, for example `custom_3`. A change keeps the key.
    key: str
    # False for a new indicator of the AI assistant until the user clicks Keep (section 23.10.6).
    kept: bool
    # The conversation that made the indicator. Null for an indicator of the user.
    assistant_conversation_id: int | None

    def to_catalog_item(self) -> IndicatorResponse:
        return IndicatorResponse(
            key=self.key,
            name=self.name,
            short_name=self.name,
            chart_placement="price" if self.chart_placement == "price" else "own",
            parameters=make_parameter_responses(self.parameters),
            outputs=["value"],
            value_description=self.value_description,
            formula=IndicatorFormulaBody(
                name=self.name,
                expression=self.expression,
                chart_placement=self.chart_placement,
                parameters=self.parameters,
            ),
        )


class CustomIndicatorCheckResponse(BaseModel):
    problems: list[IndicatorProblemResponse]
    # The bars that the expression needs for a value when each parameter has its maximum. None when the expression or
    # a parameter has a problem.
    look_back_bars: int | None
    # The same when each parameter has its default.
    default_look_back_bars: int | None


def make_response(row: tuple[int, str, str, str, str, bool, int | None, list[Any]]) -> CustomIndicatorResponse:
    (
        custom_indicator_id,
        name,
        expression,
        chart_placement,
        value_description,
        kept,
        assistant_conversation_id,
        parameters,
    ) = row
    return CustomIndicatorResponse(
        custom_indicator_id=custom_indicator_id,
        key=f"{CUSTOM_KEY_PREFIX}{custom_indicator_id}",
        name=name,
        expression=expression,
        chart_placement=chart_placement,
        value_description=value_description,
        kept=kept,
        assistant_conversation_id=assistant_conversation_id,
        parameters=parameters,
    )


def check_fields(body: CustomIndicatorBody) -> list[IndicatorProblem]:
    problems = [
        *check_name(body.name, ("name",)),
        *check_expression_with_parameters(body.expression, body.read_parameters()),
        *check_chart_placement(body.chart_placement, ("chart_placement",)),
    ]
    if not 1 <= len(body.value_description.strip()) <= MAX_VALUE_DESCRIPTION_LENGTH:
        message = f"The value description must have 1 to {MAX_VALUE_DESCRIPTION_LENGTH} characters."
        problems.append(IndicatorProblem(("value_description",), message))
    elif has_unstorable_character(body.value_description):
        message = "The value description has a character that is not allowed."
        problems.append(IndicatorProblem(("value_description",), message))
    return problems


def make_name_in_use_message(body: CustomIndicatorBody) -> str:
    return f"A custom indicator with the name {body.name!r} exists."


async def check_custom_indicator(
    connection: psycopg.AsyncConnection, body: CustomIndicatorBody, custom_indicator_id: int | None
) -> list[IndicatorProblemResponse]:
    """The problems of the fields, and of a name that another custom indicator has. Empty means correct."""
    problems = check_fields(body)
    if not has_unstorable_character(body.name):
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT 1 FROM custom_indicator
                WHERE lower(name) = lower(%s) AND custom_indicator_id IS DISTINCT FROM %s
                """,
                (body.name.strip(), custom_indicator_id),
            )
            if await cursor.fetchone() is not None:
                problems.append(IndicatorProblem(("name",), make_name_in_use_message(body)))
    return [IndicatorProblemResponse(location=list(item.location), message=item.message) for item in problems]


def refuse(problems: list[IndicatorProblemResponse]) -> JSONResponse:
    failure = IndicatorCheckFailedResponse(problems=problems)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())


def raise_not_found(custom_indicator_id: int) -> HTTPException:
    message = f"Custom indicator {custom_indicator_id} does not exist."
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=message)


def name_in_use(body: CustomIndicatorBody) -> HTTPException:
    """Another save committed the name after the check. Only the unique index sees that."""
    return HTTPException(status.HTTP_409_CONFLICT, detail=make_name_in_use_message(body))


def change_refused(custom_indicator_id: int) -> HTTPException:
    message = (
        f"The AI assistant cannot change custom indicator {custom_indicator_id}. It can change only a custom indicator "
        "that it made in this conversation and that the user has not kept. Save a new custom indicator instead."
    )
    return HTTPException(status.HTTP_403_FORBIDDEN, detail=message)


async def require_change_allowed(
    connection: psycopg.AsyncConnection, custom_indicator_id: int, conversation_id: int
) -> None:
    """The row lock holds until the commit, so a Keep at the same time cannot come before the change."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT kept, assistant_conversation_id FROM custom_indicator
            WHERE custom_indicator_id = %s FOR UPDATE
            """,
            (custom_indicator_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        raise raise_not_found(custom_indicator_id)
    kept, assistant_conversation_id = row
    if kept or assistant_conversation_id != conversation_id:
        raise change_refused(custom_indicator_id)


async def list_custom_indicators(database_url: str) -> list[CustomIndicatorResponse]:
    async with await psycopg.AsyncConnection.connect(database_url) as connection, connection.cursor() as cursor:
        await cursor.execute(f"SELECT {SELECT_FIELDS} FROM custom_indicator ORDER BY lower(name)")
        return [make_response(row) for row in await cursor.fetchall()]


async def list_indicator_catalog(database_url: str) -> list[IndicatorResponse]:
    """The built-in indicators in their order, then the custom indicators by name. The screen page, the bar charts, and
    the rule builder read it."""
    custom_indicators = await list_custom_indicators(database_url)
    return [*list_built_in_indicators(), *[item.to_catalog_item() for item in custom_indicators]]


class CustomIndicatorRoutes:
    """One user: the last change wins."""

    def __init__(self, *, database_url: str, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock

    async def list_all(self) -> list[CustomIndicatorResponse]:
        return await list_custom_indicators(self.database_url)

    async def read(self, custom_indicator_id: int) -> CustomIndicatorResponse:
        async with (
            await psycopg.AsyncConnection.connect(self.database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                f"SELECT {SELECT_FIELDS} FROM custom_indicator WHERE custom_indicator_id = %s", (custom_indicator_id,)
            )
            row = await cursor.fetchone()
        if row is None:
            raise raise_not_found(custom_indicator_id)
        return make_response(row)

    async def check(
        self, body: CustomIndicatorBody, custom_indicator_id: int | None = None
    ) -> CustomIndicatorCheckResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            problems = await check_custom_indicator(connection, body, custom_indicator_id)
        if any(problem.location[0] in {"expression", "parameters"} for problem in problems):
            return CustomIndicatorCheckResponse(problems=problems, look_back_bars=None, default_look_back_bars=None)
        return CustomIndicatorCheckResponse(
            problems=problems,
            look_back_bars=count_formula_bars(
                body.expression, tuple((parameter.name, parameter.maximum) for parameter in body.parameters)
            ),
            default_look_back_bars=count_formula_bars(
                body.expression, tuple((parameter.name, parameter.default) for parameter in body.parameters)
            ),
        )

    async def create(self, body: CustomIndicatorBody) -> CustomIndicatorResponse | JSONResponse:
        return await self.create_of(body, None)

    async def create_of(
        self, body: CustomIndicatorBody, conversation_id: int | None
    ) -> CustomIndicatorResponse | JSONResponse:
        """With `conversation_id` (port 8001): an indicator of that conversation, not kept."""
        now_utc = self.clock.read_now_utc()
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            problems = await check_custom_indicator(connection, body, None)
            if problems:
                return refuse(problems)
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"""
                        INSERT INTO custom_indicator
                            (name, expression, chart_placement, value_description, parameters, kept,
                             assistant_conversation_id, created_at_utc, changed_at_utc)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING {SELECT_FIELDS}
                        """,
                        (*self.read_values(body), conversation_id is None, conversation_id, now_utc, now_utc),
                    )
                    row = await cursor.fetchone()
            except psycopg.errors.UniqueViolation as error:
                raise name_in_use(body) from error
            await connection.commit()
        if row is None:
            message = "INSERT RETURNING gave no row."
            raise RuntimeError(message)
        return make_response(row)

    async def change(
        self, custom_indicator_id: int, body: CustomIndicatorBody
    ) -> CustomIndicatorResponse | JSONResponse:
        """Stored references keep their own expression (ADR 0009). Only new references get the changed one."""
        return await self.change_of(custom_indicator_id, body, None)

    async def change_of(
        self, custom_indicator_id: int, body: CustomIndicatorBody, conversation_id: int | None
    ) -> CustomIndicatorResponse | JSONResponse:
        """With `conversation_id` (port 8001): only an indicator of that conversation that the user has not kept. Else
        403."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            if conversation_id is not None:
                await require_change_allowed(connection, custom_indicator_id, conversation_id)
            problems = await check_custom_indicator(connection, body, custom_indicator_id)
            if problems:
                await self.read(custom_indicator_id)
                return refuse(problems)
            try:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"""
                        UPDATE custom_indicator
                        SET name = %s, expression = %s, chart_placement = %s, value_description = %s,
                            parameters = %s, changed_at_utc = %s
                        WHERE custom_indicator_id = %s
                        RETURNING {SELECT_FIELDS}
                        """,
                        (*self.read_values(body), self.clock.read_now_utc(), custom_indicator_id),
                    )
                    row = await cursor.fetchone()
            except psycopg.errors.UniqueViolation as error:
                raise name_in_use(body) from error
            await connection.commit()
        if row is None:
            raise raise_not_found(custom_indicator_id)
        return make_response(row)

    async def keep(self, custom_indicator_id: int) -> CustomIndicatorResponse:
        """Sets `kept`, so port 8001 cannot change the indicator. The change time stays: the formula does not change."""
        async with (
            await psycopg.AsyncConnection.connect(self.database_url) as connection,
            connection.cursor() as cursor,
        ):
            await cursor.execute(
                f"""
                UPDATE custom_indicator SET kept = true WHERE custom_indicator_id = %s RETURNING {SELECT_FIELDS}
                """,
                (custom_indicator_id,),
            )
            row = await cursor.fetchone()
            await connection.commit()
        if row is None:
            raise raise_not_found(custom_indicator_id)
        return make_response(row)

    async def delete(self, custom_indicator_id: int) -> None:
        """Stored references keep working: each one holds its expression (ADR 0009)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            result = await connection.execute(
                "DELETE FROM custom_indicator WHERE custom_indicator_id = %s", (custom_indicator_id,)
            )
            await connection.commit()
        if result.rowcount == 0:
            raise raise_not_found(custom_indicator_id)

    @staticmethod
    def read_values(body: CustomIndicatorBody) -> tuple[str, str, str, str, Jsonb]:
        return (
            body.name.strip(),
            body.expression.strip(),
            body.chart_placement,
            body.value_description.strip(),
            Jsonb(body.read_parameters()),
        )


def add_read_routes(router: APIRouter, routes: CustomIndicatorRoutes) -> None:
    router.add_api_route("/api/custom-indicators", routes.list_all, methods=["GET"])
    router.add_api_route("/api/custom-indicators/check", routes.check, methods=["POST"])
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}", routes.read, methods=["GET"], responses=NOT_FOUND
    )


def create_custom_indicator_assistant_router(
    *, database_url: str, clock: Clock, conversation_exists: ConversationCheck
) -> APIRouter:
    """The 5 custom indicator routes of port 8001 (docs/architecture/assistant.md 25.3.3). No keep and no delete."""
    routes = CustomIndicatorRoutes(database_url=database_url, clock=clock)
    read_conversation_id = create_conversation_dependency(conversation_exists)

    async def create(
        body: CustomIndicatorBody, conversation_id: Annotated[int, Depends(read_conversation_id)]
    ) -> CustomIndicatorResponse | JSONResponse:
        return await routes.create_of(body, conversation_id)

    async def change(
        custom_indicator_id: int,
        body: CustomIndicatorBody,
        conversation_id: Annotated[int, Depends(read_conversation_id)],
    ) -> CustomIndicatorResponse | JSONResponse:
        return await routes.change_of(custom_indicator_id, body, conversation_id)

    router = APIRouter()
    add_read_routes(router, routes)
    router.add_api_route(
        "/api/custom-indicators",
        create,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=CustomIndicatorResponse,
        responses={**CHECK_FAILED, **NAME_IN_USE},
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}",
        change,
        methods=["PUT"],
        response_model=CustomIndicatorResponse,
        responses={**NOT_FOUND, **CHECK_FAILED, **NAME_IN_USE, status.HTTP_403_FORBIDDEN: ERROR_RESPONSE},
    )
    return router


def create_custom_indicator_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = CustomIndicatorRoutes(database_url=database_url, clock=clock)

    async def list_catalog() -> list[IndicatorResponse]:
        return await list_indicator_catalog(database_url)

    router = APIRouter()
    router.add_api_route("/api/market-data/indicators", list_catalog, methods=["GET"])
    add_read_routes(router, routes)
    router.add_api_route(
        "/api/custom-indicators",
        routes.create,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=CustomIndicatorResponse,
        responses={**CHECK_FAILED, **NAME_IN_USE},
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}",
        routes.change,
        methods=["PUT"],
        response_model=CustomIndicatorResponse,
        responses={**NOT_FOUND, **CHECK_FAILED, **NAME_IN_USE},
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}/keep", routes.keep, methods=["POST"], responses=NOT_FOUND
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}",
        routes.delete,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses=NOT_FOUND,
    )
    return router
