"""The public entry of the indicator capability (docs/architecture/indicator.md section 23.3).

Strategy code imports the classes from here and registers them with `register_indicator_for_bars`. A screen gives
each saved `foundation` bar to `update`.
"""

from atrade.indicator.bar_close import BarClose
from atrade.indicator.channels import BollingerBands, DonchianChannel
from atrade.indicator.moving_averages import EMA, MACD, SMA
from atrade.indicator.wilder_averages import ATR, RSI

__all__ = ["ATR", "EMA", "MACD", "RSI", "SMA", "BarClose", "BollingerBands", "DonchianChannel"]
