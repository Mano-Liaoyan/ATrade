"""Databento fake: writes small hand-made DBN files, the format of a Databento batch download.

`FakeDatabentoClient` has the same functions as `DatabentoClient` of the `market_data` public entry. It never calls
Databento (docs/architecture.md section 17.3). Tests set `batch_jobs` and the EQUS.SUMMARY records, and read the downloads.
No mock library is used.
"""

from collections.abc import Sequence
from compression import zstd
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import databento_dbn
import databento_dbn.metadata

NEW_YORK = ZoneInfo("America/New_York")
# DBN prices are integers in units of 1e-9 (fixed-point).
PRICE_SCALE = Decimal(10**9)
# The publisher IDs of the datasets. The import does not read them.
PUBLISHER_IDS = {"XNAS.ITCH": 2, "XNYS.PILLAR": 9, "EQUS.SUMMARY": 95}
# The stubs of databento_dbn type the enum members as plain values, so the fake builds them from their values.
DAILY_SCHEMA = databento_dbn.Schema.from_str("ohlcv-1d")
STATISTICS_SCHEMA = databento_dbn.Schema.from_str("statistics")
OPENING_PRICE = databento_dbn.StatType.from_int(1)
CLOSE_PRICE = databento_dbn.StatType.from_int(11)


@dataclass(frozen=True)
class DailyRecord:
    """One `ohlcv-1d` record of one symbol on one trading day."""

    symbol: str
    trading_day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class StatisticRecord:
    """One `statistics` record. `stat_type` 1 is the official open and 11 the official close."""

    symbol: str
    trading_day: date
    stat_type: databento_dbn.StatType
    price: Decimal
    # The exchange time of the statistic, in New York time on the trading day.
    time_et: time = time(16, 0)


@dataclass(frozen=True)
class DbnFile:
    """One file of a batch job: one dataset and one schema, from `start` (included) to `end` (not included)."""

    dataset: str
    schema: databento_dbn.Schema
    start: date
    end: date
    daily_records: list[DailyRecord] = field(default_factory=list[DailyRecord])
    statistic_records: list[StatisticRecord] = field(default_factory=list[StatisticRecord])

    @property
    def file_name(self) -> str:
        return f"{self.dataset.lower().replace('.', '-')}-{self.start:%Y%m%d}.{self.schema.value}.dbn.zst"


# The DBN metadata takes objects with these attributes (`databento_dbn.metadata`).
@dataclass
class MappingInterval:
    start_date: date
    end_date: date
    symbol: str


@dataclass
class SymbolMapping:
    raw_symbol: str
    intervals: Sequence[databento_dbn.metadata.MappingInterval]


def to_nanoseconds(moment: datetime) -> int:
    return int(moment.timestamp()) * 10**9


def to_day_nanoseconds(day: date) -> int:
    return to_nanoseconds(datetime.combine(day, time(), tzinfo=UTC))


def to_fixed_price(price: Decimal) -> int:
    return int(price * PRICE_SCALE)


def find_symbols(dbn_file: DbnFile) -> list[str]:
    symbols = [record.symbol for record in dbn_file.daily_records]
    symbols += [record.symbol for record in dbn_file.statistic_records]
    return sorted(set(symbols))


def encode_daily_record(publisher_id: int, instrument_id: int, record: DailyRecord) -> bytes:
    message = databento_dbn.OHLCVMsg(
        databento_dbn.RType.OHLCV_1D,
        publisher_id,
        instrument_id,
        to_day_nanoseconds(record.trading_day),
        to_fixed_price(record.open),
        to_fixed_price(record.high),
        to_fixed_price(record.low),
        to_fixed_price(record.close),
        record.volume,
    )
    return bytes(message)


def encode_statistic_record(publisher_id: int, instrument_id: int, record: StatisticRecord) -> bytes:
    event_ns = to_nanoseconds(datetime.combine(record.trading_day, record.time_et, tzinfo=NEW_YORK))
    message = databento_dbn.StatMsg(
        publisher_id,
        instrument_id,
        event_ns,
        event_ns,
        databento_dbn.UNDEF_TIMESTAMP,
        to_fixed_price(record.price),
        databento_dbn.UNDEF_STAT_QUANTITY,
        record.stat_type,
        update_action=databento_dbn.StatUpdateAction.from_int(1),
    )
    return bytes(message)


def encode_dbn_file(dbn_file: DbnFile) -> bytes:
    """The metadata maps each raw symbol to one instrument ID for the full time range, like `ALL_SYMBOLS` does."""
    symbols = find_symbols(dbn_file)
    instrument_ids = {symbol: position + 1 for position, symbol in enumerate(symbols)}
    metadata = databento_dbn.Metadata(
        dataset=dbn_file.dataset,
        start=to_day_nanoseconds(dbn_file.start),
        end=to_day_nanoseconds(dbn_file.end),
        stype_in=databento_dbn.SType.from_str("raw_symbol"),
        stype_out=databento_dbn.SType.from_str("instrument_id"),
        schema=dbn_file.schema,
        symbols=["ALL_SYMBOLS"],
        mappings=[
            SymbolMapping(symbol, [MappingInterval(dbn_file.start, dbn_file.end, str(instrument_ids[symbol]))])
            for symbol in symbols
        ],
    )
    publisher_id = PUBLISHER_IDS[dbn_file.dataset]
    encoded = [bytes(metadata)]
    encoded += [
        encode_daily_record(publisher_id, instrument_ids[record.symbol], record)
        for record in sorted(dbn_file.daily_records, key=lambda record: record.trading_day)
    ]
    encoded += [
        encode_statistic_record(publisher_id, instrument_ids[record.symbol], record)
        for record in sorted(dbn_file.statistic_records, key=lambda record: record.trading_day)
    ]
    return zstd.compress(b"".join(encoded))


def write_dbn_files(directory: Path, dbn_files: list[DbnFile]) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for dbn_file in dbn_files:
        path = directory / dbn_file.file_name
        path.write_bytes(encode_dbn_file(dbn_file))
        paths.append(path)
    return paths


class FakeDatabentoClient:
    """`summary_records` are the EQUS.SUMMARY daily bars that Databento has. Only the records before
    `summary_end` are available. Tests change `summary_end` to make a bar available later."""

    def __init__(
        self,
        batch_jobs: dict[str, list[DbnFile]] | None = None,
        summary_records: list[DailyRecord] | None = None,
        summary_end: date = date(2000, 1, 1),
    ) -> None:
        self.batch_jobs = batch_jobs or {}
        self.summary_records = summary_records or []
        self.summary_end = summary_end
        self.downloaded_job_ids: list[str] = []
        self.summary_downloads: list[tuple[date, date]] = []
        self.summary_end_reads = 0

    def download_batch_job(self, job_id: str, output_dir: Path) -> list[Path]:
        """Writes the files of the batch job to `<output_dir>/<job_id>/`, like `batch.download` of Databento."""
        self.downloaded_job_ids.append(job_id)
        return write_dbn_files(output_dir / job_id, self.batch_jobs[job_id])

    def read_daily_summary_end_utc(self) -> datetime:
        self.summary_end_reads += 1
        return datetime.combine(self.summary_end, time(), tzinfo=UTC)

    def download_daily_summary(self, start: date, end: date, output_dir: Path) -> Path:
        """Databento refuses a range after the available end, so the fake refuses it too."""
        if end > self.summary_end:
            message = f"The EQUS.SUMMARY data ends on {self.summary_end}. The request ends on {end}."
            raise ValueError(message)
        self.summary_downloads.append((start, end))
        records = [record for record in self.summary_records if start <= record.trading_day < end]
        dbn_file = DbnFile("EQUS.SUMMARY", DAILY_SCHEMA, start, end, daily_records=records)
        return write_dbn_files(output_dir, [dbn_file])[0]
