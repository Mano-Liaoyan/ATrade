"""Custom indicators: the table, the check, the routes, and the catalog (docs/architecture/indicator.md section 23.10).

The routes are methods of `CustomIndicatorRoutes`, so the assistant port can add them to its own router (#374).
"""

from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.indicator import (
    CUSTOM_KEY_PREFIX,
    IndicatorProblem,
    check_chart_placement,
    check_expression,
    check_name,
    count_formula_bars,
)
from atrade.market_data.indicator_series import (
    IndicatorCheckFailedResponse,
    IndicatorFormulaBody,
    IndicatorProblemResponse,
    IndicatorResponse,
    list_built_in_indicators,
)

MAX_VALUE_DESCRIPTION_LENGTH = 1000
SELECT_FIELDS = "custom_indicator_id, name, expression, chart_placement, value_description"
NOT_FOUND: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
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


class CustomIndicatorResponse(CustomIndicatorBody):
    custom_indicator_id: int
    # The catalog key, for example `custom_3`. A change keeps the key.
    key: str

    def to_catalog_item(self) -> IndicatorResponse:
        return IndicatorResponse(
            key=self.key,
            name=self.name,
            short_name=self.name,
            chart_placement="price" if self.chart_placement == "price" else "own",
            parameters=[],
            outputs=["value"],
            value_description=self.value_description,
            formula=IndicatorFormulaBody(
                name=self.name, expression=self.expression, chart_placement=self.chart_placement
            ),
        )


class CustomIndicatorCheckResponse(BaseModel):
    problems: list[IndicatorProblemResponse]
    # The bars that the expression needs for a value. None when the expression has a problem.
    look_back_bars: int | None


def make_response(row: tuple[int, str, str, str, str]) -> CustomIndicatorResponse:
    custom_indicator_id, name, expression, chart_placement, value_description = row
    return CustomIndicatorResponse(
        custom_indicator_id=custom_indicator_id,
        key=f"{CUSTOM_KEY_PREFIX}{custom_indicator_id}",
        name=name,
        expression=expression,
        chart_placement=chart_placement,
        value_description=value_description,
    )


def check_fields(body: CustomIndicatorBody) -> list[IndicatorProblem]:
    problems = [
        *check_name(body.name, ("name",)),
        *check_expression(body.expression),
        *check_chart_placement(body.chart_placement, ("chart_placement",)),
    ]
    if not 1 <= len(body.value_description.strip()) <= MAX_VALUE_DESCRIPTION_LENGTH:
        message = f"The value description must have 1 to {MAX_VALUE_DESCRIPTION_LENGTH} characters."
        problems.append(IndicatorProblem(("value_description",), message))
    return problems


async def check_custom_indicator(
    connection: psycopg.AsyncConnection, body: CustomIndicatorBody, custom_indicator_id: int | None
) -> list[IndicatorProblemResponse]:
    """The problems of the fields, and of a name that another custom indicator has. Empty means correct."""
    problems = check_fields(body)
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT 1 FROM custom_indicator
            WHERE lower(name) = lower(%s) AND custom_indicator_id IS DISTINCT FROM %s
            """,
            (body.name.strip(), custom_indicator_id),
        )
        if await cursor.fetchone() is not None:
            problems.append(IndicatorProblem(("name",), f"A custom indicator with the name {body.name!r} exists."))
    return [IndicatorProblemResponse(location=list(item.location), message=item.message) for item in problems]


def refuse(problems: list[IndicatorProblemResponse]) -> JSONResponse:
    failure = IndicatorCheckFailedResponse(problems=problems)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())


def raise_not_found(custom_indicator_id: int) -> HTTPException:
    message = f"Custom indicator {custom_indicator_id} does not exist."
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=message)


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
        has_expression_problem = any(problem.location == ["expression"] for problem in problems)
        look_back_bars = None if has_expression_problem else count_formula_bars(body.expression)
        return CustomIndicatorCheckResponse(problems=problems, look_back_bars=look_back_bars)

    async def create(self, body: CustomIndicatorBody) -> CustomIndicatorResponse | JSONResponse:
        now_utc = self.clock.read_now_utc()
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            problems = await check_custom_indicator(connection, body, None)
            if problems:
                return refuse(problems)
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"""
                    INSERT INTO custom_indicator
                        (name, expression, chart_placement, value_description, created_at_utc, changed_at_utc)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING {SELECT_FIELDS}
                    """,
                    (*self.read_values(body), now_utc, now_utc),
                )
                row = await cursor.fetchone()
            await connection.commit()
        if row is None:
            message = "INSERT RETURNING gave no row."
            raise RuntimeError(message)
        return make_response(row)

    async def change(
        self, custom_indicator_id: int, body: CustomIndicatorBody
    ) -> CustomIndicatorResponse | JSONResponse:
        """Stored references keep their own expression (ADR 0009). Only new references get the changed one."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            problems = await check_custom_indicator(connection, body, custom_indicator_id)
            if problems:
                await self.read(custom_indicator_id)
                return refuse(problems)
            async with connection.cursor() as cursor:
                await cursor.execute(
                    f"""
                    UPDATE custom_indicator
                    SET name = %s, expression = %s, chart_placement = %s, value_description = %s, changed_at_utc = %s
                    WHERE custom_indicator_id = %s
                    RETURNING {SELECT_FIELDS}
                    """,
                    (*self.read_values(body), self.clock.read_now_utc(), custom_indicator_id),
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
    def read_values(body: CustomIndicatorBody) -> tuple[str, str, str, str]:
        return (body.name.strip(), body.expression.strip(), body.chart_placement, body.value_description.strip())


def create_custom_indicator_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = CustomIndicatorRoutes(database_url=database_url, clock=clock)

    async def list_catalog() -> list[IndicatorResponse]:
        return await list_indicator_catalog(database_url)

    async def check_body(body: CustomIndicatorBody) -> CustomIndicatorCheckResponse:
        return await routes.check(body)

    router = APIRouter()
    router.add_api_route("/api/market-data/indicators", list_catalog, methods=["GET"])
    router.add_api_route("/api/custom-indicators", routes.list_all, methods=["GET"])
    router.add_api_route(
        "/api/custom-indicators",
        routes.create,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=CustomIndicatorResponse,
        responses=CHECK_FAILED,
    )
    router.add_api_route("/api/custom-indicators/check", check_body, methods=["POST"])
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}", routes.read, methods=["GET"], responses=NOT_FOUND
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}",
        routes.change,
        methods=["PUT"],
        response_model=CustomIndicatorResponse,
        responses={**NOT_FOUND, **CHECK_FAILED},
    )
    router.add_api_route(
        "/api/custom-indicators/{custom_indicator_id}",
        routes.delete,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses=NOT_FOUND,
    )
    return router
