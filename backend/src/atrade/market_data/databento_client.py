"""Databento client: downloads the files of a batch job that the user bought, and the EQUS.SUMMARY daily bars of
the quarterly US universe update (docs/architecture.md section 6.2, docs/architecture/market_data.md section 8.9).

`market_data` holds the Databento client. `ibkr` stays IBKR only. Tests use `tests/fakes/databento.py`.
"""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import databento

SUMMARY_DATASET = "EQUS.SUMMARY"
DAILY_SCHEMA = "ohlcv-1d"
ISO_DATE_LENGTH = 10
ISO_SECONDS_LENGTH = 19


class DatabentoClient(Protocol):
    def download_batch_job(self, job_id: str, output_dir: Path) -> list[Path]:
        """Downloads all files of a done batch job to `<output_dir>/<job_id>/` and returns their paths."""
        ...

    def read_daily_summary_end_utc(self) -> datetime:
        """The end (not included) of the EQUS.SUMMARY data that is available now."""
        ...

    def download_daily_summary(self, start: date, end: date, output_dir: Path) -> Path:
        """Downloads the EQUS.SUMMARY `ohlcv-1d` bars of all symbols from `start` to `end` (not included) to one DBN
        file in `output_dir` and returns its path. This costs money (about 1.3 USD for a quarter)."""
        ...


def parse_range_end(value: str) -> datetime:
    """Databento writes a date or an ISO 8601 time with nanoseconds, for example 2026-10-29T00:00:00.000000000Z."""
    if len(value) <= ISO_DATE_LENGTH:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    return datetime.fromisoformat(value[:ISO_SECONDS_LENGTH]).replace(tzinfo=UTC)


class DatabentoHistoricalClient:
    """The real client. A download of a done batch job does not cost again for 30 days (section 8.8.1)."""

    def __init__(self, api_key: str) -> None:
        self.historical = databento.Historical(key=api_key)

    def download_batch_job(self, job_id: str, output_dir: Path) -> list[Path]:
        return self.historical.batch.download(job_id=job_id, output_dir=output_dir)

    def read_daily_summary_end_utc(self) -> datetime:
        return parse_range_end(self.historical.metadata.get_dataset_range(dataset=SUMMARY_DATASET)["end"])

    def download_daily_summary(self, start: date, end: date, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"equs-summary-{start:%Y%m%d}-{end:%Y%m%d}.{DAILY_SCHEMA}.dbn.zst"
        self.historical.timeseries.get_range(
            dataset=SUMMARY_DATASET, schema=DAILY_SCHEMA, symbols="ALL_SYMBOLS", start=start, end=end, path=path
        )
        return path
