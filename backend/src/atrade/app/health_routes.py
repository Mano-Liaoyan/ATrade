"""GET /api/health: reports if the Web process reaches PostgreSQL, and the server time."""

from datetime import datetime
from typing import Literal

import psycopg
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from atrade.foundation.clock import Clock

DATABASE_CONNECT_TIMEOUT_SECONDS = 3


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unreachable"]
    time_utc: datetime


async def can_reach_database(database_url: str) -> bool:
    try:
        async with await psycopg.AsyncConnection.connect(
            database_url, connect_timeout=DATABASE_CONNECT_TIMEOUT_SECONDS
        ) as connection:
            await connection.execute("SELECT 1")
    except psycopg.OperationalError:
        return False
    return True


def create_health_router(*, database_url: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    async def read_health(response: Response) -> HealthResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        is_database_reachable = await can_reach_database(database_url)
        time_utc = clock.read_now_utc()
        if is_database_reachable:
            return HealthResponse(status="ok", database="ok", time_utc=time_utc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="unreachable", time_utc=time_utc)

    return router
