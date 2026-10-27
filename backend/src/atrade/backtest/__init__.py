"""Public entry of the backtest capability: backtest runs, their results, the metric functions, and backtests for
other capabilities (queue one, read its outcome)."""

from atrade.backtest.backtest_access import (
    BacktestOutcome,
    check_backtest_request,
    queue_backtest,
    read_backtest_outcome,
)
from atrade.backtest.backtest_metrics import (
    BacktestMetrics,
    BacktestTrade,
    EquityPoint,
    calculate_equity_curve,
    calculate_metrics,
)
from atrade.backtest.backtest_run import run_backtest
from atrade.backtest.backtest_runner import BacktestRunner
from atrade.backtest.backtest_store import BacktestRequest, BacktestStatus
from atrade.backtest.http_routes import create_backtest_router

__all__ = [
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestRequest",
    "BacktestRunner",
    "BacktestStatus",
    "BacktestTrade",
    "EquityPoint",
    "calculate_equity_curve",
    "calculate_metrics",
    "check_backtest_request",
    "create_backtest_router",
    "queue_backtest",
    "read_backtest_outcome",
    "run_backtest",
]
