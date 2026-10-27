"""Public entry of the backtest capability: backtest runs, their results, and the metric functions."""

from atrade.backtest.backtest_metrics import (
    BacktestMetrics,
    BacktestTrade,
    EquityPoint,
    calculate_equity_curve,
    calculate_metrics,
)
from atrade.backtest.backtest_run import run_backtest
from atrade.backtest.backtest_runner import BacktestRunner
from atrade.backtest.http_routes import create_backtest_router

__all__ = [
    "BacktestMetrics",
    "BacktestRunner",
    "BacktestTrade",
    "EquityPoint",
    "calculate_equity_curve",
    "calculate_metrics",
    "create_backtest_router",
    "run_backtest",
]
