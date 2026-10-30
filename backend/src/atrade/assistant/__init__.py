"""Public entry of the assistant capability: the conversations with the AI assistant and /ws/assistant.

The AI assistant runs in the assistant service (docs/architecture/assistant.md 25.2). This module keeps the
conversation metadata in PostgreSQL and connects the browser to the assistant service. The credentials stay in the
assistant service (ADR 0005).
"""

import psycopg
from fastapi import APIRouter

from atrade.assistant import conversation_store
from atrade.assistant.assistant_service import (
    AssistantService,
    AssistantServiceClient,
    AssistantServiceError,
    BacktestFinished,
    ConversationMessage,
    CredentialSummary,
    LoginEnd,
    LoginEvent,
    LoginOption,
    LoginStep,
    MessageEnd,
    ModelSelection,
    ProviderModel,
    ProviderSummary,
    RunError,
    RunEvent,
    StrategyVersionSaved,
    TextDelta,
    ToolStep,
)
from atrade.assistant.assistant_socket import ASSISTANT_SOCKET_MESSAGE_MODELS, create_assistant_socket_router
from atrade.assistant.credential_routes import create_credential_router
from atrade.assistant.http_routes import create_conversation_router
from atrade.foundation.clock import Clock


def create_assistant_router(*, database_url: str, clock: Clock, assistant_service: AssistantService) -> APIRouter:
    router = APIRouter()
    router.include_router(
        create_conversation_router(database_url=database_url, clock=clock, assistant_service=assistant_service)
    )
    router.include_router(create_credential_router(assistant_service=assistant_service))
    router.include_router(
        create_assistant_socket_router(database_url=database_url, assistant_service=assistant_service)
    )
    return router


async def conversation_exists(*, database_url: str, conversation_id: int) -> bool:
    """Port 8001 records only a conversation that exists (docs/architecture/assistant.md 25.3.2)."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await conversation_store.select_conversation(connection, conversation_id) is not None


__all__ = [
    "ASSISTANT_SOCKET_MESSAGE_MODELS",
    "AssistantService",
    "AssistantServiceClient",
    "AssistantServiceError",
    "BacktestFinished",
    "ConversationMessage",
    "CredentialSummary",
    "LoginEnd",
    "LoginEvent",
    "LoginOption",
    "LoginStep",
    "MessageEnd",
    "ModelSelection",
    "ProviderModel",
    "ProviderSummary",
    "RunError",
    "RunEvent",
    "StrategyVersionSaved",
    "TextDelta",
    "ToolStep",
    "conversation_exists",
    "create_assistant_router",
]
