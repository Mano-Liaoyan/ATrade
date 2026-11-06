"""Converts saved bars to Arrow IPC bytes. NautilusTrader 2.0 BarDataWrangler takes Arrow bytes, not a DataFrame."""

# pyarrow 26 has no type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportUnknownParameterType=false

from datetime import datetime
from decimal import Context, Decimal

import pyarrow

from atrade.foundation.bar import Bar, BarPeriod, find_bar_end

NANOSECONDS_PER_SECOND = 1_000_000_000
# BarDataWrangler reads prices and volumes as Arrow decimal128(38, 16).
ARROW_DECIMAL_TYPE = pyarrow.decimal128(38, 16)
ARROW_DECIMAL_PLACES = Decimal(1).scaleb(-16)
ARROW_DECIMAL_CONTEXT = Context(prec=38)


def convert_to_ns(time_utc: datetime) -> int:
    return int(time_utc.timestamp()) * NANOSECONDS_PER_SECOND


def to_arrow_decimals(values: list[Decimal]) -> pyarrow.Array:
    """SQL division at a stock split stores more than 16 decimal places, and pyarrow refuses them."""
    return pyarrow.array(
        [value.quantize(ARROW_DECIMAL_PLACES, context=ARROW_DECIMAL_CONTEXT) for value in values], ARROW_DECIMAL_TYPE
    )


def convert_bars_to_arrow_bytes(bars: list[Bar], bar_period: BarPeriod) -> bytes:
    """`ts_event` is the bar end: a strategy sees a bar only after its period is over."""
    bar_end_ns = [convert_to_ns(find_bar_end(bar.start_utc, bar_period)) for bar in bars]
    table = pyarrow.table(
        {
            "open": to_arrow_decimals([bar.open for bar in bars]),
            "high": to_arrow_decimals([bar.high for bar in bars]),
            "low": to_arrow_decimals([bar.low for bar in bars]),
            "close": to_arrow_decimals([bar.close for bar in bars]),
            "volume": to_arrow_decimals([bar.volume for bar in bars]),
            "ts_event": pyarrow.array(bar_end_ns, pyarrow.uint64()),
            "ts_init": pyarrow.array(bar_end_ns, pyarrow.uint64()),
        }
    )
    sink = pyarrow.BufferOutputStream()
    with pyarrow.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    arrow_bytes: bytes = sink.getvalue().to_pybytes()
    return arrow_bytes
