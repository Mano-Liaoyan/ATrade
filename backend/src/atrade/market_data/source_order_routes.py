"""HTTP routes of the global source order (docs/architecture/market_data.md section 8.7.3)."""

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from atrade.foundation.clock import Clock
from atrade.market_data.bar_source import BarSource, check_source_order, select_source_order, update_source_order


class SourceOrderBody(BaseModel):
    """The global source order: the first bar source that saved a time range gives all bars of the range."""

    source_order: list[BarSource]


def create_source_order_router(*, database_url: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.get("/api/market-data/source-order")
    async def read_source_order(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
    ) -> SourceOrderBody:
        async with await psycopg.AsyncConnection.connect(database_url) as connection:
            return SourceOrderBody(source_order=await select_source_order(connection))

    # A refused source order is a 422 with a `detail` text, like a request that FastAPI refuses.
    @router.put("/api/market-data/source-order")
    async def save_source_order(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        body: SourceOrderBody,
    ) -> SourceOrderBody:
        problem = check_source_order(body.source_order)
        if problem is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=problem)
        async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
            await update_source_order(connection, body.source_order, clock.read_now_utc())
        return SourceOrderBody(source_order=body.source_order)

    return router
