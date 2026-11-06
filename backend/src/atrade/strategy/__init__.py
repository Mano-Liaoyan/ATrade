"""Public entry of the strategy capability: strategies, strategy versions, the checks before save, code completion,
the chart indicators of the code, and the save of the AI assistant."""

from atrade.strategy.chart_indicators import ChartIndicator, list_chart_indicators
from atrade.strategy.code_checks import CodeProblem
from atrade.strategy.code_syntax import find_backtest_only_orders
from atrade.strategy.http_routes import STRATEGY_CHANGE_SOCKET, create_strategy_assistant_router, create_strategy_router
from atrade.strategy.language_server import STRATEGY_LANGUAGE_SERVER_PATH, create_strategy_language_server_router
from atrade.strategy.strategy_account import FORWARD_TEST_VENUE, find_account
from atrade.strategy.strategy_loading import StrategyFileError, load_strategy_classes
from atrade.strategy.strategy_parameters import StrategyParameter, read_strategy_parameters
from atrade.strategy.strategy_store import SavedVersion
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.version_reading import (
    StrategyVersion,
    list_version_chart_indicators,
    read_strategy_outline,
    read_strategy_version,
    read_strategy_versions,
)
from atrade.strategy.version_saving import save_ai_assistant_version

__all__ = [
    "FORWARD_TEST_VENUE",
    "STRATEGY_CHANGE_SOCKET",
    "STRATEGY_LANGUAGE_SERVER_PATH",
    "STRATEGY_TEMPLATE",
    "ChartIndicator",
    "CodeProblem",
    "SavedVersion",
    "StrategyFileError",
    "StrategyParameter",
    "StrategyVersion",
    "create_strategy_assistant_router",
    "create_strategy_language_server_router",
    "create_strategy_router",
    "find_account",
    "find_backtest_only_orders",
    "list_chart_indicators",
    "list_version_chart_indicators",
    "load_strategy_classes",
    "read_strategy_outline",
    "read_strategy_parameters",
    "read_strategy_version",
    "read_strategy_versions",
    "save_ai_assistant_version",
]
