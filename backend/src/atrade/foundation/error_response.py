"""The body of a refused HTTP request. FastAPI HTTPException sends {"detail": "<reason>"}.

Routes declare it with `responses=` (ERROR_RESPONSE), so the frontend gets the type from the OpenAPI document
(docs/architecture.md section 13). A request that does not validate gets FastAPI's 422 body: a list in `detail`.
"""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


ERROR_RESPONSE: dict[str, Any] = {"model": ErrorResponse}
# A 422 can also be FastAPI's validation error, with a list of field errors (HTTPValidationError) in `detail`.
REFUSED_OR_NOT_VALID_RESPONSE: dict[str, Any] = {
    "model": ErrorResponse,
    "description": "The request is refused (detail is a text), or a field is not valid (detail is a list).",
}
