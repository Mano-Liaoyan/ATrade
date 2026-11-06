"""Start of the forward-test worker: settings that are not valid stop the start and the log names the reason. The
quarterly US universe update needs DATABENTO_API_KEY (docs/architecture.md section 15, docs/architecture/market_data.md
section 8.9). A valid start blocks reads of the process before the worker starts child processes."""

import logging

import pytest
from pydantic import SecretStr

from atrade.app import forward_test_worker
from atrade.app.forward_test_worker import create_us_universe_update, main
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock


def test_does_not_start_when_the_bar_fetcher_client_id_is_in_the_forward_test_range(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_IBKR_BAR_FETCHER_CLIENT_ID", "11")
    caplog.set_level(logging.ERROR)

    with pytest.raises(SystemExit) as stop:
        main()

    assert stop.value.code == 1
    assert "The forward-test worker does not start" in caplog.text
    assert "bar fetcher client ID 11 is inside the forward test client ID range" in caplog.text


def test_blocks_reads_of_the_process_before_the_worker_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    steps: list[str] = []

    async def record_run_worker(_: Settings) -> None:
        steps.append("run")

    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setattr(forward_test_worker, "block_process_reads", lambda: steps.append("block"))
    monkeypatch.setattr(forward_test_worker, "run_worker", record_run_worker)

    main()

    assert steps == ["block", "run"]


def test_the_quarterly_update_does_not_run_without_a_databento_api_key_and_the_log_tells_why(
    clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=None)

    assert create_us_universe_update(settings, clock) is None
    assert "The quarterly US universe update does not run. DATABENTO_API_KEY is empty." in caplog.text


def test_the_quarterly_update_runs_with_a_databento_api_key(clock: FixedClock) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=SecretStr("db-test-key"))

    assert create_us_universe_update(settings, clock) is not None
