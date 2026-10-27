"""HTTP routes of paper_trading: the order routes and GET /api/paper-trading/paper-capital. The router also includes
/ws/paper-trading from account_socket.py.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from atrade.foundation.clock import Clock
from atrade.paper_trading.account_socket import create_account_socket_router
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor, fetch_paper_capital_usd
from atrade.paper_trading.paper_orders import (
    FindBlockingForwardTest,
    ManualOrderResponse,
    OrderBlockedResponse,
    OrderErrorResponse,
    OrderRefusedResponse,
    PaperOrderRoutes,
)


class PaperCapitalResponse(BaseModel):
    """The default paper capital of the backtest form (docs/architecture.md section 10)."""

    paper_capital_usd: Decimal


def add_order_routes(router: APIRouter, routes: PaperOrderRoutes) -> None:
    refused_or_failed: dict[int | str, dict[str, Any]] = {
        status.HTTP_403_FORBIDDEN: {"model": OrderRefusedResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": OrderErrorResponse},
    }
    router.add_api_route(
        "/api/paper-trading/orders",
        routes.send_order,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        response_model=ManualOrderResponse,
        responses={**refused_or_failed, status.HTTP_409_CONFLICT: {"model": OrderBlockedResponse}},
    )
    router.add_api_route(
        "/api/paper-trading/orders",
        routes.list_open_orders,
        methods=["GET"],
        responses={status.HTTP_502_BAD_GATEWAY: {"model": OrderErrorResponse}},
    )
    router.add_api_route(
        "/api/paper-trading/orders/{order_id}",
        routes.cancel_order,
        methods=["DELETE"],
        status_code=status.HTTP_202_ACCEPTED,
        response_model=None,
        responses={
            **refused_or_failed,
            status.HTTP_404_NOT_FOUND: {"model": OrderErrorResponse},
            status.HTTP_409_CONFLICT: {"model": OrderErrorResponse},
        },
    )
    router.add_api_route("/api/paper-trading/manual-orders", routes.list_manual_orders, methods=["GET"])


def create_paper_trading_router(
    *,
    paper_account_monitor: PaperAccountMonitor,
    database_url: str,
    clock: Clock,
    find_blocking_forward_test: FindBlockingForwardTest,
) -> APIRouter:
    """`find_blocking_forward_test` returns the forward test that runs on an instrument (section 12.2)."""
    router = APIRouter()
    routes = PaperOrderRoutes(
        paper_account_monitor=paper_account_monitor,
        database_url=database_url,
        clock=clock,
        find_blocking_forward_test=find_blocking_forward_test,
    )
    add_order_routes(router, routes)

    @router.get("/api/paper-trading/paper-capital")
    async def read_paper_capital() -> PaperCapitalResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        return PaperCapitalResponse(paper_capital_usd=await fetch_paper_capital_usd(paper_account_monitor))

    router.include_router(create_account_socket_router(paper_account_monitor=paper_account_monitor))

    return router
