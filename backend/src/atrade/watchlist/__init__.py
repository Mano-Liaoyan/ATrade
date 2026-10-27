"""Public entry of the watchlist capability: add, delete, and list the instruments that the user saves."""

from atrade.watchlist.http_routes import create_watchlist_router

__all__ = ["create_watchlist_router"]
