"""HTTP routes of paper_trading: the order routes and GET /api/paper-trading/paper-capital. The router also includes
/ws/paper-trading from account_socket.py.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from atrade.foundation.clock import Clock
from atrade.ibkr import GatewayRequestError
from atrade.market_data import StockSplitConfirmedError
from atrade.paper_trading.account_socket import OwnerMessage, OwnerPositionMessage, create_account_socket_router
from atrade.paper_trading.paper_account_monitor import PaperAccountMonitor, fetch_paper_capital_usd
from atrade.paper_trading.paper_orders import (
    ManualOrderResponse,
    OrderErrorResponse,
    OrderRefusedByLedgerResponse,
    OrderRefusedResponse,
    PaperOrderRoutes,
)
from atrade.paper_trading.split_check_store import SplitCheckStatus
from atrade.paper_trading.stock_split_ledger import (
    SplitCheckNotFoundError,
    SplitCheckResolvedError,
    StockSplitLedger,
)


class PaperCapitalResponse(BaseModel):
    """The default paper capital of the backtest form (docs/architecture.md section 10)."""

    paper_capital_usd: Decimal


class SplitCheckResolvedResponse(BaseModel):
    """The split check after "Apply split" or "Keep ledger" (section 11.11)."""

    id: int
    symbol: str
    exchange: str
    currency: str
    status: SplitCheckStatus


class StockSplitAppliedResponse(BaseModel):
    split_check: SplitCheckResolvedResponse
    # The owner positions of the instrument after the ledger change.
    owners: list[OwnerPositionMessage]


class StockSplitRoutes:
    def __init__(self, ledger: StockSplitLedger) -> None:
        self.ledger = ledger

    async def apply_split(self, split_check_id: int) -> StockSplitAppliedResponse:
        try:
            split_check = await self.ledger.read_needed_check(split_check_id)
            positions = await self.ledger.apply_split(split_check_id)
        except SplitCheckNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except (SplitCheckResolvedError, StockSplitConfirmedError) as error:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
        except GatewayRequestError as error:
            # The last IBKR close (without a stored daily bar) or the forex rate of the cash in lieu.
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        return StockSplitAppliedResponse(
            split_check=SplitCheckResolvedResponse(
                id=split_check.id,
                symbol=split_check.symbol,
                exchange=split_check.exchange,
                currency=split_check.currency,
                status="applied",
            ),
            owners=[
                OwnerPositionMessage(
                    owner=OwnerMessage(kind=position.owner.kind, forward_test_id=position.owner.forward_test_id),
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                )
                for position in positions
            ],
        )

    async def keep_ledger(self, split_check_id: int) -> SplitCheckResolvedResponse:
        try:
            split_check = await self.ledger.keep_ledger(split_check_id)
        except SplitCheckNotFoundError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except SplitCheckResolvedError as error:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
        return SplitCheckResolvedResponse(
            id=split_check.id,
            symbol=split_check.symbol,
            exchange=split_check.exchange,
            currency=split_check.currency,
            status="kept",
        )


def add_stock_split_routes(router: APIRouter, routes: StockSplitRoutes) -> None:
    not_found_or_resolved: dict[int | str, dict[str, Any]] = {
        status.HTTP_404_NOT_FOUND: {"model": OrderErrorResponse},
        status.HTTP_409_CONFLICT: {"model": OrderErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": OrderErrorResponse},
    }
    router.add_api_route(
        "/api/paper-trading/stock-splits/{split_check_id}/apply",
        routes.apply_split,
        methods=["POST"],
        responses=not_found_or_resolved,
    )
    router.add_api_route(
        "/api/paper-trading/stock-splits/{split_check_id}/keep-ledger",
        routes.keep_ledger,
        methods=["POST"],
        responses=not_found_or_resolved,
    )


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
        responses={
            **refused_or_failed,
            status.HTTP_409_CONFLICT: {"model": OrderRefusedByLedgerResponse},
        },
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
) -> APIRouter:
    router = APIRouter()
    routes = PaperOrderRoutes(
        paper_account_monitor=paper_account_monitor,
        database_url=database_url,
        clock=clock,
    )
    add_order_routes(router, routes)
    add_stock_split_routes(
        router,
        StockSplitRoutes(
            StockSplitLedger(
                database_url=database_url, gateway_connection=paper_account_monitor.gateway_connection, clock=clock
            )
        ),
    )

    @router.get("/api/paper-trading/paper-capital")
    async def read_paper_capital() -> PaperCapitalResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        return PaperCapitalResponse(paper_capital_usd=await fetch_paper_capital_usd(paper_account_monitor))

    router.include_router(
        create_account_socket_router(paper_account_monitor=paper_account_monitor, ledger=routes.ledger)
    )

    return router
