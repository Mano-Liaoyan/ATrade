"""The strategy template asks for a warm-up that fits the bar period, not 60 days of bars for every period.

60 days of 1-minute bars is about 23 000 bars and many IBKR historical data requests (#61 story 17).
"""

from datetime import timedelta
from typing import Any

from nautilus_trader.model import BarType

from atrade.strategy.strategy_template import STRATEGY_TEMPLATE

AVERAGE_PERIOD = 20


def load_template() -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(compile(STRATEGY_TEMPLATE, "strategy_template.py", "exec"), namespace)
    return namespace


def test_warm_up_of_1_minute_bars_is_one_week() -> None:
    warm_up_length = load_template()["find_warm_up_length"]

    assert warm_up_length(BarType.from_str("AAPL.NASDAQ-1-MINUTE-LAST-EXTERNAL"), AVERAGE_PERIOD) == timedelta(days=7)


def test_warm_up_of_1_day_bars_covers_3_average_periods() -> None:
    warm_up_length = load_template()["find_warm_up_length"]

    assert warm_up_length(BarType.from_str("AAPL.NASDAQ-1-DAY-LAST-EXTERNAL"), AVERAGE_PERIOD) == timedelta(days=60)
