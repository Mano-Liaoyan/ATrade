"""Test strategy: registers the ATrade `BarClose` indicator and records the indicator value in each `on_bar`.

The indicator tests replace RECORD_FILE before they run this file as strategy code. Each line of the file is
`<bar close> <indicator value>`.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId
from nautilus_trader.trading import Strategy

from atrade.indicator import BarClose

RECORD_FILE = "/tmp/bar_close_records.txt"


class RecordBarCloseConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs: object) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class RecordBarCloseStrategy(Strategy):
    def __init__(self, config: RecordBarCloseConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.bar_close = BarClose()

    def on_start(self) -> None:
        self.register_indicator_for_bars(self.settings.bar_type, self.bar_close)
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        with Path(RECORD_FILE).open("a") as record_file:
            record_file.write(f"{bar.close.as_double()} {self.bar_close.value}\n")
