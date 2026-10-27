"""The committed OpenAPI document of the frontend matches the routes of the Web app."""

import json
from pathlib import Path

from atrade.app.openapi_document import build_openapi_document

COMMITTED_OPENAPI_DOCUMENT = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "api" / "openapi.json"


def test_committed_openapi_document_matches_the_routes() -> None:
    committed_document = COMMITTED_OPENAPI_DOCUMENT.read_text()

    assert committed_document == build_openapi_document(), "Run `pnpm generate:api` in frontend/."


def test_document_has_the_json_schema_of_the_websocket_messages() -> None:
    schemas = json.loads(build_openapi_document())["components"]["schemas"]

    assert schemas["LiveBarMessage"]["properties"]["bar"] == {"$ref": "#/components/schemas/BarResponse"}
    assert schemas["LiveBarMessage"]["properties"]["type"]["const"] == "bar"
    assert schemas["LiveBarErrorMessage"]["required"] == ["detail"]
    assert schemas["HeartbeatMessage"]["properties"]["type"]["const"] == "heartbeat"
