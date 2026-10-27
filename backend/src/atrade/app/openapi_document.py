"""Writes the OpenAPI document of the Web app. The frontend generates its API types from this file.

Run `pnpm generate:api` in `frontend/`. It calls `python -m atrade.app.openapi_document <output file>`.
"""

import json
import sys
from pathlib import Path

from atrade.app.web import create_web_app
from atrade.foundation.clock import SystemClock
from atrade.foundation.settings import Settings
from atrade.ibkr import IbAsyncGatewayConnection

# The document needs only the routes. The app does not start, so it opens no database or Gateway connection.
UNUSED_DATABASE_URL = "postgresql://unused/atrade"
UNUSED_GATEWAY_HOST = "127.0.0.1"
UNUSED_GATEWAY_PORT = 4004
UNUSED_CLIENT_ID = 1


def build_openapi_document() -> str:
    settings = Settings(database_url=UNUSED_DATABASE_URL)
    gateway_connection = IbAsyncGatewayConnection(
        host=UNUSED_GATEWAY_HOST, port=UNUSED_GATEWAY_PORT, client_id=UNUSED_CLIENT_ID
    )
    app = create_web_app(settings=settings, clock=SystemClock(), gateway_connection=gateway_connection)
    return json.dumps(app.openapi(), indent=2) + "\n"


def main() -> None:
    output_path = Path(sys.argv[1])
    output_path.write_text(build_openapi_document())


if __name__ == "__main__":
    main()
