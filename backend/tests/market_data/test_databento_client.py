"""The schema end of a Databento dataset range (#350) and the file of a daily summary download
(docs/architecture/market_data.md section 8.9). No test calls Databento."""

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from databento.common.error import BentoError, BentoServerError
from databento.common.validation import validate_file_write_path

from atrade.market_data.databento_client import (
    DatabentoDownloadNotStartedError,
    DatabentoHistoricalClient,
    find_schema_end,
)

DATASET_END = "2026-11-03T15:20:00.000000000Z"


def test_schema_end_comes_from_the_schema_range() -> None:
    dataset_range: dict[str, object] = {
        "start": "2024-07-01T00:00:00.000000000Z",
        "end": DATASET_END,
        "schema": {"ohlcv-1d": {"start": "2024-07-01T00:00:00.000000000Z", "end": "2026-11-03T00:00:00.000000000Z"}},
    }

    assert find_schema_end(dataset_range, "ohlcv-1d") == datetime(2026, 11, 3, tzinfo=UTC)


def test_schema_end_without_the_schema_is_the_day_start_of_the_dataset_end() -> None:
    dataset_range: dict[str, object] = {"start": "2024-07-01", "end": DATASET_END, "schema": {"ohlcv-1h": {}}}

    assert find_schema_end(dataset_range, "ohlcv-1d") == datetime(2026, 11, 3, tzinfo=UTC)


def test_schema_end_without_schema_ranges_is_the_day_start_of_the_dataset_end() -> None:
    assert find_schema_end({"end": DATASET_END}, "ohlcv-1d") == datetime(2026, 11, 3, tzinfo=UTC)


class StreamedTimeseries:
    """`timeseries.get_range` of databento 0.87: it refuses a path that exists, and a failed stream leaves a partial
    file."""

    def __init__(self, failures: int, http_failures: int = 0) -> None:
        self.failures = failures
        self.http_failures = http_failures

    def get_range(self, *, path: Path, **_: object) -> None:
        validate_file_write_path(path, "path")
        if self.http_failures > 0:
            self.http_failures -= 1
            raise BentoServerError(http_status=503)
        with path.open("xb") as writer:
            writer.write(b"partial")
            if self.failures > 0:
                self.failures -= 1
                raise BentoError
            writer.write(b" and complete")


def create_client(failures: int, monkeypatch: pytest.MonkeyPatch, http_failures: int = 0) -> DatabentoHistoricalClient:
    client = DatabentoHistoricalClient("db-no-real-key")
    timeseries = StreamedTimeseries(failures, http_failures)
    monkeypatch.setattr(client, "historical", SimpleNamespace(timeseries=timeseries))
    return client


def test_a_failed_download_leaves_no_file_at_the_final_path_and_the_next_download_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = create_client(1, monkeypatch)
    with pytest.raises(BentoError):
        client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)
    assert [path.name for path in tmp_path.iterdir() if path.name.startswith("equs-summary")] == []

    path = client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)

    assert path.read_bytes() == b"partial and complete"
    assert list(tmp_path.iterdir()) == [path]


def test_a_second_download_of_the_same_range_replaces_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client(0, monkeypatch)
    client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)

    path = client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)

    assert path.read_bytes() == b"partial and complete"


def test_an_http_error_before_the_data_is_a_download_that_did_not_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = create_client(0, monkeypatch, http_failures=1)

    with pytest.raises(DatabentoDownloadNotStartedError):
        client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)


def test_a_stream_that_stops_is_not_a_download_that_did_not_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = create_client(1, monkeypatch)

    with pytest.raises(BentoError):
        client.download_daily_summary(date(2024, 9, 22), date(2025, 1, 1), tmp_path)
