"""Public entry of paper_trading: the paper account check, the paper account state, orders by hand, and
/ws/paper-trading."""

from atrade.paper_trading.account_socket import PAPER_TRADING_SOCKET_MESSAGE_MODELS
from atrade.paper_trading.http_routes import create_paper_trading_router
from atrade.paper_trading.paper_account_check import PaperAccountCheck, PaperAccountCheckError, require_paper_account
from atrade.paper_trading.paper_account_monitor import (
    PaperAccountBalance,
    PaperAccountMonitor,
    fetch_paper_capital_usd,
)
from atrade.paper_trading.paper_orders import BlockingForwardTest, FindBlockingForwardTest

__all__ = [
    "PAPER_TRADING_SOCKET_MESSAGE_MODELS",
    "BlockingForwardTest",
    "FindBlockingForwardTest",
    "PaperAccountBalance",
    "PaperAccountCheck",
    "PaperAccountCheckError",
    "PaperAccountMonitor",
    "create_paper_trading_router",
    "fetch_paper_capital_usd",
    "require_paper_account",
]
