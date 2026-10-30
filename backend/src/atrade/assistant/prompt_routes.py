"""Browser routes of the prompt versions on port 8000 (docs/architecture/assistant.md 25.9, 25.11).

These routes are not on port 8001: the AI assistant cannot change its own prompt. They refuse nothing except a
text that is not valid (FastAPI's 422), so they declare no ErrorResponse.
"""

from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import APIRouter, status
from pydantic import BaseModel, StringConstraints

from atrade.assistant import prompt_store
from atrade.assistant.system_prompt import FIXED_PART_TEMPLATE
from atrade.foundation.clock import Clock

# The same limit as the CHECK constraint of assistant_prompt_version.text.
MAX_PROMPT_TEXT_LENGTH = 50000

PromptText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_PROMPT_TEXT_LENGTH)]


class SavePromptVersionRequest(BaseModel):
    text: PromptText


class PromptVersionResponse(BaseModel):
    id: int
    version_number: int
    # The editable part of the system prompt.
    text: str
    created_at_utc: datetime


class PromptVersionListResponse(BaseModel):
    # The newest first.
    prompt_versions: list[PromptVersionResponse]
    # The default editable part. "Restore default" puts it in the text area.
    default_text: str
    # The fixed part, with the names of the values that the conversation start adds.
    fixed_part: str


def to_response(record: prompt_store.PromptVersionRecord) -> PromptVersionResponse:
    return PromptVersionResponse(
        id=record.id, version_number=record.version_number, text=record.text, created_at_utc=record.created_at_utc
    )


class PromptRoutes:
    def __init__(self, *, database_url: str, clock: Clock, default_prompt_text: str) -> None:
        self.database_url = database_url
        self.clock = clock
        self.default_prompt_text = default_prompt_text

    async def list_prompt_versions(self) -> PromptVersionListResponse:
        """When no version exists, saves the default text as version 1, so the list is never empty."""
        async with (
            await psycopg.AsyncConnection.connect(self.database_url) as connection,
            connection.transaction(),
        ):
            await prompt_store.select_or_insert_latest_version(
                connection, default_text=self.default_prompt_text, created_at_utc=self.clock.read_now_utc()
            )
            records = await prompt_store.select_prompt_versions(connection)
        return PromptVersionListResponse(
            prompt_versions=[to_response(record) for record in records],
            default_text=self.default_prompt_text,
            fixed_part=FIXED_PART_TEMPLATE,
        )

    async def save_prompt_version(self, request: SavePromptVersionRequest) -> PromptVersionResponse:
        async with (
            await psycopg.AsyncConnection.connect(self.database_url) as connection,
            connection.transaction(),
        ):
            await prompt_store.lock_prompt_versions(connection)
            record = await prompt_store.insert_prompt_version(
                connection, text=request.text, created_at_utc=self.clock.read_now_utc()
            )
        return to_response(record)


def create_prompt_router(*, database_url: str, clock: Clock, default_prompt_text: str) -> APIRouter:
    routes = PromptRoutes(database_url=database_url, clock=clock, default_prompt_text=default_prompt_text)
    router = APIRouter(prefix="/api/assistant/prompt-versions")
    router.add_api_route("", routes.list_prompt_versions, methods=["GET"])
    router.add_api_route(
        "",
        routes.save_prompt_version,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
    )
    return router
