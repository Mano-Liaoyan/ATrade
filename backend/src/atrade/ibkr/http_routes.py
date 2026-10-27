"""GET /api/ibkr/gateway: reports if the Web process is connected to IB Gateway, and the Gateway address."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from atrade.ibkr.gateway_connection import GatewayConnection


class GatewayStatusResponse(BaseModel):
    status: Literal["connected", "unreachable"]
    host: str
    port: int


def create_ibkr_router(*, gateway_connection: GatewayConnection, host: str, port: int) -> APIRouter:
    router = APIRouter()

    @router.get("/api/ibkr/gateway")
    async def read_gateway_status() -> GatewayStatusResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        if gateway_connection.is_connected():
            return GatewayStatusResponse(status="connected", host=host, port=port)
        return GatewayStatusResponse(status="unreachable", host=host, port=port)

    return router
