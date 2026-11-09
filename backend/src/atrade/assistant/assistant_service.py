"""The connection of web to the assistant service (docs/architecture/assistant.md 25.14).

The assistant service listens on port 8002 in the network atrade-assistant-internal. web calls it over HTTP:

- `POST /conversations/{id}/runs` with the user message, its images, the model selection with the thinking level, and the system
  prompt. The answer is one JSON line for each pi event that web needs: `text_delta`, `message_end` (with the model,
  the credential name, and the thinking level),
  `error`, and the tool events `tool_step`, `strategy_version_saved`, `backtest_finished`, `screen_saved`, and
  `screen_run_finished` (25.10).
- `POST /conversations/{id}/abort`.
- `POST /conversations/{id}/title`: one model call without tools. `502` with `detail` when it fails.
- `GET /conversations/{id}/messages`: the messages of the JSONL file.
- `DELETE /conversations/{id}`: stops the run and deletes the JSONL file.
- `GET /providers`, `GET /credentials`, `DELETE /credentials/{id}` (25.7). No answer holds a secret.
- `POST /logins` with the provider, the method, and the credential name. The answer is one JSON line for each login
  event: `login_step`, then `login_end` with the new credential, or `error`. Closing the request stops the login.
- `POST /login-answers` with the prompt ID and the value: the answer of the browser to a login step `prompt`.

`AssistantService` is the interface. The tests use a fake of it (tests/fakes/assistant.py). It gives the server
messages of /ws/assistant directly, so the JSON lines become these messages in one step (`read_event_line`).
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field, JsonValue, StringConstraints, TypeAdapter, ValidationError

# The service name in deploy/compose.yaml and the port of assistant/src/main.ts.
ASSISTANT_SERVICE_URL = "http://assistant:8002"
CONNECT_TIMEOUT_SECONDS = 5.0
# A title is one short model call.
REQUEST_TIMEOUT_SECONDS = 120.0
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404
# The errors of an event line with an unknown type, and of an event line without a type.
UNUSED_EVENT_ERROR_TYPES = {"union_tag_invalid", "union_tag_not_found"}


# The thinking levels of pi (THINKING_LEVEL_OPTIONS of pi-coding-agent). A model without reasoning has only "off".
type ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh", "max"]


# One image is at most 3 MB, so 4 images and the JSON around them stay under the 16 MiB WebSocket limit of uvicorn.
MAX_PROMPT_IMAGES = 4
MAX_PROMPT_IMAGE_BASE64_LENGTH = 4_000_000


class PromptImage(BaseModel):
    """One image of a user message. `base64` is the file without the `data:` prefix."""

    mime_type: Literal["image/png", "image/jpeg", "image/webp", "image/gif"]
    base64: Annotated[
        str,
        StringConstraints(max_length=MAX_PROMPT_IMAGE_BASE64_LENGTH, pattern=r"^[A-Za-z0-9+/]+={0,2}$"),
    ]


class AssistantServiceError(Exception):
    """The assistant service is not reachable, or it refused the request. The text names the reason."""


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str
    credential_id: str
    # The requested thinking level of the run. pi lowers it to a level of the model. The title call does not use it.
    thinking_level: ThinkingLevel


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


class MessageDeltaMessage(BaseModel):
    """A part of the streamed text of an AI assistant message."""

    type: Literal["message_delta"] = "message_delta"
    text: str


class MessageEndMessage(BaseModel):
    """The end of one AI assistant message: its full text, its model, its credential name, and the thinking level of
    its run."""

    type: Literal["message_end"] = "message_end"
    text: str
    provider: str
    model: str
    credential_name: str
    thinking_level: str | None


class ToolStepMessage(BaseModel):
    """The start, an update, or the end of one tool call. One `tool_call_id` is one tool step of the conversation.

    `status` is `running` at the start and at each update, then `succeeded` or `failed`. For `run_backtest`,
    `backtest_id` and `backtest_status` give the queue state (`queued`) or the run state (`running`, then a final
    status). They are null for the other tools and at the start.
    """

    type: Literal["tool_step"] = "tool_step"
    tool_call_id: str
    tool_name: str
    status: Literal["running", "succeeded", "failed"]
    backtest_id: int | None
    backtest_status: str | None


class StrategyVersionSavedMessage(BaseModel):
    """The AI assistant saved a strategy version, for the diff card (25.5.2)."""

    type: Literal["strategy_version_saved"] = "strategy_version_saved"
    strategy_id: int
    strategy_version_id: int
    version_number: int


class BacktestFinishedMessage(BaseModel):
    """A backtest of `run_backtest` ended in the wait of the tool, for the metric card."""

    type: Literal["backtest_finished"] = "backtest_finished"
    backtest_id: int


class ScreenSavedMessage(BaseModel):
    """The AI assistant made or changed a screen, for the condition card (25.12.4). The card compares `definition`
    with `previous_definition`: the screen before `update_screen`, or the source screen of `create_screen`. Null when
    `create_screen` has no source screen."""

    type: Literal["screen_saved"] = "screen_saved"
    screen_id: int
    name: str
    market: str
    definition: JsonValue
    previous_definition: JsonValue


class ScreenRunFinishedMessage(BaseModel):
    """`run_screen` saved a screen result. The last condition card of the screen shows its funnel counts."""

    type: Literal["screen_run_finished"] = "screen_run_finished"
    screen_id: int
    screen_result_id: int
    start_count: int
    after_filters_count: int
    after_indicator_conditions_count: int
    result_count: int


class AssistantErrorMessage(BaseModel):
    """An error of the conversation, for the Output tab of the "Problems and output" panel."""

    type: Literal["error"] = "error"
    message: str


class LoginOptionResponse(BaseModel):
    id: str
    label: str


class LoginStepMessage(BaseModel):
    """One login step of pi (25.7.3).

    - `auth_url`: open `url` (the authorization link). `message` has the instructions of the provider.
    - `device_code`: enter `user_code` at `url`.
    - `progress`, `info`: `message` (and for `info` maybe a `url`).
    - `prompt`: show a field for `prompt_type` (`text`, `secret` as a password field, `select` with `options`, or
      `manual_code` to paste a code) with the label `message`, and answer with `login_answer` and `prompt_id`.
    """

    type: Literal["login_step"] = "login_step"
    step: Literal["auth_url", "device_code", "progress", "info", "prompt"]
    message: str | None
    url: str | None
    user_code: str | None
    prompt_id: str | None
    prompt_type: Literal["text", "secret", "select", "manual_code"] | None
    options: list[LoginOptionResponse] | None


class LoginEndMessage(BaseModel):
    """The login ended. The credential is in the credential file of the assistant service."""

    type: Literal["login_end"] = "login_end"
    credential: CredentialResponse


class TextDeltaLine(BaseModel):
    """The text delta line of the assistant service. This line is the only one with a form other than its message."""

    type: Literal["text_delta"]
    delta: str


# The events of a run and of a login that have the same form in the JSON lines and on /ws/assistant.
type SameFormEvent = (
    MessageEndMessage
    | AssistantErrorMessage
    | ToolStepMessage
    | StrategyVersionSavedMessage
    | BacktestFinishedMessage
    | ScreenSavedMessage
    | ScreenRunFinishedMessage
    | LoginStepMessage
    | LoginEndMessage
)
type AssistantEvent = MessageDeltaMessage | SameFormEvent
type EventLine = Annotated[TextDeltaLine | SameFormEvent, Field(discriminator="type")]
EVENT_LINE_ADAPTER: TypeAdapter[EventLine] = TypeAdapter(EventLine)

type LoginMethod = Literal["oauth", "api_key"]


@dataclass(frozen=True)
class ProviderModel:
    id: str
    name: str
    # The thinking levels of the model, in the order of pi. Only "off" for a model without reasoning.
    thinking_levels: list[ThinkingLevel] = field(default_factory=lambda: list[ThinkingLevel](["off"]))
    # The model accepts images in a user message.
    reads_images: bool = False


@dataclass(frozen=True)
class ProviderSummary:
    """A provider of pi with its login methods, and the models of its stored credentials (25.7.1)."""

    id: str
    name: str
    login_methods: list[LoginMethod]
    models: list[ProviderModel]


@dataclass(frozen=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    text: str
    provider: str | None
    model: str | None
    credential_name: str | None
    # Null for a user message, and for an AI assistant message of a run before the thinking level was recorded.
    thinking_level: str | None = None


class AssistantService(Protocol):
    def run(
        self,
        conversation_id: int,
        text: str,
        selection: ModelSelection,
        system_prompt: str,
        images: Sequence[PromptImage] = (),
    ) -> AsyncIterator[AssistantEvent]:
        """Runs one user message with the system prompt of the conversation. The iterator ends at the settled run."""
        ...

    async def abort(self, conversation_id: int) -> None: ...

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str: ...

    async def read_messages(self, conversation_id: int) -> list[ConversationMessage]: ...

    async def delete_conversation(self, conversation_id: int) -> None: ...

    async def list_providers(self) -> list[ProviderSummary]: ...

    async def list_credentials(self) -> list[CredentialResponse]: ...

    async def delete_credential(self, credential_id: str) -> bool:
        """Deletes a credential from the credential file. False when it does not exist."""
        ...

    def login(self, provider: str, method: LoginMethod, name: str) -> AsyncIterator[AssistantEvent]:
        """Runs one login. The iterator ends with LoginEndMessage or AssistantErrorMessage. Closing the iterator stops the login."""
        ...

    async def answer_login(self, prompt_id: str, value: str) -> bool:
        """Answers a login step `prompt`. False when no login waits for the prompt."""
        ...


def to_provider(provider: dict[str, Any]) -> ProviderSummary:
    return ProviderSummary(
        id=provider["id"],
        name=provider["name"],
        login_methods=provider["login_methods"],
        models=[
            ProviderModel(
                id=model["id"],
                name=model["name"],
                thinking_levels=model["thinking_levels"],
                reads_images=model["reads_images"],
            )
            for model in provider["models"]
        ],
    )


def read_event_line(line: str) -> AssistantEvent | None:
    """The event of one JSON line of the assistant service, or None for an event that web does not use. A line that
    is not valid raises AssistantServiceError."""
    if not line:
        return None
    try:
        event = EVENT_LINE_ADAPTER.validate_json(line)
    except ValidationError as error:
        if error.errors(include_url=False, include_input=False)[0]["type"] in UNUSED_EVENT_ERROR_TYPES:
            return None
        message = f"The assistant service sent a line that is not an event: {line[:200]}"
        raise AssistantServiceError(message) from None
    return MessageDeltaMessage(text=event.delta) if isinstance(event, TextDeltaLine) else event


def not_reachable(error: httpx.HTTPError) -> AssistantServiceError:
    return AssistantServiceError(f"The assistant service is not reachable: {error}")


def read_detail(response: httpx.Response) -> str:
    try:
        return str(response.json()["detail"])
    except ValueError, KeyError, TypeError:
        return f"The assistant service answered {response.status_code}."


def selection_body(selection: ModelSelection) -> dict[str, str]:
    """The model and the credential. Only the run body adds the thinking level."""
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
                # Split only at the newline. aiter_lines also splits at U+2028, U+2029, and U+0085. JSON.stringify
                # does not escape these characters, so they can occur in a JSON line.
                last_line = ""
                async for text in response.aiter_text():
                    *lines, last_line = (last_line + text).split("\n")
                    for line in lines:
                        yield line
                yield last_line
        except httpx.HTTPError as error:
            raise not_reachable(error) from error

    async def run(
        self,
        conversation_id: int,
        text: str,
        selection: ModelSelection,
        system_prompt: str,
        images: Sequence[PromptImage] = (),
    ) -> AsyncIterator[AssistantEvent]:
        # A tool can wait 15 minutes for a backtest (25.4.2).
        body = {
            "text": text,
            "images": [image.model_dump() for image in images],
            **selection_body(selection),
            "thinking_level": selection.thinking_level,
            "system_prompt": system_prompt,
        }
        async for line in self.stream_lines(f"/conversations/{conversation_id}/runs", body):
            event = read_event_line(line)
            if event is not None:
                yield event

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
                thinking_level=message.get("thinking_level"),
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

    async def list_credentials(self) -> list[CredentialResponse]:
        response = await self.request("GET", "/credentials")
        if response.status_code != HTTP_OK:
            raise AssistantServiceError(read_detail(response))
        return [CredentialResponse.model_validate(credential) for credential in response.json()["credentials"]]

    async def delete_credential(self, credential_id: str) -> bool:
        response = await self.request("DELETE", f"/credentials/{credential_id}")
        if response.status_code == HTTP_NOT_FOUND:
            return False
        if response.status_code != HTTP_NO_CONTENT:
            raise AssistantServiceError(read_detail(response))
        return True

    async def login(self, provider: str, method: LoginMethod, name: str) -> AsyncIterator[AssistantEvent]:
        body = {"provider": provider, "method": method, "name": name}
        async for line in self.stream_lines("/logins", body):
            event = read_event_line(line)
            if event is not None:
                yield event

    async def answer_login(self, prompt_id: str, value: str) -> bool:
        response = await self.request("POST", "/login-answers", {"prompt_id": prompt_id, "value": value})
        return response.status_code == HTTP_NO_CONTENT
