"""The schema end of a Databento dataset range (docs/architecture/market_data.md section 8.9, #350)."""

from datetime import UTC, datetime

from atrade.market_data.databento_client import find_schema_end

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
