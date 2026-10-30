"""Public entry of the strategy capability: strategies, strategy versions, the checks before save, and code completion."""

from atrade.strategy.http_routes import create_strategy_router
from atrade.strategy.language_server import STRATEGY_LANGUAGE_SERVER_PATH, create_strategy_language_server_router
from atrade.strategy.strategy_loading import StrategyFileError, load_strategy_classes
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from atrade.strategy.version_reading import (
    StrategyOutline,
    StrategyVersion,
    read_strategy_outline,
    read_strategy_version,
    read_strategy_versions,
)

__all__ = [
    "STRATEGY_LANGUAGE_SERVER_PATH",
    "STRATEGY_TEMPLATE",
    "StrategyFileError",
    "StrategyOutline",
    "StrategyVersion",
    "create_strategy_language_server_router",
    "create_strategy_router",
    "load_strategy_classes",
    "read_strategy_outline",
    "read_strategy_version",
    "read_strategy_versions",
]
