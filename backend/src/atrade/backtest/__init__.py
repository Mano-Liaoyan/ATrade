"""Public entry of the backtest capability: backtest runs, their results, the metric functions, backtests for
other capabilities (queue one, read its outcome, the last IDs of a strategy), and the look-back bars of `request_bars`."""

from atrade.backtest.backtest_access import (
    BacktestOutcome,
    check_backtest_request,
    queue_backtest,
    read_backtest_outcome,
    read_last_backtest_ids,
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
from atrade.backtest.backtest_run import find_look_back_length, run_backtest
from atrade.backtest.backtest_runner import BacktestRunner
from atrade.backtest.backtest_start import BacktestRefusal, start_backtest
from atrade.backtest.backtest_store import BacktestRequest, BacktestStatus
from atrade.backtest.http_routes import create_backtest_assistant_router, create_backtest_router
from atrade.backtest.strategy_engine_run import write_look_back_catalog

__all__ = [
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestRefusal",
    "BacktestRequest",
    "BacktestRunner",
    "BacktestStatus",
    "BacktestTrade",
    "EquityPoint",
    "RoundTrip",
    "calculate_daily_returns",
    "calculate_equity_curve",
    "calculate_metrics",
    "calculate_round_trip_metrics",
    "check_backtest_request",
    "create_backtest_assistant_router",
    "create_backtest_router",
    "find_look_back_length",
    "find_round_trips",
    "queue_backtest",
    "read_backtest_outcome",
    "read_last_backtest_ids",
    "run_backtest",
    "start_backtest",
    "write_look_back_catalog",
]
