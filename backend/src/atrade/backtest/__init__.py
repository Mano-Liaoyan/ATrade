"""Public entry of the backtest capability: backtest runs, their results, the metric functions (with PSR and DSR), backtests for
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
    RoundTrip,
    calculate_daily_returns,
    calculate_equity_curve,
    calculate_metrics,
    calculate_round_trip_metrics,
    find_round_trips,
)
from atrade.backtest.backtest_run import LookBack, find_look_back, run_backtest
from atrade.backtest.backtest_runner import BacktestRunner
from atrade.backtest.backtest_store import BacktestRequest, BacktestStatus
from atrade.backtest.http_routes import create_backtest_router
from atrade.backtest.sharpe_probability import (
    calculate_deflated_sharpe,
    calculate_probabilistic_sharpe,
    find_sharpe_probability_status,
)
from atrade.backtest.strategy_engine_run import write_look_back_catalog

__all__ = [
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestRequest",
    "BacktestRunner",
    "BacktestStatus",
    "BacktestTrade",
    "EquityPoint",
    "LookBack",
    "RoundTrip",
    "calculate_daily_returns",
    "calculate_deflated_sharpe",
    "calculate_equity_curve",
    "calculate_metrics",
    "calculate_probabilistic_sharpe",
    "calculate_round_trip_metrics",
    "check_backtest_request",
    "create_backtest_router",
    "find_look_back",
    "find_round_trips",
    "find_sharpe_probability_status",
    "queue_backtest",
    "read_backtest_outcome",
    "run_backtest",
    "write_look_back_catalog",
]
