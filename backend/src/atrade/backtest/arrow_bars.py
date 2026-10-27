"""Converts saved bars to Arrow IPC bytes. NautilusTrader 2.0 BarDataWrangler takes Arrow bytes, not a DataFrame."""

# pyarrow 26 has no type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from datetime import datetime

import pyarrow

from atrade.foundation.bar import Bar, BarPeriod

NANOSECONDS_PER_SECOND = 1_000_000_000
# BarDataWrangler reads prices and volumes as Arrow decimal128(38, 16).
ARROW_DECIMAL_TYPE = pyarrow.decimal128(38, 16)


def convert_to_ns(time_utc: datetime) -> int:
    return int(time_utc.timestamp()) * NANOSECONDS_PER_SECOND


def convert_bars_to_arrow_bytes(bars: list[Bar], bar_period: BarPeriod) -> bytes:
    """`ts_event` is the bar end: a strategy sees a bar only after its period is over."""
    bar_end_ns = [convert_to_ns(bar.start_utc + bar_period.length) for bar in bars]
    table = pyarrow.table(
        {
            "open": pyarrow.array([bar.open for bar in bars], ARROW_DECIMAL_TYPE),
            "high": pyarrow.array([bar.high for bar in bars], ARROW_DECIMAL_TYPE),
            "low": pyarrow.array([bar.low for bar in bars], ARROW_DECIMAL_TYPE),
            "close": pyarrow.array([bar.close for bar in bars], ARROW_DECIMAL_TYPE),
            "volume": pyarrow.array([bar.volume for bar in bars], ARROW_DECIMAL_TYPE),
            "ts_event": pyarrow.array(bar_end_ns, pyarrow.uint64()),
            "ts_init": pyarrow.array(bar_end_ns, pyarrow.uint64()),
        }
    )
    sink = pyarrow.BufferOutputStream()
    with pyarrow.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    arrow_bytes: bytes = sink.getvalue().to_pybytes()
    return arrow_bytes
