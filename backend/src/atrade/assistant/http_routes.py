"""Browser routes of the conversations on port 8000 (docs/architecture/assistant.md 25.11).

The metadata of a conversation is in PostgreSQL. The messages are in the JSONL file of the assistant service, so
reading the messages and deleting a conversation call the assistant service. These routes are not on port 8001.
"""

from datetime import datetime
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints

from atrade.assistant import conversation_store, prompt_store
from atrade.assistant.assistant_service import AssistantService, AssistantServiceError
from atrade.assistant.system_prompt import StartContextReader, make_fixed_part
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE

# The same limit as the CHECK constraint of assistant_conversation.title.
MAX_TITLE_LENGTH = 200

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_LENGTH)]


class CreateConversationRequest(BaseModel):
    strategy_id: int
    # The version that the browser shows when the conversation starts. The fixed part of the system prompt names it.
    version_number: int | None = Field(default=None, ge=1)


class RenameConversationRequest(BaseModel):
    title: Title


class ConversationResponse(BaseModel):
    id: int
    strategy_id: int
    title: str
    title_state: conversation_store.TitleState
    created_at_utc: datetime
    # The provider, the model, and the credential name of the last AI assistant message. None before the first answer.
    last_provider: str | None
    last_model: str | None
    last_credential_name: str | None
    # The prompt version of the conversation (25.9.1). All its runs use it.
    prompt_version_id: int
    prompt_version_number: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class ConversationMessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    # Only for an AI assistant message: its provider, model, and credential name (25.8.2).
    provider: str | None
    model: str | None
    credential_name: str | None


class ConversationDetailResponse(ConversationResponse):
    messages: list[ConversationMessageResponse]


def new_conversation_title(created_at_utc: datetime) -> str:
    """The title before the generated title: "New conversation" and the creation time in UTC (25.8.3)."""
    return f"New conversation {created_at_utc:%Y-%m-%d %H:%M} UTC"


def to_response(record: conversation_store.ConversationRecord) -> ConversationResponse:
    return ConversationResponse(
        id=record.id,
        strategy_id=record.strategy_id,
        title=record.title,
        title_state=record.title_state,
        created_at_utc=record.created_at_utc,
        last_provider=record.last_provider,
        last_model=record.last_model,
        last_credential_name=record.last_credential_name,
        prompt_version_id=record.prompt_version_id,
        prompt_version_number=record.prompt_version_number,
    )


def conversation_not_found(conversation_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"The conversation {conversation_id} does not exist.")


def assistant_not_reachable(error: AssistantServiceError) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))


class ConversationRoutes:
    """The route functions. They share the database URL, the clock, the assistant service, and the prompt parts."""

    def __init__(
        self,
        *,
        database_url: str,
        clock: Clock,
        assistant_service: AssistantService,
        read_start_context: StartContextReader,
        default_prompt_text: str,
    ) -> None:
        self.database_url = database_url
        self.clock = clock
        self.assistant_service = assistant_service
        self.read_start_context = read_start_context
        self.default_prompt_text = default_prompt_text

    async def list_conversations(self, strategy_id: int) -> ConversationListResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            records = await conversation_store.select_conversations(connection, strategy_id)
        return ConversationListResponse(conversations=[to_response(record) for record in records])

    async def create_conversation(self, request: CreateConversationRequest) -> ConversationResponse:
        """The conversation records the latest prompt version and the fixed part of the system prompt (25.9)."""
        strategy_missing = HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"The strategy {request.strategy_id} does not exist."
        )
        start_context = await self.read_start_context(request.strategy_id, request.version_number)
        if start_context is None:
            raise strategy_missing
        created_at_utc = self.clock.read_now_utc()
        async with (
            await psycopg.AsyncConnection.connect(self.database_url) as connection,
            connection.transaction(),
        ):
            prompt_version = await prompt_store.select_or_insert_latest_version(
                connection, default_text=self.default_prompt_text, created_at_utc=created_at_utc
            )
            record = await conversation_store.insert_conversation(
                connection,
                strategy_id=request.strategy_id,
                title=new_conversation_title(created_at_utc),
                created_at_utc=created_at_utc,
                prompt_version_id=prompt_version.id,
                fixed_prompt=make_fixed_part(start_context),
            )
        if record is None:
            raise strategy_missing
        return to_response(record)

    async def read_conversation(self, conversation_id: int) -> ConversationDetailResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            record = await conversation_store.select_conversation(connection, conversation_id)
        if record is None:
            raise conversation_not_found(conversation_id)
        try:
            messages = await self.assistant_service.read_messages(conversation_id)
        except AssistantServiceError as error:
            raise assistant_not_reachable(error) from error
        return ConversationDetailResponse(
            **to_response(record).model_dump(),
            messages=[
                ConversationMessageResponse(
                    role=message.role,
                    text=message.text,
                    provider=message.provider,
                    model=message.model,
                    credential_name=message.credential_name,
                )
                for message in messages
            ],
        )

    async def rename_conversation(
        self, conversation_id: int, request: RenameConversationRequest
    ) -> ConversationResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            record = await conversation_store.rename_conversation(connection, conversation_id, request.title)
        if record is None:
            raise conversation_not_found(conversation_id)
        return to_response(record)

    async def delete_conversation(self, conversation_id: int) -> None:
        """Deletes the JSONL file first. When the assistant service is not reachable, the row stays for a new try."""
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if await conversation_store.select_conversation(connection, conversation_id) is None:
                raise conversation_not_found(conversation_id)
            try:
                await self.assistant_service.delete_conversation(conversation_id)
            except AssistantServiceError as error:
                raise assistant_not_reachable(error) from error
            await conversation_store.delete_conversation(connection, conversation_id)


def create_conversation_router(
    *,
    database_url: str,
    clock: Clock,
    assistant_service: AssistantService,
    read_start_context: StartContextReader,
    default_prompt_text: str,
) -> APIRouter:
    routes = ConversationRoutes(
        database_url=database_url,
        clock=clock,
        assistant_service=assistant_service,
        read_start_context=read_start_context,
        default_prompt_text=default_prompt_text,
    )
    router = APIRouter(prefix="/api/assistant/conversations")
    router.add_api_route("", routes.list_conversations, methods=["GET"])
    router.add_api_route(
        "",
        routes.create_conversation,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        responses={status.HTTP_404_NOT_FOUND: ERROR_RESPONSE},
    )
    router.add_api_route(
        "/{conversation_id}",
        routes.read_conversation,
        methods=["GET"],
        responses={
            status.HTTP_404_NOT_FOUND: ERROR_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: ERROR_RESPONSE,
        },
    )
    router.add_api_route(
        "/{conversation_id}",
        routes.rename_conversation,
        methods=["PATCH"],
        responses={status.HTTP_404_NOT_FOUND: ERROR_RESPONSE},
    )
    router.add_api_route(
        "/{conversation_id}",
        routes.delete_conversation,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_404_NOT_FOUND: ERROR_RESPONSE,
            status.HTTP_503_SERVICE_UNAVAILABLE: ERROR_RESPONSE,
        },
    )
    return router
