"""Alembic environment. Migrations contain only SQL (op.execute). There is no autogenerate and no ORM metadata."""

import os

from alembic import context
from sqlalchemy import create_engine

POSTGRES_SCHEME = "postgresql://"
PSYCOPG_SCHEME = "postgresql+psycopg://"


def read_database_url() -> str:
    configured_url = context.config.attributes.get("database_url")
    if isinstance(configured_url, str):
        return configured_url
    return os.environ["DATABASE_URL"]


def run_migrations() -> None:
    # SQLAlchemy picks psycopg 3 only with an explicit driver name in the URL.
    database_url = read_database_url().replace(POSTGRES_SCHEME, PSYCOPG_SCHEME, 1)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
