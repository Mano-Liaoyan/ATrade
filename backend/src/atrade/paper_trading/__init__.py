"""Public entry of paper_trading: the paper account check, the paper account state, and /ws/paper-trading."""

from atrade.paper_trading.http_routes import create_paper_trading_router
from atrade.paper_trading.paper_account_check import PaperAccountCheck, PaperAccountCheckError, require_paper_account
from atrade.paper_trading.paper_account_monitor import (
    PaperAccountBalance,
    PaperAccountMonitor,
    fetch_paper_capital_usd,
)

__all__ = [
    "PaperAccountBalance",
    "PaperAccountCheck",
    "PaperAccountCheckError",
    "PaperAccountMonitor",
    "create_paper_trading_router",
    "fetch_paper_capital_usd",
    "require_paper_account",
]
