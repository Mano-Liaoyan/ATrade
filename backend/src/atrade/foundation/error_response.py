"""The body of a refused HTTP request. FastAPI HTTPException sends {"detail": "<reason>"}.

Routes declare it with `responses=` (ERROR_RESPONSE), so the frontend gets the type from the OpenAPI document
(docs/architecture.md section 13). A request that does not validate gets FastAPI's 422 body: a list in `detail`.
"""

import json
import logging
from typing import Any

import psycopg
from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

UNSTORABLE_VALUE_MESSAGE = "The database cannot store a value of the request: a NUL character or a number out of range."


class ErrorResponse(BaseModel):
    detail: str


ERROR_RESPONSE: dict[str, Any] = {"model": ErrorResponse}
# A 422 can also be FastAPI's validation error, with a list of field errors (HTTPValidationError) in `detail`.
REFUSED_OR_NOT_VALID_RESPONSE: dict[str, Any] = {
    "model": ErrorResponse,
    "description": "The request is refused (detail is a text), or a field is not valid (detail is a list).",
}


def add_validation_error_handler(app: FastAPI) -> None:
    """FastAPI's 422 body without `input`. json.dumps writes each text as ASCII, so a lone surrogate in the request
    gives a 422 and not a 500 at encoding.

    The same 422 for a value that passes the route and that PostgreSQL refuses. This one handler covers all routes."""

    def send_field_errors(detail: list[dict[str, Any]]) -> Response:
        return Response(
            json.dumps({"detail": detail}),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            media_type="application/json",
        )

    async def send_validation_error(_request: Request, error: Exception) -> Response:
        errors = jsonable_encoder(error.errors() if isinstance(error, RequestValidationError) else [])
        return send_field_errors([{key: value for key, value in item.items() if key != "input"} for item in errors])

    async def send_unstorable_value_error(_request: Request, error: Exception) -> Response:
        logger.warning("PostgreSQL refused a value of a request: %s", error)
        return send_field_errors([{"type": "value_error", "loc": ["request"], "msg": UNSTORABLE_VALUE_MESSAGE}])

    app.add_exception_handler(RequestValidationError, send_validation_error)
    app.add_exception_handler(psycopg.DataError, send_unstorable_value_error)
