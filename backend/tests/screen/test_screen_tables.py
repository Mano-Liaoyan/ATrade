"""The constraints of the screen tables (docs/architecture/screen.md section 24.4)."""

from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.types.json import Jsonb

NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def insert_screen(connection: psycopg.Connection, *, name: str = "Momentum", market: str = "US") -> int:
    row = connection.execute(
        """
        INSERT INTO screen (name, market, definition, kept, created_at_utc, updated_at_utc)
        VALUES (%(name)s, %(market)s, %(definition)s, true, %(now)s, %(now)s)
        RETURNING id
        """,
        {"name": name, "market": market, "definition": Jsonb({}), "now": NOW_UTC},
    ).fetchone()
    assert row is not None
    return int(row[0])


def insert_screen_result(connection: psycopg.Connection, screen_id: int) -> int:
    row = connection.execute(
        """
        INSERT INTO screen_result (
            screen_id, run_at_utc, definition, market, daily_bars_date, run_seconds,
            start_count, after_filters_count, after_indicator_conditions_count, result_count
        )
        VALUES (%(screen_id)s, %(now)s, %(definition)s, 'US', '2026-01-01', 0.5, 10, 5, 2, 2)
        RETURNING id
        """,
        {"screen_id": screen_id, "now": NOW_UTC, "definition": Jsonb({})},
    ).fetchone()
    assert row is not None
    return int(row[0])


def insert_row(connection: psycopg.Connection, screen_result_id: int, position: int) -> None:
    connection.execute(
        """
        INSERT INTO screen_result_row (screen_result_id, position, symbol, exchange, currency, values)
        VALUES (%(id)s, %(position)s, 'AAPL', 'NASDAQ', 'USD', %(values)s)
        """,
        {"id": screen_result_id, "position": position, "values": Jsonb({})},
    )


def count_rows_and_exclusions(connection: psycopg.Connection) -> tuple[int, int]:
    row = connection.execute(
        "SELECT (SELECT count(*) FROM screen_result_row), (SELECT count(*) FROM screen_result_exclusion)"
    ).fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


def test_the_screen_name_is_unique(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        insert_screen(connection, name="Momentum")
        with pytest.raises(psycopg.errors.UniqueViolation):
            insert_screen(connection, name="Momentum")


@pytest.mark.parametrize("name", ["", "x" * 101])
def test_the_screen_name_has_1_to_100_characters(database_url: str, name: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection, pytest.raises(psycopg.errors.CheckViolation):
        insert_screen(connection, name=name)


def test_the_market_is_us_or_hk(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        insert_screen(connection, name="US screen", market="US")
        insert_screen(connection, name="HK screen", market="HK")
        with pytest.raises(psycopg.errors.CheckViolation):
            insert_screen(connection, name="JP screen", market="JP")


def test_a_screen_result_row_position_is_unique_in_its_result(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        screen_result_id = insert_screen_result(connection, insert_screen(connection))
        insert_row(connection, screen_result_id, 1)
        with pytest.raises(psycopg.errors.UniqueViolation):
            insert_row(connection, screen_result_id, 1)


def test_a_delete_of_a_screen_result_deletes_its_rows_and_exclusions(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        screen_result_id = insert_screen_result(connection, insert_screen(connection))
        insert_row(connection, screen_result_id, 1)
        connection.execute(
            """
            INSERT INTO screen_result_exclusion (screen_result_id, symbol, exchange, currency, reason)
            VALUES (%(id)s, 'MSFT', 'NASDAQ', 'USD', 'No value: RSI(14)')
            """,
            {"id": screen_result_id},
        )

        connection.execute("DELETE FROM screen_result WHERE id = %(id)s", {"id": screen_result_id})

        assert count_rows_and_exclusions(connection) == (0, 0)


def test_a_delete_of_a_conversation_keeps_its_screens_and_screen_results(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        strategy = connection.execute(
            "INSERT INTO strategy (name, created_at_utc) VALUES ('SMA', %(now)s) RETURNING id", {"now": NOW_UTC}
        ).fetchone()
        assert strategy is not None
        prompt_version = connection.execute(
            """
            INSERT INTO assistant_prompt_version (version_number, text, created_at_utc)
            VALUES (1, 'Prompt', %(now)s) RETURNING id
            """,
            {"now": NOW_UTC},
        ).fetchone()
        assert prompt_version is not None
        conversation = connection.execute(
            """
            INSERT INTO assistant_conversation (strategy_id, title, created_at_utc, prompt_version_id, fixed_prompt)
            VALUES (%(strategy_id)s, 'Talk', %(now)s, %(prompt_version_id)s, '') RETURNING id
            """,
            {"strategy_id": strategy[0], "now": NOW_UTC, "prompt_version_id": prompt_version[0]},
        ).fetchone()
        assert conversation is not None
        screen_id = insert_screen(connection)
        screen_result_id = insert_screen_result(connection, screen_id)
        connection.execute("UPDATE screen SET assistant_conversation_id = %(id)s", {"id": conversation[0]})
        connection.execute("UPDATE screen_result SET assistant_conversation_id = %(id)s", {"id": conversation[0]})

        connection.execute("DELETE FROM assistant_conversation")

        screen = connection.execute(
            "SELECT assistant_conversation_id FROM screen WHERE id = %(id)s", {"id": screen_id}
        ).fetchone()
        result = connection.execute(
            "SELECT assistant_conversation_id FROM screen_result WHERE id = %(id)s", {"id": screen_result_id}
        ).fetchone()
        assert (screen, result) == ((None,), (None,))
