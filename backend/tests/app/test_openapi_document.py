"""The committed OpenAPI document of the frontend matches the routes of the Web app."""

from pathlib import Path

from atrade.app.openapi_document import build_openapi_document

COMMITTED_OPENAPI_DOCUMENT = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "api" / "openapi.json"


def test_committed_openapi_document_matches_the_routes() -> None:
    committed_document = COMMITTED_OPENAPI_DOCUMENT.read_text()

    assert committed_document == build_openapi_document(), "Run `pnpm generate:api` in frontend/."
