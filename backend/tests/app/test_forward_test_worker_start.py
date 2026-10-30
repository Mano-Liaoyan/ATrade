"""Forward-test worker entry: the quarterly US universe update needs DATABENTO_API_KEY
(docs/architecture.md section 15, docs/architecture/market_data.md section 8.9)."""

import pytest
from pydantic import SecretStr

from atrade.app.forward_test_worker import create_us_universe_update
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock


def test_the_quarterly_update_does_not_run_without_a_databento_api_key_and_the_log_tells_why(
    clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=None)

    assert create_us_universe_update(settings, clock) is None
    assert "The quarterly US universe update does not run. DATABENTO_API_KEY is empty." in caplog.text


def test_the_quarterly_update_runs_with_a_databento_api_key(clock: FixedClock) -> None:
    settings = Settings(database_url="postgresql://localhost/atrade", databento_api_key=SecretStr("db-test-key"))

    assert create_us_universe_update(settings, clock) is not None
