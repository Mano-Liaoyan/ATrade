"""Writes the OpenAPI document of the Web app. The frontend generates its API types from this file.

OpenAPI does not describe WebSocket messages. The JSON Schema of each WebSocket message model is added to
`components.schemas`, so the frontend gets those types from the same file.

Run `vp run generate:api` in `frontend/`. It calls `python -m atrade.app.openapi_document <output file>`.
"""

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from atrade.app.web import create_web_app
from atrade.forward_test import FORWARD_TEST_SOCKET_MESSAGE_MODELS
from atrade.foundation.clock import SystemClock
from atrade.foundation.settings import Settings
from atrade.ibkr import IbAsyncGatewayConnection
from atrade.market_data import MARKET_DATA_SOCKET_MESSAGE_MODELS
from atrade.paper_trading import PAPER_TRADING_SOCKET_MESSAGE_MODELS

# The document needs only the routes. The app does not start, so it opens no database or Gateway connection.
UNUSED_DATABASE_URL = "postgresql://unused/atrade"
UNUSED_GATEWAY_HOST = "127.0.0.1"
UNUSED_GATEWAY_PORT = 4004
UNUSED_CLIENT_ID = 1
SCHEMA_REF_TEMPLATE = "#/components/schemas/{model}"
# One list per /ws/ route. Each list has HeartbeatMessage; add_socket_message_schemas adds it once.
SOCKET_MESSAGE_MODEL_LISTS: list[list[type[BaseModel]]] = [
    MARKET_DATA_SOCKET_MESSAGE_MODELS,
    FORWARD_TEST_SOCKET_MESSAGE_MODELS,
    PAPER_TRADING_SOCKET_MESSAGE_MODELS,
]
SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = list(
    dict.fromkeys(model for models in SOCKET_MESSAGE_MODEL_LISTS for model in models)
)


def add_socket_message_schemas(document: dict[str, Any], models: list[type[BaseModel]]) -> None:
    """Adds the JSON Schema of each model, and of the models that it uses, to `components.schemas`."""
    _, top_schema = models_json_schema([(model, "serialization") for model in models], ref_template=SCHEMA_REF_TEMPLATE)
    schemas: dict[str, Any] = document.setdefault("components", {}).setdefault("schemas", {})
    for name, schema in top_schema.get("$defs", {}).items():
        if name in schemas and schemas[name] != schema:
            message = f"The WebSocket message schema {name} has the name of a different OpenAPI schema."
            raise ValueError(message)
        schemas[name] = schema


def build_openapi_document() -> str:
    settings = Settings(database_url=UNUSED_DATABASE_URL)
    gateway_connection = IbAsyncGatewayConnection(
        host=UNUSED_GATEWAY_HOST, port=UNUSED_GATEWAY_PORT, client_id=UNUSED_CLIENT_ID
    )
    app = create_web_app(settings=settings, clock=SystemClock(), gateway_connection=gateway_connection)
    document = app.openapi()
    add_socket_message_schemas(document, SOCKET_MESSAGE_MODELS)
    return json.dumps(document, indent=2) + "\n"


def main() -> None:
    output_path = Path(sys.argv[1])
    output_path.write_text(build_openapi_document())


if __name__ == "__main__":
    main()
