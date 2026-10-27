"""The committed OpenAPI document of the frontend matches the routes of the Web app."""

import json
from pathlib import Path
from typing import Any

from atrade.app.openapi_document import SOCKET_MESSAGE_MODEL_LISTS, build_openapi_document
from atrade.foundation.socket_push import HeartbeatMessage

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


def test_document_has_the_json_schema_of_the_paper_trading_socket_messages() -> None:
    schemas = json.loads(build_openapi_document())["components"]["schemas"]

    assert schemas["PaperAccountMessage"]["properties"]["type"]["const"] == "account"
    assert schemas["PaperAccountMessage"]["properties"]["check"] == {
        "$ref": "#/components/schemas/PaperAccountCheckMessage"
    }
    assert schemas["OpenOrdersMessage"]["properties"]["type"]["const"] == "orders"
    assert schemas["OpenOrdersMessage"]["properties"]["orders"]["items"] == {
        "$ref": "#/components/schemas/OpenOrderResponse"
    }


def read_error_schema_ref(paths: dict[str, Any], path: str, method: str, status_code: str) -> str:
    return paths[path][method]["responses"][status_code]["content"]["application/json"]["schema"]["$ref"]


def test_strategy_and_backtest_routes_declare_their_error_model() -> None:
    paths = json.loads(build_openapi_document())["paths"]
    error_ref = "#/components/schemas/ErrorResponse"

    assert read_error_schema_ref(paths, "/api/strategies", "post", "409") == error_ref
    assert read_error_schema_ref(paths, "/api/strategies/{strategy_id}", "get", "404") == error_ref
    assert read_error_schema_ref(paths, "/api/strategies/{strategy_id}", "delete", "409") == error_ref
    assert read_error_schema_ref(paths, "/api/strategies/{strategy_id}/versions", "post", "404") == error_ref
    assert read_error_schema_ref(paths, "/api/backtests", "post", "422") == error_ref
    assert read_error_schema_ref(paths, "/api/backtests/{backtest_id}", "get", "404") == error_ref


def test_each_socket_message_list_has_the_heartbeat_message() -> None:
    for models in SOCKET_MESSAGE_MODEL_LISTS:
        assert HeartbeatMessage in models
