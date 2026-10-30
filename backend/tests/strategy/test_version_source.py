"""The version source and the rules of a strategy version (docs/architecture/strategy.md section 9.1.1)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql

from atrade.app.database_migrations import MIGRATIONS_DIR

REVISION_BEFORE_SOURCE_AND_RULES = "8d4b6f2a1c93"
CREATED_AT_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


@pytest.fixture
def empty_database_url(migrated_database_url: str) -> Iterator[str]:
    # A unique name, so that two test runs on one PostgreSQL server do not drop the database of the other run.
    database_name = f"atrade_version_source_migration_{uuid.uuid4().hex}"
    with psycopg.connect(migrated_database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    url_parts = urlsplit(migrated_database_url)._replace(path=f"/{database_name}")
    try:
        yield urlunsplit(url_parts)
    finally:
        with psycopg.connect(migrated_database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))


def upgrade_to(database_url: str, revision: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, revision)


def test_existing_versions_get_the_source_user_and_no_rules(empty_database_url: str) -> None:
    upgrade_to(empty_database_url, REVISION_BEFORE_SOURCE_AND_RULES)
    with psycopg.connect(empty_database_url, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO strategy (name, created_at_utc) VALUES ('Old', %(now)s)", {"now": CREATED_AT_UTC}
        )
        connection.execute(
            """
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
            SELECT id, 1, 'x = 1', 'sha', %(now)s FROM strategy
            """,
            {"now": CREATED_AT_UTC},
        )

    upgrade_to(empty_database_url, "head")

    with psycopg.connect(empty_database_url) as connection:
        rows = connection.execute("SELECT source, rules FROM strategy_version").fetchall()
    assert rows == [("user", None)]


@pytest.mark.anyio
async def test_the_rules_of_a_version_cannot_be_changed(web_client: httpx.AsyncClient, database_url: str) -> None:
    await web_client.post("/api/strategies", json={"name": "Moving average"})

    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        pytest.raises(psycopg.errors.RaiseException, match="append-only"),
    ):
        connection.execute("""UPDATE strategy_version SET rules = '{"entry": []}'""")


@pytest.mark.anyio
async def test_the_source_accepts_only_user_and_rule_builder(web_client: httpx.AsyncClient, database_url: str) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    insert_version = """
        INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc, source)
        VALUES (%(strategy_id)s, %(version_number)s, 'x = 1', 'sha', %(now)s, %(source)s)
        """

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            insert_version,
            {"strategy_id": strategy["id"], "version_number": 2, "source": "user", "now": CREATED_AT_UTC},
        )
        connection.execute(
            insert_version,
            {"strategy_id": strategy["id"], "version_number": 3, "source": "rule_builder", "now": CREATED_AT_UTC},
        )
        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                insert_version,
                {"strategy_id": strategy["id"], "version_number": 4, "source": "ai_assistant", "now": CREATED_AT_UTC},
            )


@pytest.mark.anyio
async def test_a_code_save_records_the_source_user_and_no_rules(web_client: httpx.AsyncClient) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Moving average"})).json()
    template = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["code"]
    code_v2 = template.replace("average_period: int = 20", "average_period: int = 30")

    save_response = await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code_v2})

    assert save_response.json()["source"] == "user"
    assert save_response.json()["rules"] is None
    version_2 = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/2")).json()
    assert version_2["source"] == "user"
    assert version_2["rules"] is None
    strategy_after = (await web_client.get(f"/api/strategies/{strategy['id']}")).json()
    assert [version["source"] for version in strategy_after["versions"]] == ["user", "user"]
    assert all("rules" not in version for version in strategy_after["versions"])
