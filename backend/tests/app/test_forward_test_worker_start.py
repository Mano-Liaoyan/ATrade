"""Start of the forward-test worker: settings that are not valid stop the start and the log names the reason. The
quarterly US universe update needs DATABENTO_API_KEY (docs/architecture.md section 15, docs/architecture/market_data.md
section 8.9). A valid start blocks reads of the process before the worker starts child processes. A child gets only
the variables that it needs."""

import json
import logging
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

from atrade.app import forward_test_worker
from atrade.app.forward_test_worker import create_us_universe_update, main, start_forward_test_process
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock

# Runs in place of the forward test child: it needs IB Gateway. It reads the settings as the child does at its start.
WRITE_CHILD_FACTS_CODE = """
import json
import os
import sys
from pathlib import Path

from atrade.foundation.settings import Settings

settings = Settings()
facts = {
    "variable_names": sorted(os.environ),
    "database_url": settings.database_url,
    "ibkr_host": settings.ibkr_host,
    "ibkr_paper_port": settings.ibkr_paper_port,
}
Path(sys.argv[1]).write_text(json.dumps(facts))
"""


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


@pytest.mark.anyio
async def test_forward_test_child_gets_its_settings_and_no_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts_file = tmp_path / "child_facts.json"
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_IBKR_HOST", "gateway.example")
    monkeypatch.setenv("ATRADE_IBKR_PAPER_PORT", "4010")
    monkeypatch.setenv("ATRADE_IBKR_ACCOUNT_ID", "DU1234567")
    monkeypatch.setenv("DATABENTO_API_KEY", "db-test-key")
    monkeypatch.setenv("ATRADE_IBKR_PASSWORD", "test-password")
    monkeypatch.setattr(
        forward_test_worker,
        "FORWARD_TEST_PROCESS_COMMAND",
        [sys.executable, "-c", WRITE_CHILD_FACTS_CODE, str(facts_file)],
    )

    child = await start_forward_test_process(1, "run")
    assert await child.process.wait() == 0

    facts = json.loads(facts_file.read_text())
    assert facts["database_url"] == "postgresql://db.example/atrade"
    assert facts["ibkr_host"] == "gateway.example"
    assert facts["ibkr_paper_port"] == 4010
    assert "DATABENTO_API_KEY" not in facts["variable_names"]
    assert "ATRADE_IBKR_PASSWORD" not in facts["variable_names"]
    assert "ATRADE_IBKR_ACCOUNT_ID" not in facts["variable_names"]


def test_the_quarterly_update_does_not_run_without_a_databento_api_key_and_the_log_tells_why(
    clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=None)

    assert create_us_universe_update(settings, clock) is None
    assert "The quarterly US universe update does not run. DATABENTO_API_KEY is empty." in caplog.text


def test_the_quarterly_update_runs_with_a_databento_api_key(clock: FixedClock) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=SecretStr("db-test-key"))

    assert create_us_universe_update(settings, clock) is not None
