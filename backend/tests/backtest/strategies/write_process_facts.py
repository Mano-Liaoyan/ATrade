"""Test strategy: writes facts about its own process to a log file at start, and can loop forever in `on_bar`.

The facts are the environment variables, `oom_score_adj`, the niceness, and the process ID. The isolation tests
replace PROCESS_FACTS_FILE and LOOP_FOREVER_IN_ON_BAR before they save this file as a strategy version.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

import json
import os
from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId
from nautilus_trader.trading import Strategy

PROCESS_FACTS_FILE = "/tmp/process_facts.json"
LOOP_FOREVER_IN_ON_BAR = False


class ProcessFactsConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs: object) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class ProcessFactsStrategy(Strategy):
    def __init__(self, config: ProcessFactsConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.bar_count = 0

    def on_start(self) -> None:
        process_facts = {
            "environment": dict(os.environ),
            "oom_score_adj": int(Path("/proc/self/oom_score_adj").read_text()),
            "niceness": os.nice(0),
            "process_id": os.getpid(),
        }
        Path(PROCESS_FACTS_FILE).write_text(json.dumps(process_facts))
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        while LOOP_FOREVER_IN_ON_BAR:
            self.bar_count += 1
