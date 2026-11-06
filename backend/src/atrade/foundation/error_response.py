"""The body of a refused HTTP request. FastAPI HTTPException sends {"detail": "<reason>"}.

Routes declare it with `responses=` (ERROR_RESPONSE), so the frontend gets the type from the OpenAPI document
(docs/architecture.md section 13). A request that does not validate gets FastAPI's 422 body: a list in `detail`.
"""

import json
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel


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
    gives a 422 and not a 500 at encoding."""

    async def send_validation_error(_request: Request, error: Exception) -> Response:
        errors = jsonable_encoder(error.errors() if isinstance(error, RequestValidationError) else [])
        detail = [{key: value for key, value in item.items() if key != "input"} for item in errors]
        return Response(
            json.dumps({"detail": detail}),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            media_type="application/json",
        )

    app.add_exception_handler(RequestValidationError, send_validation_error)
