"""The connection of web to the assistant service (docs/architecture/assistant.md 25.14).

The assistant service listens on port 8002 in the network atrade-assistant-internal. web calls it over HTTP:

- `POST /conversations/{id}/runs` with the user message and the model selection. The answer is one JSON line for each
  pi event that web needs: `text_delta`, `message_end` (with the model and the credential name), and `error`.
- `POST /conversations/{id}/steer`, `POST /conversations/{id}/abort`.
- `POST /conversations/{id}/title`: one model call without tools. `502` with `detail` when it fails.
- `GET /conversations/{id}/messages`: the messages of the JSONL file.
- `DELETE /conversations/{id}`: stops the run and deletes the JSONL file.

`AssistantService` is the interface. The tests use a fake of it (tests/fakes/assistant.py).
"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

# The service name in deploy/compose.yaml and the port of assistant/src/main.ts.
ASSISTANT_SERVICE_URL = "http://assistant:8002"
CONNECT_TIMEOUT_SECONDS = 5.0
# A title is one short model call.
REQUEST_TIMEOUT_SECONDS = 120.0
HTTP_OK = 200
HTTP_NO_CONTENT = 204


class AssistantServiceError(Exception):
    """The assistant service is not reachable, or it refused the request. The text names the reason."""


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str
    credential_id: str


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class MessageEnd:
    text: str
    provider: str
    model: str
    credential_name: str


@dataclass(frozen=True)
class RunError:
    message: str


type RunEvent = TextDelta | MessageEnd | RunError


@dataclass(frozen=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    text: str
    provider: str | None
    model: str | None
    credential_name: str | None


class AssistantService(Protocol):
    def run(self, conversation_id: int, text: str, selection: ModelSelection) -> AsyncIterator[RunEvent]:
        """Runs one user message. The iterator ends when the run is settled."""
        ...

    async def steer(self, conversation_id: int, text: str) -> bool:
        """Adds a user message to the active run. False when the conversation has no active run."""
        ...

    async def abort(self, conversation_id: int) -> None: ...

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str: ...

    async def read_messages(self, conversation_id: int) -> list[ConversationMessage]: ...

    async def delete_conversation(self, conversation_id: int) -> None: ...


def to_run_event(event: dict[str, Any]) -> RunEvent | None:
    """The run event of one line of the assistant service, or None for an event that web does not use."""
    match event.get("type"):
        case "text_delta":
            return TextDelta(text=str(event["delta"]))
        case "message_end":
            return MessageEnd(
                text=str(event["text"]),
                provider=str(event["provider"]),
                model=str(event["model"]),
                credential_name=str(event["credential_name"]),
            )
        case "error":
            return RunError(message=str(event["message"]))
        case _:
            return None


def read_run_event(line: str) -> RunEvent | None:
    if not line:
        return None
    try:
        return to_run_event(json.loads(line))
    except ValueError, KeyError, TypeError, AttributeError:
        message = f"The assistant service sent a line that is not a run event: {line[:200]}"
        raise AssistantServiceError(message) from None


def not_reachable(error: httpx.HTTPError) -> AssistantServiceError:
    return AssistantServiceError(f"The assistant service is not reachable: {error}")


def read_detail(response: httpx.Response) -> str:
    try:
        return str(response.json()["detail"])
    except ValueError, KeyError, TypeError:
        return f"The assistant service answered {response.status_code}."


def selection_body(selection: ModelSelection) -> dict[str, str]:
    return {"provider": selection.provider, "model": selection.model, "credential_id": selection.credential_id}


class AssistantServiceClient:
    """AssistantService over HTTP. Each call opens its own connection."""

    def __init__(self, *, base_url: str = ASSISTANT_SERVICE_URL, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url
        self.transport = transport

    def open_client(self, *, read_timeout_seconds: float | None) -> httpx.AsyncClient:
        timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS, read=read_timeout_seconds)
        return httpx.AsyncClient(base_url=self.base_url, transport=self.transport, timeout=timeout)

    async def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
        try:
            async with self.open_client(read_timeout_seconds=REQUEST_TIMEOUT_SECONDS) as client:
                return await client.request(method, path, json=body)
        except httpx.HTTPError as error:
            raise not_reachable(error) from error

    async def run(self, conversation_id: int, text: str, selection: ModelSelection) -> AsyncIterator[RunEvent]:
        body = {"text": text, **selection_body(selection)}
        try:
            # A run has no read timeout: a tool can wait 15 minutes for a backtest (25.4.2).
            async with (
                self.open_client(read_timeout_seconds=None) as client,
                client.stream("POST", f"/conversations/{conversation_id}/runs", json=body) as response,
            ):
                if response.status_code != HTTP_OK:
                    await response.aread()
                    raise AssistantServiceError(read_detail(response))
                async for line in response.aiter_lines():
                    event = read_run_event(line)
                    if event is not None:
                        yield event
        except httpx.HTTPError as error:
            raise not_reachable(error) from error

    async def steer(self, conversation_id: int, text: str) -> bool:
        response = await self.request("POST", f"/conversations/{conversation_id}/steer", {"text": text})
        return response.status_code == HTTP_NO_CONTENT

    async def abort(self, conversation_id: int) -> None:
        await self.request("POST", f"/conversations/{conversation_id}/abort", {})

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str:
        response = await self.request("POST", f"/conversations/{conversation_id}/title", selection_body(selection))
        if response.status_code != HTTP_OK:
            raise AssistantServiceError(read_detail(response))
        return str(response.json()["title"])

    async def read_messages(self, conversation_id: int) -> list[ConversationMessage]:
        response = await self.request("GET", f"/conversations/{conversation_id}/messages")
        if response.status_code != HTTP_OK:
            raise AssistantServiceError(read_detail(response))
        messages: list[dict[str, Any]] = response.json()["messages"]
        return [
            ConversationMessage(
                role=message["role"],
                text=message["text"],
                provider=message["provider"],
                model=message["model"],
                credential_name=message["credential_name"],
            )
            for message in messages
        ]

    async def delete_conversation(self, conversation_id: int) -> None:
        response = await self.request("DELETE", f"/conversations/{conversation_id}")
        if response.status_code != HTTP_NO_CONTENT:
            raise AssistantServiceError(read_detail(response))
