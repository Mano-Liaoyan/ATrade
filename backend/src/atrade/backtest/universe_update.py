"""The custom data that tells a multi-instrument strategy the members of each universe period (#198).

The decision and the reason are in docs/architecture/backtest.md section 10.10.8. A strategy calls
`subscribe_data(DataType("UniverseUpdate"))` and gets the list in `on_data(data)` as `data.data.bar_types`.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from datetime import datetime
from typing import Final

from nautilus_trader.model import CustomData, DataType, register_custom_data_class
from nautilus_trader.model.custom import customdataclass  # pyright: ignore[reportUnknownVariableType] untyped.

from atrade.backtest.arrow_bars import convert_to_ns

UNIVERSE_UPDATE: Final = "UniverseUpdate"


@customdataclass
class UniverseUpdate:
    """The members of one universe period: their bar types, joined with commas."""

    bar_types: str = ""


register_custom_data_class(UniverseUpdate)


def make_universe_update(period_start_utc: datetime, bar_types: list[str]) -> CustomData:
    """The list of the period. `ts_event` and `ts_init` are the period start."""
    time_ns = convert_to_ns(period_start_utc)
    # readability-exception: the decorator adds the `ts_event` and `ts_init` arguments, and the type checker does
    # not see them.
    update = UniverseUpdate(time_ns, time_ns, bar_types=",".join(bar_types))  # pyright: ignore[reportCallIssue]
    return CustomData(DataType(UNIVERSE_UPDATE), update)
