"""Test strategy: registers one `atrade.indicator` class and records its outputs in each `on_bar`.

The indicator tests replace the record file line, the indicator line, and the outputs line before they run this file
as strategy code. Each line of the record file is a JSON list with the outputs of one bar (null is "no value").
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

import json
from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId
from nautilus_trader.trading import Strategy

import atrade.indicator

RECORD_FILE = "/tmp/indicator_records.txt"


class RecordIndicatorOutputsConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs: object) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class RecordIndicatorOutputsStrategy(Strategy):
    def __init__(self, config: RecordIndicatorOutputsConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.indicator = atrade.indicator.SMA()

    def on_start(self) -> None:
        self.register_indicator_for_bars(self.settings.bar_type, self.indicator)
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        outputs = [self.indicator.value]
        with Path(RECORD_FILE).open("a") as record_file:
            record_file.write(json.dumps(outputs) + "\n")
