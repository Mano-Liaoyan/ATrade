"""HTTP routes of parameter sweeps (docs/architecture/backtest.md section 10.11.3). Port 8001 has only the 3 read
routes (docs/architecture/assistant.md 25.3.3): the AI assistant reads a sweep but does not start, cancel, or delete
one."""

from collections import Counter
from dataclasses import replace
from datetime import datetime
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from atrade.backtest import backtest_store
from atrade.backtest.backtest_access import find_bar_range
from atrade.backtest.backtest_start import BacktestRefusal, prepare_backtest
from atrade.backtest.backtest_store import BacktestStatus, ParameterValues
from atrade.backtest.http_routes import (
    NOT_FOUND,
    REFUSED,
    BacktestMetricsResponse,
    BacktestRoutes,
    StartBacktestRequest,
    refuse,
    to_metrics_response,
)
from atrade.backtest.parameter_sweep import (
    GridEntry,
    SweepRow,
    cancel_queued_runs,
    delete_sweep,
    insert_sweep,
    make_grid,
    requeue_failed_runs,
    select_sweep,
    select_sweep_runs,
    select_sweeps,
)
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE
from atrade.foundation.table_changes import ChangeSocket
from atrade.market_data import ExchangeRateReader
from atrade.strategy import StrategyParameter, StrategyVersion, read_strategy_parameters, read_strategy_version

# A sweep and the status of its runs: /ws/ sends a change message after a change (foundation/table_changes).
SWEEP_CHANGE_SOCKET = ChangeSocket(path="/ws/sweeps", tables=frozenset({"backtest", "parameter_sweep"}))

SWEEP_NOT_FOUND = "Parameter sweep not found."


class ParameterResponse(BaseModel):
    name: str
    type: str
    default: int | float | bool


class ParametersResponse(BaseModel):
    parameters: list[ParameterResponse]


class StartSweepRequest(StartBacktestRequest):
    """The fields of a backtest start and the grid of 1 to 3 parameters."""

    grid: list[GridEntry]


class SweepRunResponse(BaseModel):
    backtest_id: int
    parameters: ParameterValues
    status: BacktestStatus
    metrics: BacktestMetricsResponse | None


class SweepResponse(BaseModel):
    id: int
    strategy_version_id: int
    strategy_id: int
    strategy_name: str
    version_number: int
    grid: list[dict[str, object]]
    created_at_utc: datetime
    run_count: int
    # The run count of each status that has runs.
    status_counts: dict[str, int]


class SweepDetailResponse(SweepResponse):
    runs: list[SweepRunResponse]


def to_sweep_response(
    sweep: SweepRow, version: StrategyVersion, runs: list[backtest_store.BacktestRow]
) -> SweepResponse:
    return SweepResponse(
        id=sweep.id,
        strategy_version_id=sweep.strategy_version_id,
        strategy_id=version.strategy_id,
        strategy_name=version.strategy_name,
        version_number=version.version_number,
        grid=sweep.grid,
        created_at_utc=sweep.created_at_utc,
        run_count=len(runs),
        status_counts=dict(Counter(run.status for run in runs)),
    )


class SweepRoutes:
    def __init__(self, *, database_url: str, clock: Clock, exchange_rate_reader: ExchangeRateReader) -> None:
        self.database_url = database_url
        self.clock = clock
        self.exchange_rate_reader = exchange_rate_reader
        self.backtest_routes = BacktestRoutes(
            database_url=database_url, clock=clock, exchange_rate_reader=exchange_rate_reader
        )

    async def read_version_of(self, sweep: SweepRow) -> StrategyVersion:
        version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=sweep.strategy_version_id
        )
        if version is None:
            message = f"Sweep {sweep.id} refers to strategy version {sweep.strategy_version_id}, which is missing."
            raise RuntimeError(message)
        return version

    async def read_parameters_of(self, strategy_version_id: int) -> list[StrategyParameter] | None:
        version = await read_strategy_version(database_url=self.database_url, strategy_version_id=strategy_version_id)
        if version is None:
            return None
        return read_strategy_parameters(version.code)

    async def read_parameters(self, strategy_version_id: Annotated[int, Query()]) -> ParametersResponse:
        parameters = await self.read_parameters_of(strategy_version_id)
        if parameters is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy version not found.")
        return ParametersResponse(
            parameters=[
                ParameterResponse(name=parameter.name, type=parameter.type, default=parameter.default)
                for parameter in parameters
            ]
        )

    async def start_sweep(self, request: StartSweepRequest) -> SweepDetailResponse:
        parameters = await self.read_parameters_of(request.strategy_version_id)
        if parameters is None:
            refuse(f"Strategy version {request.strategy_version_id} does not exist.")
        combinations = make_grid(request.grid, parameters)
        if isinstance(combinations, str):
            refuse(combinations)
        backtest_request, periods = await self.backtest_routes.make_backtest_request(request)
        prepared = await prepare_backtest(
            database_url=self.database_url,
            exchange_rate_reader=self.exchange_rate_reader,
            request=backtest_request,
            universe_periods=periods,
        )
        if isinstance(prepared, BacktestRefusal):
            refuse(prepared.detail)
        bar_range = await find_bar_range(database_url=self.database_url, request=prepared, universe_periods=periods)
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            sweep_id = await insert_sweep(
                connection,
                request=replace(prepared, parameters=None),
                bar_range=bar_range,
                grid=request.grid,
                combinations=combinations,
                universe_periods=periods,
                created_at_utc=self.clock.read_now_utc(),
            )
        return await self.read_sweep(sweep_id)

    async def list_sweeps(self) -> list[SweepResponse]:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            sweeps = await select_sweeps(connection)
            return [
                to_sweep_response(
                    sweep, await self.read_version_of(sweep), await select_sweep_runs(connection, sweep.id)
                )
                for sweep in sweeps
            ]

    async def read_sweep(self, sweep_id: int) -> SweepDetailResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            sweep = await select_sweep(connection, sweep_id)
            if sweep is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SWEEP_NOT_FOUND)
            runs = await select_sweep_runs(connection, sweep_id)
        return SweepDetailResponse(
            **to_sweep_response(sweep, await self.read_version_of(sweep), runs).model_dump(),
            runs=[
                SweepRunResponse(
                    backtest_id=run.id,
                    parameters=run.parameters or {},
                    status=run.status,
                    metrics=to_metrics_response(backtest_store.read_metrics(run)),
                )
                for run in runs
            ],
        )

    async def cancel_sweep(self, sweep_id: int) -> SweepDetailResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if await select_sweep(connection, sweep_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SWEEP_NOT_FOUND)
            await cancel_queued_runs(connection, sweep_id=sweep_id, ended_at_utc=self.clock.read_now_utc())
        return await self.read_sweep(sweep_id)

    async def requeue_failed_runs(self, sweep_id: int) -> SweepDetailResponse:
        """Queues the failed and timed-out runs again, for example after the kernel stopped them when memory was low.
        The runs that finished stay."""
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if await select_sweep(connection, sweep_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SWEEP_NOT_FOUND)
            requeued_count = await requeue_failed_runs(connection, sweep_id=sweep_id)
        if requeued_count == 0:
            refuse(f"Parameter sweep #{sweep_id} has no failed or timed-out runs.")
        return await self.read_sweep(sweep_id)

    async def delete_sweep(self, sweep_id: int) -> None:
        """A true delete of the sweep and its runs. 409 while a run is queued or running, and for a run that is the
        same-period backtest of a forward test."""
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if await select_sweep(connection, sweep_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SWEEP_NOT_FOUND)
            refusal = await delete_sweep(connection, sweep_id)
        if refusal is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=refusal)


def create_sweep_assistant_router(
    *, database_url: str, clock: Clock, exchange_rate_reader: ExchangeRateReader
) -> APIRouter:
    """The read routes of port 8001. The user starts each sweep, so the user controls its cost and its DSR trials."""
    routes = SweepRoutes(database_url=database_url, clock=clock, exchange_rate_reader=exchange_rate_reader)
    router = APIRouter(prefix="/api")
    add_sweep_read_routes(router, routes)
    return router


def add_sweep_read_routes(router: APIRouter, routes: SweepRoutes) -> None:
    router.add_api_route("/sweeps/parameters", routes.read_parameters, methods=["GET"], responses=NOT_FOUND)
    router.add_api_route("/sweeps", routes.list_sweeps, methods=["GET"])
    router.add_api_route("/sweeps/{sweep_id}", routes.read_sweep, methods=["GET"], responses=NOT_FOUND)


def create_sweep_router(*, database_url: str, clock: Clock, exchange_rate_reader: ExchangeRateReader) -> APIRouter:
    routes = SweepRoutes(database_url=database_url, clock=clock, exchange_rate_reader=exchange_rate_reader)
    router = APIRouter(prefix="/api")
    responses: dict[int | str, dict[str, Any]] = {**REFUSED, **NOT_FOUND}
    add_sweep_read_routes(router, routes)
    router.add_api_route(
        "/sweeps", routes.start_sweep, methods=["POST"], status_code=status.HTTP_201_CREATED, responses=REFUSED
    )
    router.add_api_route("/sweeps/{sweep_id}/cancel", routes.cancel_sweep, methods=["POST"], responses=responses)
    router.add_api_route(
        "/sweeps/{sweep_id}/requeue-failed", routes.requeue_failed_runs, methods=["POST"], responses=responses
    )
    router.add_api_route(
        "/sweeps/{sweep_id}",
        routes.delete_sweep,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={**NOT_FOUND, status.HTTP_409_CONFLICT: ERROR_RESPONSE},
    )
    return router
