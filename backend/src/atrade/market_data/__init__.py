"""Public entry of the market_data capability: instrument search."""

from atrade.market_data.http_routes import create_market_data_router

__all__ = ["create_market_data_router"]
