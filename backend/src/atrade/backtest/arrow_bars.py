"""Converts saved bars to Arrow IPC bytes. NautilusTrader 2.0 BarDataWrangler takes Arrow bytes, not a DataFrame."""

# pyarrow 26 has no type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal

import pyarrow

from atrade.foundation.bar import Bar, BarPeriod

NANOSECONDS_PER_SECOND = 1_000_000_000
# BarDataWrangler reads prices and volumes as Arrow decimal128(38, 16).
ARROW_DECIMAL_TYPE = pyarrow.decimal128(38, 16)
ARROW_DECIMAL_STEP = Decimal("1e-16")
# The default decimal context has 28 digits. A value of 13 integer digits and 16 decimal places needs more.
ARROW_DECIMAL_CONTEXT = Context(prec=38, rounding=ROUND_HALF_EVEN)


def convert_to_ns(time_utc: datetime) -> int:
    return int(time_utc.timestamp()) * NANOSECONDS_PER_SECOND


def round_to_arrow_scale(value: Decimal) -> Decimal:
    """Rounds half-even to 16 decimal places, so the error is at most 5e-17. The stock split adjustment of Databento
    bars divides numeric prices and multiplies numeric volumes in PostgreSQL. Stock splits with ratios such as 1/15
    give more than 16 decimal places, and Arrow refuses them. The rounding keeps low <= high."""
    return value.quantize(ARROW_DECIMAL_STEP, context=ARROW_DECIMAL_CONTEXT)


def convert_bars_to_arrow_bytes(bars: list[Bar], bar_period: BarPeriod) -> bytes:
    """`ts_event` is the bar end: a strategy sees a bar only after its period is over."""
    bar_end_ns = [convert_to_ns(bar.start_utc + bar_period.length) for bar in bars]
    table = pyarrow.table(
        {
            "open": pyarrow.array([round_to_arrow_scale(bar.open) for bar in bars], ARROW_DECIMAL_TYPE),
            "high": pyarrow.array([round_to_arrow_scale(bar.high) for bar in bars], ARROW_DECIMAL_TYPE),
            "low": pyarrow.array([round_to_arrow_scale(bar.low) for bar in bars], ARROW_DECIMAL_TYPE),
            "close": pyarrow.array([round_to_arrow_scale(bar.close) for bar in bars], ARROW_DECIMAL_TYPE),
            "volume": pyarrow.array([round_to_arrow_scale(bar.volume) for bar in bars], ARROW_DECIMAL_TYPE),
            "ts_event": pyarrow.array(bar_end_ns, pyarrow.uint64()),
            "ts_init": pyarrow.array(bar_end_ns, pyarrow.uint64()),
        }
    )
    sink = pyarrow.BufferOutputStream()
    with pyarrow.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    arrow_bytes: bytes = sink.getvalue().to_pybytes()
    return arrow_bytes
