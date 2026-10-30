"""Public entry of the assistant capability: the conversations with the AI assistant and /ws/assistant.

The AI assistant runs in the assistant service (docs/architecture/assistant.md 25.2). This module keeps the
conversation metadata in PostgreSQL and connects the browser to the assistant service. The credentials stay in the
assistant service (ADR 0005).
"""

from fastapi import APIRouter

from atrade.assistant.assistant_service import (
    AssistantService,
    AssistantServiceClient,
    AssistantServiceError,
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
    TextDelta,
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


__all__ = [
    "ASSISTANT_SOCKET_MESSAGE_MODELS",
    "AssistantService",
    "AssistantServiceClient",
    "AssistantServiceError",
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
    "TextDelta",
    "create_assistant_router",
]
