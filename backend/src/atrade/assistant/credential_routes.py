"""Browser routes of the providers and the credentials on port 8000 (docs/architecture/assistant.md 25.7, 25.11).

The credentials are in the credential file of the assistant service, not in PostgreSQL (ADR 0005). `web` keeps no
credential and no secret: these routes only read the list without secrets, and delete. The login runs on
/ws/assistant, because it asks questions and waits for answers. These routes are not on port 8001.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel

from atrade.assistant.assistant_service import (
    AssistantService,
    AssistantServiceError,
    CredentialSummary,
    ThinkingLevel,
)
from atrade.foundation.error_response import ERROR_RESPONSE

# The credential IDs of the assistant service are UUIDs. The pattern keeps the ID one path segment.
CREDENTIAL_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"


class ProviderModelResponse(BaseModel):
    id: str
    name: str
    # The thinking levels of the model, in the order of pi. Only "off" for a model without reasoning.
    thinking_levels: list[ThinkingLevel]


class ProviderResponse(BaseModel):
    id: str
    name: str
    # "oauth" is a subscription login, "api_key" an API key (25.7.1).
    login_methods: list[Literal["oauth", "api_key"]]
    # Only the models of the stored credentials of the provider. A provider without a credential has none.
    models: list[ProviderModelResponse]


class ProviderListResponse(BaseModel):
    providers: list[ProviderResponse]


class CredentialResponse(BaseModel):
    id: str
    name: str
    provider: str
    type: Literal["oauth", "api_key"]
    # The last 4 characters of an API key. None for a subscription login.
    key_last4: str | None
    # "failed": the last OAuth refresh failed. The user deletes the credential and logs in again.
    state: Literal["ready", "failed"]
    state_message: str | None


class CredentialListResponse(BaseModel):
    credentials: list[CredentialResponse]


def to_credential_response(credential: CredentialSummary) -> CredentialResponse:
    return CredentialResponse(
        id=credential.id,
        name=credential.name,
        provider=credential.provider,
        type=credential.type,
        key_last4=credential.key_last4,
        state=credential.state,
        state_message=credential.state_message,
    )


def assistant_not_reachable(error: AssistantServiceError) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))


class CredentialRoutes:
    def __init__(self, *, assistant_service: AssistantService) -> None:
        self.assistant_service = assistant_service

    async def list_providers(self) -> ProviderListResponse:
        try:
            providers = await self.assistant_service.list_providers()
        except AssistantServiceError as error:
            raise assistant_not_reachable(error) from error
        return ProviderListResponse(
            providers=[
                ProviderResponse(
                    id=provider.id,
                    name=provider.name,
                    login_methods=provider.login_methods,
                    models=[
                        ProviderModelResponse(id=model.id, name=model.name, thinking_levels=model.thinking_levels)
                        for model in provider.models
                    ],
                )
                for provider in providers
            ]
        )

    async def list_credentials(self) -> CredentialListResponse:
        try:
            credentials = await self.assistant_service.list_credentials()
        except AssistantServiceError as error:
            raise assistant_not_reachable(error) from error
        return CredentialListResponse(credentials=[to_credential_response(credential) for credential in credentials])

    async def delete_credential(self, credential_id: Annotated[str, Path(pattern=CREDENTIAL_ID_PATTERN)]) -> None:
        try:
            deleted = await self.assistant_service.delete_credential(credential_id)
        except AssistantServiceError as error:
            raise assistant_not_reachable(error) from error
        if not deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"The credential {credential_id} does not exist.")


def create_credential_router(*, assistant_service: AssistantService) -> APIRouter:
    routes = CredentialRoutes(assistant_service=assistant_service)
    router = APIRouter(prefix="/api/assistant")
    not_reachable: dict[int | str, dict[str, Any]] = {status.HTTP_503_SERVICE_UNAVAILABLE: ERROR_RESPONSE}
    router.add_api_route("/providers", routes.list_providers, methods=["GET"], responses=not_reachable)
    router.add_api_route("/credentials", routes.list_credentials, methods=["GET"], responses=not_reachable)
    router.add_api_route(
        "/credentials/{credential_id}",
        routes.delete_credential,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={status.HTTP_404_NOT_FOUND: ERROR_RESPONSE, **not_reachable},
    )
    return router
