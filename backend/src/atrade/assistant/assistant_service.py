"""The connection of web to the assistant service (docs/architecture/assistant.md 25.14).

The assistant service listens on port 8002 in the network atrade-assistant-internal. web calls it over HTTP:

- `POST /conversations/{id}/runs` with the user message, the model selection, and the system prompt. The answer is one
  JSON line for each pi event that web needs: `text_delta`, `message_end` (with the model and the credential name),
  `error`, and the tool events `tool_step`, `strategy_version_saved`, and `backtest_finished` (25.10).
- `POST /conversations/{id}/steer`, `POST /conversations/{id}/abort`.
- `POST /conversations/{id}/title`: one model call without tools. `502` with `detail` when it fails.
- `GET /conversations/{id}/messages`: the messages of the JSONL file.
- `DELETE /conversations/{id}`: stops the run and deletes the JSONL file.
- `GET /providers`, `GET /credentials`, `DELETE /credentials/{id}` (25.7). No answer holds a secret.
- `POST /logins` with the provider, the method, and the credential name. The answer is one JSON line for each login
  event: `login_step`, then `login_end` with the new credential, or `error`. Closing the request stops the login.
- `POST /login-answers` with the prompt ID and the value: the answer of the browser to a login step `prompt`.

`AssistantService` is the interface. The tests use a fake of it (tests/fakes/assistant.py).
"""

import json
from collections.abc import AsyncIterator, Callable
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
HTTP_NOT_FOUND = 404


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


@dataclass(frozen=True)
class ToolStep:
    """The start, an update (onUpdate), or the end of one tool call."""

    tool_call_id: str
    tool_name: str
    status: Literal["running", "succeeded", "failed"]
    # run_backtest only: the backtest and its queue state or run state.
    backtest_id: int | None
    backtest_status: str | None


@dataclass(frozen=True)
class StrategyVersionSaved:
    strategy_id: int
    strategy_version_id: int
    version_number: int


@dataclass(frozen=True)
class BacktestFinished:
    backtest_id: int


type RunEvent = TextDelta | MessageEnd | RunError | ToolStep | StrategyVersionSaved | BacktestFinished

TOOL_STEP_STATUSES: dict[str, Literal["running", "succeeded", "failed"]] = {
    "running": "running",
    "succeeded": "succeeded",
    "failed": "failed",
}

type LoginMethod = Literal["oauth", "api_key"]
type CredentialType = Literal["oauth", "api_key"]
type CredentialState = Literal["ready", "failed"]
type LoginStepKind = Literal["auth_url", "device_code", "progress", "info", "prompt"]
type LoginPromptType = Literal["text", "secret", "select", "manual_code"]


@dataclass(frozen=True)
class ProviderModel:
    id: str
    name: str


@dataclass(frozen=True)
class ProviderSummary:
    """A provider of pi with its login methods, and the models of its stored credentials (25.7.1)."""

    id: str
    name: str
    login_methods: list[LoginMethod]
    models: list[ProviderModel]


@dataclass(frozen=True)
class CredentialSummary:
    """A stored credential without its secret. An API key shows only its last 4 characters (25.7.4)."""

    id: str
    name: str
    provider: str
    type: CredentialType
    key_last4: str | None
    # "failed": the last OAuth refresh failed, so the user must log in again. `state_message` names the reason.
    state: CredentialState
    state_message: str | None


@dataclass(frozen=True)
class LoginOption:
    id: str
    label: str


@dataclass(frozen=True)
class LoginStep:
    """One login step of pi: a notify() event, or a prompt() request that waits for a login answer (25.7.3)."""

    step: LoginStepKind
    message: str | None = None
    url: str | None = None
    user_code: str | None = None
    prompt_id: str | None = None
    prompt_type: LoginPromptType | None = None
    options: list[LoginOption] | None = None


@dataclass(frozen=True)
class LoginEnd:
    credential: CredentialSummary


type LoginEvent = LoginStep | LoginEnd | RunError


@dataclass(frozen=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    text: str
    provider: str | None
    model: str | None
    credential_name: str | None


class AssistantService(Protocol):
    def run(
        self, conversation_id: int, text: str, selection: ModelSelection, system_prompt: str
    ) -> AsyncIterator[RunEvent]:
        """Runs one user message with the system prompt of the conversation. The iterator ends at the settled run."""
        ...

    async def steer(self, conversation_id: int, text: str) -> bool:
        """Adds a user message to the active run. False when the conversation has no active run."""
        ...

    async def abort(self, conversation_id: int) -> None: ...

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str: ...

    async def read_messages(self, conversation_id: int) -> list[ConversationMessage]: ...

    async def delete_conversation(self, conversation_id: int) -> None: ...

    async def list_providers(self) -> list[ProviderSummary]: ...

    async def list_credentials(self) -> list[CredentialSummary]: ...

    async def delete_credential(self, credential_id: str) -> bool:
        """Deletes a credential from the credential file. False when it does not exist."""
        ...

    def login(self, provider: str, method: LoginMethod, name: str) -> AsyncIterator[LoginEvent]:
        """Runs one login. The iterator ends with LoginEnd or RunError. Closing the iterator stops the login."""
        ...

    async def answer_login(self, prompt_id: str, value: str) -> bool:
        """Answers a login step `prompt`. False when no login waits for the prompt."""
        ...


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
        case "tool_step":
            return to_tool_step(event)
        case "strategy_version_saved":
            return StrategyVersionSaved(
                strategy_id=int(event["strategy_id"]),
                strategy_version_id=int(event["strategy_version_id"]),
                version_number=int(event["version_number"]),
            )
        case "backtest_finished":
            return BacktestFinished(backtest_id=int(event["backtest_id"]))
        case _:
            return None


def to_tool_step(event: dict[str, Any]) -> ToolStep:
    backtest_id = event.get("backtest_id")
    backtest_status = event.get("backtest_status")
    return ToolStep(
        tool_call_id=str(event["tool_call_id"]),
        tool_name=str(event["tool_name"]),
        status=TOOL_STEP_STATUSES[str(event["status"])],
        backtest_id=None if backtest_id is None else int(backtest_id),
        backtest_status=None if backtest_status is None else str(backtest_status),
    )


def to_credential(credential: dict[str, Any]) -> CredentialSummary:
    return CredentialSummary(
        id=credential["id"],
        name=credential["name"],
        provider=credential["provider"],
        type=credential["type"],
        key_last4=credential["key_last4"],
        state=credential["state"],
        state_message=credential["state_message"],
    )


def to_provider(provider: dict[str, Any]) -> ProviderSummary:
    return ProviderSummary(
        id=provider["id"],
        name=provider["name"],
        login_methods=provider["login_methods"],
        models=[ProviderModel(id=model["id"], name=model["name"]) for model in provider["models"]],
    )


def to_login_event(event: dict[str, Any]) -> LoginEvent | None:
    """The login event of one line of the assistant service, or None for an event that web does not use."""
    match event.get("type"):
        case "login_step":
            options: list[dict[str, str]] | None = event.get("options")
            return LoginStep(
                step=event["step"],
                message=event.get("message"),
                url=event.get("url"),
                user_code=event.get("user_code"),
                prompt_id=event.get("prompt_id"),
                prompt_type=event.get("prompt_type"),
                options=None
                if options is None
                else [LoginOption(id=item["id"], label=item["label"]) for item in options],
            )
        case "login_end":
            return LoginEnd(credential=to_credential(event["credential"]))
        case "error":
            return RunError(message=str(event["message"]))
        case _:
            return None


def read_event_line[T](line: str, convert: Callable[[dict[str, Any]], T | None], kind: str) -> T | None:
    """The event of one JSON line of the assistant service. A line that is not valid raises AssistantServiceError."""
    if not line:
        return None
    try:
        return convert(json.loads(line))
    except ValueError, KeyError, TypeError, AttributeError:
        message = f"The assistant service sent a line that is not a {kind} event: {line[:200]}"
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

    async def stream_lines(self, path: str, body: dict[str, Any]) -> AsyncIterator[str]:
        """The JSON lines of a streamed answer. No read timeout: a run or a login waits for the user or a tool."""
        try:
            async with (
                self.open_client(read_timeout_seconds=None) as client,
                client.stream("POST", path, json=body) as response,
            ):
                if response.status_code != HTTP_OK:
                    await response.aread()
                    raise AssistantServiceError(read_detail(response))
                async for line in response.aiter_lines():
                    yield line
        except httpx.HTTPError as error:
            raise not_reachable(error) from error

    async def run(
        self, conversation_id: int, text: str, selection: ModelSelection, system_prompt: str
    ) -> AsyncIterator[RunEvent]:
        # A tool can wait 15 minutes for a backtest (25.4.2).
        body = {"text": text, **selection_body(selection), "system_prompt": system_prompt}
        async for line in self.stream_lines(f"/conversations/{conversation_id}/runs", body):
            event = read_event_line(line, to_run_event, "run")
            if event is not None:
                yield event

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

    async def list_providers(self) -> list[ProviderSummary]:
        response = await self.request("GET", "/providers")
        if response.status_code != HTTP_OK:
            raise AssistantServiceError(read_detail(response))
        return [to_provider(provider) for provider in response.json()["providers"]]

    async def list_credentials(self) -> list[CredentialSummary]:
        response = await self.request("GET", "/credentials")
        if response.status_code != HTTP_OK:
            raise AssistantServiceError(read_detail(response))
        return [to_credential(credential) for credential in response.json()["credentials"]]

    async def delete_credential(self, credential_id: str) -> bool:
        response = await self.request("DELETE", f"/credentials/{credential_id}")
        if response.status_code == HTTP_NOT_FOUND:
            return False
        if response.status_code != HTTP_NO_CONTENT:
            raise AssistantServiceError(read_detail(response))
        return True

    async def login(self, provider: str, method: LoginMethod, name: str) -> AsyncIterator[LoginEvent]:
        body = {"provider": provider, "method": method, "name": name}
        async for line in self.stream_lines("/logins", body):
            event = read_event_line(line, to_login_event, "login")
            if event is not None:
                yield event

    async def answer_login(self, prompt_id: str, value: str) -> bool:
        response = await self.request("POST", "/login-answers", {"prompt_id": prompt_id, "value": value})
        return response.status_code == HTTP_NO_CONTENT
