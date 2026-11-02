"""IBKR stock split check program: starts with the IBKR fake and refuses an unusable client ID.

Real PostgreSQL. No real IBKR call (docs/architecture.md section 6.4).
"""

from pathlib import Path

import psycopg
import pytest

from atrade.app.ibkr_split_check import main
from atrade.market_data import import_databento_files
from tests.fakes.databento import write_dbn_files
from tests.fakes.ibkr import FakeGatewayConnection
from tests.market_data.test_stock_split_import import TRADING_DAYS, create_bars, create_history_files


def test_the_program_checks_the_waiting_instruments_and_stops_when_none_waits(
    database_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bars = create_bars("STAY", TRADING_DAYS[:3], [("50", "51", 1000)] * 3)
    import_databento_files(
        database_url=database_url,
        file_paths=write_dbn_files(tmp_path, create_history_files(bars)),
        still_trading_rule="ibkr_check",
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    client_ids: list[int] = []

    def create_fake_gateway(*, client_id: int, **_: object) -> FakeGatewayConnection:
        client_ids.append(client_id)
        return FakeGatewayConnection(managed_accounts=["DU1234567"], client_id=client_id)

    monkeypatch.setattr("atrade.app.ibkr_split_check.IbAsyncGatewayConnection", create_fake_gateway)
    caplog.set_level("INFO")

    main([])

    assert client_ids == [30]
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT count(*) FROM ibkr_split_check WHERE checked_end_utc IS NULL").fetchone()
    assert row == (0,)
    assert "Checked 1 instruments. Applied 0 stock splits. 0 stock splits wait for the check." in caplog.text


def test_the_program_refuses_client_id_0(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/atrade")

    with pytest.raises(SystemExit) as stop:
        main(["--ibkr-client-id", "0"])

    assert stop.value.code == 1
    assert "client ID 0 is not allowed" in caplog.text
