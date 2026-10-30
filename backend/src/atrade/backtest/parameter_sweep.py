"""Parameter sweeps: the grid of parameter values and the SQL of the parameter_sweep table
(docs/architecture/backtest.md section 10.11).

Each combination of the grid is one backtest row with `sweep_id` and `parameters`. The runs wait in the same queue as
other backtests, so the backtest limits apply to them.
"""

import itertools
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Annotated

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from atrade.backtest import backtest_store
from atrade.backtest.backtest_store import BacktestRequest, BacktestRow, ParameterValues, UniversePeriod
from atrade.strategy import StrategyParameter

MAX_SWEEP_PARAMETERS = 3
MAX_SWEEP_RUNS = 200
# The decimal places of a float grid value. Without the rounding, 0.1 + 0.2 gives 0.30000000000000004.
FLOAT_GRID_DECIMALS = 10


class GridEntry(BaseModel):
    """One parameter of the grid. An `int` or `float` parameter needs `start`, `end`, and `step`. A `bool` parameter
    takes no values: the grid uses false and true."""

    name: Annotated[str, Field(min_length=1)]
    start: Decimal | None = None
    end: Decimal | None = None
    step: Decimal | None = None


def make_values(entry: GridEntry, parameter: StrategyParameter) -> list[int | float | bool] | str:
    """The values of one parameter, or why the entry is not valid. A float range that the step does not divide ends
    at the last value before `end`."""
    if parameter.type == "bool":
        if entry.start is not None or entry.end is not None or entry.step is not None:
            return f"The bool parameter {entry.name} takes no start, end, or step."
        return [False, True]
    if entry.start is None or entry.end is None or entry.step is None:
        return f"The parameter {entry.name} needs start, end, and step."
    if entry.step <= 0:
        return f"The step of {entry.name} must be more than 0."
    if entry.end < entry.start:
        return f"The end of {entry.name} must not be before its start."
    if parameter.type == "int" and any(value != value.to_integral_value() for value in (entry.start, entry.step)):
        return f"The int parameter {entry.name} needs an integer start and step."
    count = int((entry.end - entry.start) / entry.step) + 1
    if count > MAX_SWEEP_RUNS:
        return f"The grid has more than {MAX_SWEEP_RUNS} runs."
    values = [entry.start + entry.step * index for index in range(count)]
    if parameter.type == "int":
        return [int(value) for value in values]
    return [round(float(value), FLOAT_GRID_DECIMALS) for value in values]


def make_grid(entries: list[GridEntry], parameters: list[StrategyParameter]) -> list[ParameterValues] | str:
    """All combinations of the grid, or why the grid is not valid (docs/architecture/backtest.md section 10.11.1)."""
    if not entries or len(entries) > MAX_SWEEP_PARAMETERS:
        return f"The grid needs 1 to {MAX_SWEEP_PARAMETERS} parameters."
    by_name = {parameter.name: parameter for parameter in parameters}
    names = [entry.name for entry in entries]
    if len(set(names)) != len(names):
        return "The grid names a parameter more than once."
    values_by_name: list[list[int | float | bool]] = []
    for entry in entries:
        parameter = by_name.get(entry.name)
        if parameter is None:
            return f"{entry.name} is not a parameter of the strategy version."
        values = make_values(entry, parameter)
        if isinstance(values, str):
            return values
        values_by_name.append(values)
    run_count = 1
    for values in values_by_name:
        run_count *= len(values)
    if run_count > MAX_SWEEP_RUNS:
        return f"The grid has {run_count} runs. The maximum is {MAX_SWEEP_RUNS}."
    return [dict(zip(names, combination, strict=True)) for combination in itertools.product(*values_by_name)]


@dataclass(frozen=True)
class SweepRow:
    id: int
    strategy_version_id: int
    grid: list[dict[str, object]]
    created_at_utc: datetime


SWEEP_COLUMNS = "id, strategy_version_id, grid, created_at_utc"


async def insert_sweep(  # noqa: PLR0913 readability-exception: the keywords of one sweep start.
    connection: psycopg.AsyncConnection,
    *,
    request: BacktestRequest,
    grid: list[GridEntry],
    combinations: list[ParameterValues],
    universe_periods: list[UniversePeriod],
    created_at_utc: datetime,
) -> int:
    """Adds the sweep and one queued backtest for each combination. One transaction."""
    async with connection.transaction():
        cursor = await connection.execute(
            """
            INSERT INTO parameter_sweep (strategy_version_id, grid, created_at_utc)
            VALUES (%(strategy_version_id)s, %(grid)s, %(created_at_utc)s)
            RETURNING id
            """,
            {
                "strategy_version_id": request.strategy_version_id,
                "grid": Jsonb([entry.model_dump(mode="json", exclude_none=True) for entry in grid]),
                "created_at_utc": created_at_utc,
            },
        )
        inserted = await cursor.fetchone()
        if inserted is None:
            message = "INSERT ... RETURNING returned no row."
            raise RuntimeError(message)
        sweep_id = int(inserted[0])
        for combination in combinations:
            await backtest_store.insert_backtest(
                connection,
                request=replace(request, parameters=combination),
                created_at_utc=created_at_utc,
                universe_periods=universe_periods,
                sweep_id=sweep_id,
            )
    return sweep_id


async def select_sweeps(connection: psycopg.AsyncConnection) -> list[SweepRow]:
    """All sweeps, the newest first."""
    async with connection.cursor(row_factory=class_row(SweepRow)) as cursor:
        await cursor.execute(f"SELECT {SWEEP_COLUMNS} FROM parameter_sweep ORDER BY id DESC")
        return await cursor.fetchall()


async def select_sweep(connection: psycopg.AsyncConnection, sweep_id: int) -> SweepRow | None:
    async with connection.cursor(row_factory=class_row(SweepRow)) as cursor:
        await cursor.execute(f"SELECT {SWEEP_COLUMNS} FROM parameter_sweep WHERE id = %(id)s", {"id": sweep_id})
        return await cursor.fetchone()


async def select_sweep_runs(connection: psycopg.AsyncConnection, sweep_id: int) -> list[BacktestRow]:
    """The runs of the sweep, in grid order."""
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(
            f"SELECT {backtest_store.BACKTEST_COLUMNS} FROM backtest WHERE sweep_id = %(id)s ORDER BY id",
            {"id": sweep_id},
        )
        return await cursor.fetchall()


async def cancel_queued_runs(connection: psycopg.AsyncConnection, *, sweep_id: int, ended_at_utc: datetime) -> None:
    """Sets the queued runs of the sweep to cancelled. A running run continues to its end."""
    await connection.execute(
        """
        UPDATE backtest SET status = 'cancelled', ended_at_utc = %(ended_at_utc)s
        WHERE sweep_id = %(id)s AND status = 'queued'
        """,
        {"id": sweep_id, "ended_at_utc": ended_at_utc},
    )
