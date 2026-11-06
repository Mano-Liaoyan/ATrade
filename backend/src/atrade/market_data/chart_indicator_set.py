"""The chart indicator set: the indicators of the instrument page chart and the favorites of "Add indicator"
(docs/architecture/indicator.md section 23.9.7).

The set is one row of the table `chart_indicator_set`, like the global source order. The last `PUT` wins.
"""

from collections import Counter

import psycopg
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from atrade.foundation.clock import Clock
from atrade.indicator import (
    INDICATOR_CATALOG,
    check_indicator_reference,
    find_indicator_definition,
    is_custom_key,
)
from atrade.market_data.indicator_series import (
    IndicatorCheckFailedResponse,
    IndicatorFormulaBody,
    IndicatorProblemResponse,
)

MAX_PANES = 4
PALETTE_SIZE = 14
LINE_STYLES = ("solid", "dashed", "dotted")
MIN_LINE_WIDTH = 1
MAX_LINE_WIDTH = 4

type Location = list[str | int]


class SavedChartLine(BaseModel):
    output: str
    # A palette index from 1 to 14 (section 23.9.3).
    color: int
    # `solid`, `dashed`, or `dotted`. The route checks the value, so a wrong value is a problem with its location.
    style: str
    # 1 to 4 pixels.
    width: int


class SavedChartIndicator(BaseModel):
    indicator: str
    parameters: dict[str, int | float]
    hidden: bool
    # One line for each output of the indicator.
    lines: list[SavedChartLine]
    # A custom indicator only (section 23.10). The chart keeps it after a change or a delete (ADR 0009).
    formula: IndicatorFormulaBody | None = Field(default=None, exclude_if=lambda value: value is None)


class SavedChartPane(BaseModel):
    indicators: list[SavedChartIndicator]


class ChartIndicatorSet(BaseModel):
    """The first pane is the price pane. The other panes are own panes, in the order on the chart."""

    panes: list[SavedChartPane]
    # Catalog keys. "Add indicator" shows them first.
    favorites: list[str]


# The set that the migration writes: the price pane without indicators, and no favorites.
DEFAULT_CHART_INDICATOR_SET = ChartIndicatorSet(panes=[SavedChartPane(indicators=[])], favorites=[])


def check_chart_indicator_set(chart_set: ChartIndicatorSet) -> list[IndicatorProblemResponse]:
    """Returns the problems of section 23.9.7, each with its location in the body. Empty means correct."""
    problems: list[IndicatorProblemResponse] = []
    if not 1 <= len(chart_set.panes) <= MAX_PANES:
        message = f"A chart has 1 to {MAX_PANES} panes, not {len(chart_set.panes)}."
        problems.append(IndicatorProblemResponse(location=["panes"], message=message))
    for pane_index, pane in enumerate(chart_set.panes):
        location: Location = ["panes", pane_index, "indicators"]
        if pane_index > 0 and not pane.indicators:
            problems.append(IndicatorProblemResponse(location=location, message="An own pane must have an indicator."))
        for indicator_index, indicator in enumerate(pane.indicators):
            problems.extend(
                check_chart_indicator(indicator, is_price_pane=pane_index == 0, location=[*location, indicator_index])
            )
    problems.extend(check_favorites(chart_set.favorites))
    return problems


def check_chart_indicator(
    indicator: SavedChartIndicator, *, is_price_pane: bool, location: Location
) -> list[IndicatorProblemResponse]:
    reference = indicator.model_dump(include={"indicator", "parameters", "formula"}, exclude_none=True)
    problems = [
        IndicatorProblemResponse(location=[*location, *problem.location], message=problem.message)
        for problem in check_indicator_reference(reference, has_output=False)
    ]
    is_custom = is_custom_key(indicator.indicator)
    if is_custom and problems:
        return problems
    definition = find_indicator_definition(reference) if is_custom else INDICATOR_CATALOG.get(indicator.indicator)
    if definition is None:
        return problems
    expected_placement = "price" if is_price_pane else "own"
    if definition.chart_placement != expected_placement:
        pane_name = "the price pane" if is_price_pane else "an own pane"
        message = (
            f"{definition.name} has the chart placement {definition.chart_placement!r}. It cannot be in {pane_name}."
        )
        problems.append(IndicatorProblemResponse(location=[*location, "indicator"], message=message))
    return [*problems, *check_lines(indicator.lines, definition.outputs, [*location, "lines"])]


def check_lines(
    lines: list[SavedChartLine], outputs: tuple[str, ...], location: Location
) -> list[IndicatorProblemResponse]:
    problems: list[IndicatorProblemResponse] = []
    seen: set[str] = set()
    for line_index, line in enumerate(lines):
        line_location: Location = [*location, line_index]
        if line.output not in outputs:
            message = f"Unknown output {line.output!r}. Known outputs: {', '.join(outputs)}."
            problems.append(IndicatorProblemResponse(location=[*line_location, "output"], message=message))
        elif line.output in seen:
            message = f"The output {line.output!r} has more than 1 line."
            problems.append(IndicatorProblemResponse(location=[*line_location, "output"], message=message))
        seen.add(line.output)
        problems.extend(check_line_style(line, line_location))
    missing = [output for output in outputs if output not in seen]
    if missing:
        message = f"Each output needs 1 line. No line for: {', '.join(missing)}."
        problems.append(IndicatorProblemResponse(location=location, message=message))
    return problems


def check_line_style(line: SavedChartLine, location: Location) -> list[IndicatorProblemResponse]:
    problems: list[IndicatorProblemResponse] = []
    if not 1 <= line.color <= PALETTE_SIZE:
        message = f"The color must be from 1 to {PALETTE_SIZE}, not {line.color}."
        problems.append(IndicatorProblemResponse(location=[*location, "color"], message=message))
    if line.style not in LINE_STYLES:
        message = f"Unknown line style {line.style!r}. Known line styles: {', '.join(LINE_STYLES)}."
        problems.append(IndicatorProblemResponse(location=[*location, "style"], message=message))
    if not MIN_LINE_WIDTH <= line.width <= MAX_LINE_WIDTH:
        message = f"The width must be from {MIN_LINE_WIDTH} to {MAX_LINE_WIDTH}, not {line.width}."
        problems.append(IndicatorProblemResponse(location=[*location, "width"], message=message))
    return problems


def check_favorites(favorites: list[str]) -> list[IndicatorProblemResponse]:
    problems: list[IndicatorProblemResponse] = []
    counts: Counter[str] = Counter()
    for index, key in enumerate(favorites):
        counts[key] += 1
        # A deleted custom indicator can stay here: "Add indicator" shows only the catalog (section 23.10).
        if key not in INDICATOR_CATALOG and not is_custom_key(key):
            message = f"Unknown indicator {key!r}. Known indicators: {', '.join(INDICATOR_CATALOG)}."
            problems.append(IndicatorProblemResponse(location=["favorites", index], message=message))
        elif counts[key] > 1:
            message = f"The favorite {key!r} is in the list more than 1 time."
            problems.append(IndicatorProblemResponse(location=["favorites", index], message=message))
    return problems


async def select_chart_indicator_set(connection: psycopg.AsyncConnection) -> ChartIndicatorSet:
    """The saved set. Without a row (only an emptied test database), the set of the migration."""
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT panes, favorites FROM chart_indicator_set")
        row = await cursor.fetchone()
    if row is None:
        return DEFAULT_CHART_INDICATOR_SET
    return ChartIndicatorSet.model_validate({"panes": row[0], "favorites": row[1]})


def create_chart_indicator_set_router(*, database_url: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.get("/api/market-data/chart-indicators")
    async def read_chart_indicator_set(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
    ) -> ChartIndicatorSet:
        async with await psycopg.AsyncConnection.connect(database_url) as connection:
            return await select_chart_indicator_set(connection)

    @router.put(
        "/api/market-data/chart-indicators",
        response_model=ChartIndicatorSet,
        responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": IndicatorCheckFailedResponse}},
    )
    async def save_chart_indicator_set(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        body: ChartIndicatorSet,
    ) -> ChartIndicatorSet | JSONResponse:
        """A `422` of section 23.9.7 has the problem list. A body of a wrong JSON type is the FastAPI `422`."""
        problems = check_chart_indicator_set(body)
        if problems:
            failure = IndicatorCheckFailedResponse(problems=problems)
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())
        body_json = body.model_dump(mode="json")
        async with await psycopg.AsyncConnection.connect(database_url) as connection:
            await connection.execute(
                """
                INSERT INTO chart_indicator_set (single_row, panes, favorites, changed_at_utc)
                VALUES (true, %(panes)s, %(favorites)s, %(changed_at_utc)s)
                ON CONFLICT (single_row) DO UPDATE
                SET panes = excluded.panes, favorites = excluded.favorites, changed_at_utc = excluded.changed_at_utc
                """,
                {
                    "panes": Jsonb(body_json["panes"]),
                    "favorites": Jsonb(body_json["favorites"]),
                    "changed_at_utc": clock.read_now_utc(),
                },
            )
            await connection.commit()
        return body

    return router
