"""The public entry of the indicator capability (docs/architecture/indicator.md section 23.3).

Strategy code imports the classes from here and registers them with `register_indicator_for_bars`.
"""

from atrade.indicator.bar_close import BarClose

__all__ = ["BarClose"]
