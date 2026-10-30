"""The AST reading of the strategy parameters (docs/architecture/backtest.md section 10.11.1)."""

from atrade.strategy import StrategyParameter, read_strategy_parameters

CODE = """
import sys
sys.exit("the reading must not run the code")

from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy


class SweepConfig(StrategyConfig):
    def __init__(
        self,
        *,
        instrument_id,
        bar_type,
        universe: list = [],
        fast_period: int = 10,
        threshold: float = 0.5,
        use_stop: bool = True,
        slow_period: int,
        untyped = 3,
        label: str = "a",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)


class SweepStrategy(Strategy):
    pass
"""


def test_reading_finds_only_typed_int_float_and_bool_fields_with_defaults() -> None:
    parameters = read_strategy_parameters(CODE)

    assert parameters == [
        StrategyParameter(name="fast_period", type="int", default=10),
        StrategyParameter(name="threshold", type="float", default=0.5),
        StrategyParameter(name="use_stop", type="bool", default=True),
    ]


def test_code_with_a_syntax_error_has_no_parameters() -> None:
    assert read_strategy_parameters("class (") == []
