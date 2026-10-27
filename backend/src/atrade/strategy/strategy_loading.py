"""Loads the code of a strategy version and finds its Strategy and StrategyConfig classes.

Backtests and forward tests run strategy versions with it. Only child processes call it, because it runs user code.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy

STRATEGY_MODULE_NAME = "strategy_version"


class StrategyFileError(ValueError):
    """The strategy file does not have the required classes. The message is the error that the user sees."""


def load_strategy_module(code: str, work_directory: Path) -> ModuleType:
    """Imports the strategy code from a file, so that tracebacks show its line numbers."""
    code_file = work_directory / f"{STRATEGY_MODULE_NAME}.py"
    code_file.write_text(code)
    module_spec = importlib.util.spec_from_file_location(STRATEGY_MODULE_NAME, code_file)
    if module_spec is None or module_spec.loader is None:
        message = f"Python cannot load {code_file}."
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(module_spec)
    # readability-exception: running the user strategy code is the purpose of a backtest and a forward test (E1).
    module_spec.loader.exec_module(module)
    return module


def find_strategy_classes(module: ModuleType) -> tuple[type[Strategy], type[StrategyConfig]]:
    """The checks before save make sure that the file has exactly 1 subclass of each (strategy.md section 9.3)."""
    defined_classes = [
        value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__
    ]
    strategy_classes = [value for value in defined_classes if issubclass(value, Strategy)]
    config_classes = [value for value in defined_classes if issubclass(value, StrategyConfig)]
    if len(strategy_classes) != 1 or len(config_classes) != 1:
        message = "The strategy file must have exactly 1 Strategy subclass and 1 StrategyConfig subclass."
        raise StrategyFileError(message)
    return strategy_classes[0], config_classes[0]


def load_strategy_classes(code: str, work_directory: Path) -> tuple[type[Strategy], type[StrategyConfig]]:
    """Writes the code to `work_directory`, imports it, and returns its classes. Raises StrategyFileError."""
    return find_strategy_classes(load_strategy_module(code, work_directory))
