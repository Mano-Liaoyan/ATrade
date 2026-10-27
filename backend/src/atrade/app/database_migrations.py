"""Runs the Alembic migrations in backend/migrations. The Web entry and the tests call it at start."""

from pathlib import Path

from alembic import command
from alembic.config import Config

# src/atrade/app/database_migrations.py -> backend/migrations. The project is installed in editable mode.
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def upgrade_database(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
