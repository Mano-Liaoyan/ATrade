"""GET /api/ibkr/gateway: reports if the Web process is connected to IB Gateway and IB Gateway to IBKR, and the
Gateway address."""

from fastapi import APIRouter
from pydantic import BaseModel

from atrade.ibkr.gateway_connection import GatewayConnection, GatewayStatus


class GatewayStatusResponse(BaseModel):
    status: GatewayStatus
    host: str
    port: int


def create_ibkr_router(*, gateway_connection: GatewayConnection, host: str, port: int) -> APIRouter:
    router = APIRouter()

    @router.get("/api/ibkr/gateway")
    async def read_gateway_status() -> GatewayStatusResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        return GatewayStatusResponse(status=gateway_connection.read_status(), host=host, port=port)

    return router
