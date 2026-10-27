"""Public entry of the backtest capability: backtest runs, their results, the metric functions, backtests for
other capabilities (queue one, read its outcome), and the look-back bars of `request_bars`."""

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
from atrade.backtest.backtest_run import find_look_back_length, run_backtest
from atrade.backtest.backtest_runner import BacktestRunner
from atrade.backtest.backtest_store import BacktestRequest, BacktestStatus
from atrade.backtest.http_routes import create_backtest_router
from atrade.backtest.strategy_engine_run import write_look_back_catalog

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
    "find_look_back_length",
    "queue_backtest",
    "read_backtest_outcome",
    "run_backtest",
    "write_look_back_catalog",
]
