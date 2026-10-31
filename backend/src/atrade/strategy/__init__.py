"""Public entry of the strategy capability: strategies, strategy versions, the checks before save, code completion,
and the save of the AI assistant."""

from atrade.strategy.code_checks import CodeProblem
from atrade.strategy.http_routes import create_strategy_assistant_router, create_strategy_router
from atrade.strategy.language_server import STRATEGY_LANGUAGE_SERVER_PATH, create_strategy_language_server_router
from atrade.strategy.strategy_loading import StrategyFileError, load_strategy_classes
from atrade.strategy.strategy_parameters import StrategyParameter, read_strategy_parameters
from atrade.strategy.strategy_store import SavedVersion, StrategyVersionRecord
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.version_reading import (
    StrategyOutline,
    StrategyVersion,
    read_strategy_outline,
    read_strategy_version,
    read_strategy_versions,
)
from atrade.strategy.version_saving import save_ai_assistant_version

__all__ = [
    "STRATEGY_LANGUAGE_SERVER_PATH",
    "STRATEGY_TEMPLATE",
    "CodeProblem",
    "SavedVersion",
    "StrategyFileError",
    "StrategyOutline",
    "StrategyParameter",
    "StrategyVersion",
    "StrategyVersionRecord",
    "create_strategy_assistant_router",
    "create_strategy_language_server_router",
    "create_strategy_router",
    "load_strategy_classes",
    "read_strategy_outline",
    "read_strategy_parameters",
    "read_strategy_version",
    "read_strategy_versions",
    "save_ai_assistant_version",
]
