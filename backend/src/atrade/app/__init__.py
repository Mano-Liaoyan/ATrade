"""Program entry points. They create all dependencies by hand and connect the capabilities."""

from atrade.app.database_migrations import upgrade_database
from atrade.app.web import create_web_app

__all__ = ["create_web_app", "upgrade_database"]
