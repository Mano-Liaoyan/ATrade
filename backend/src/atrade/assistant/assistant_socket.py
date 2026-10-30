"""/ws/assistant: the conversation with the AI assistant (docs/architecture/assistant.md 25.10).

The browser opens one socket for one conversation: `/ws/assistant?conversation_id=<id>`. `web` forwards the browser
messages to the assistant service and changes the run events of the service into the ATrade messages below. The
frontend depends only on these messages.

After the first run with an answer, `web` generates the title once (25.8.3). A failure sends an `error` message and
leaves the title. A rename before or during the generation wins. When the browser leaves, `web` stops the active run.

The provider login runs on the same path (25.7.3). The Credentials dialog opens `/ws/assistant` without
`conversation_id`, because a login needs no conversation. `login_start` starts one login, each pi step comes as
`login_step`, a `prompt` step waits for `login_answer`, and `login_end` gives the new credential. When the browser
leaves, the login stops. The value of a `login_answer` can be an API key: `web` sends it only to the assistant
service. It never logs it and never sends it back, also not in the error text of a message that is not valid.
"""

from typing import Annotated, Literal

import anyio
import psycopg
from anyio.abc import TaskGroup
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, StringConstraints, TypeAdapter, ValidationError

from atrade.assistant import conversation_store
from atrade.assistant.assistant_service import (
    AssistantService,
    AssistantServiceError,
    LoginEnd,
    LoginEvent,
    LoginStep,
    MessageEnd,
    ModelSelection,
    RunError,
    RunEvent,
    TextDelta,
)
from atrade.assistant.credential_routes import CredentialResponse, to_credential_response
from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage

ASSISTANT_SOCKET_PATH = "/ws/assistant"
POLICY_VIOLATION_CODE = 1008

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PromptMessage(BaseModel):
    """Browser to server: a new user message, with the provider, the model, and the credential of this message."""

    type: Literal["prompt"] = "prompt"
    text: NonEmptyText
    provider: NonEmptyText
    model: NonEmptyText
    credential_id: NonEmptyText


class SteerMessage(BaseModel):
    """Browser to server: a user message while the AI assistant runs."""

    type: Literal["steer"] = "steer"
    text: NonEmptyText


class AbortMessage(BaseModel):
    """Browser to server: stop the active run (the "Stop" button)."""

    type: Literal["abort"] = "abort"


class MessageDeltaMessage(BaseModel):
    """A part of the streamed text of an AI assistant message."""

    type: Literal["message_delta"] = "message_delta"
    text: str


class MessageEndMessage(BaseModel):
    """The end of one AI assistant message: its full text, its model, and its credential name."""

    type: Literal["message_end"] = "message_end"
    text: str
    provider: str
    model: str
    credential_name: str


class RunStateMessage(BaseModel):
    type: Literal["run_state"] = "run_state"
    state: Literal["running", "settled"]


class AssistantErrorMessage(BaseModel):
    """An error of the conversation, for the Output tab of the "Problems and output" panel."""

    type: Literal["error"] = "error"
    message: str


class LoginStartMessage(BaseModel):
    """Browser to server: start a login. `method` "oauth" is a subscription login. `name` names the new credential."""

    type: Literal["login_start"] = "login_start"
    provider: NonEmptyText
    method: Literal["oauth", "api_key"]
    name: NonEmptyText


class LoginAnswerMessage(BaseModel):
    """Browser to server: the answer to a login step `prompt`. For a `select` prompt, the ID of the option."""

    type: Literal["login_answer"] = "login_answer"
    prompt_id: NonEmptyText
    value: str


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


type BrowserMessage = Annotated[
    PromptMessage | SteerMessage | AbortMessage | LoginStartMessage | LoginAnswerMessage, Field(discriminator="type")
]
BROWSER_MESSAGE_ADAPTER: TypeAdapter[BrowserMessage] = TypeAdapter(BrowserMessage)

# The messages of /ws/assistant in both directions. The OpenAPI document adds their JSON Schema for the frontend types.
ASSISTANT_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [
    PromptMessage,
    SteerMessage,
    AbortMessage,
    MessageDeltaMessage,
    MessageEndMessage,
    RunStateMessage,
    AssistantErrorMessage,
    HeartbeatMessage,
    LoginStartMessage,
    LoginAnswerMessage,
    LoginStepMessage,
    LoginEndMessage,
]


def to_socket_message(event: RunEvent) -> BaseModel:
    match event:
        case TextDelta():
            return MessageDeltaMessage(text=event.text)
        case MessageEnd():
            return MessageEndMessage(
                text=event.text, provider=event.provider, model=event.model, credential_name=event.credential_name
            )
        case RunError():
            return AssistantErrorMessage(message=event.message)


def to_login_message(event: LoginEvent) -> BaseModel:
    match event:
        case LoginStep():
            options = (
                None
                if event.options is None
                else [LoginOptionResponse(id=option.id, label=option.label) for option in event.options]
            )
            return LoginStepMessage(
                step=event.step,
                message=event.message,
                url=event.url,
                user_code=event.user_code,
                prompt_id=event.prompt_id,
                prompt_type=event.prompt_type,
                options=options,
            )
        case LoginEnd():
            return LoginEndMessage(credential=to_credential_response(event.credential))
        case RunError():
            return AssistantErrorMessage(message=event.message)


class ConversationSocket:
    """One browser socket of one conversation, or of the Credentials dialog (no conversation).

    At most one run and one login are active.
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        conversation_id: int | None,
        database_url: str,
        assistant_service: AssistantService,
    ) -> None:
        self.websocket = websocket
        self.socket_conversation_id = conversation_id
        self.database_url = database_url
        self.assistant_service = assistant_service
        self.send_lock = anyio.Lock()
        self.is_running = False
        self.is_logging_in = False

    @property
    def conversation_id(self) -> int:
        if self.socket_conversation_id is None:
            message = "This socket has no conversation. Open /ws/assistant with conversation_id."
            raise AssistantServiceError(message)
        return self.socket_conversation_id

    async def send(self, message: BaseModel) -> None:
        async with self.send_lock:
            await self.websocket.send_text(message.model_dump_json())

    async def send_error(self, message: str) -> None:
        await self.send(AssistantErrorMessage(message=message))

    async def send_heartbeats(self) -> None:
        while True:
            await anyio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            await self.send(HeartbeatMessage())

    async def receive(self, text: str, task_group: TaskGroup) -> None:
        try:
            message = BROWSER_MESSAGE_ADAPTER.validate_json(text)
        except ValidationError as error:
            # Without the input: a login_answer can hold an API key.
            await self.send_error(f"The message is not valid: {error.errors(include_url=False, include_input=False)}")
            return
        try:
            await self.answer(message, task_group)
        except AssistantServiceError as error:
            await self.send_error(str(error))

    async def answer(self, message: BrowserMessage, task_group: TaskGroup) -> None:
        match message:
            case LoginStartMessage():
                if self.is_logging_in:
                    await self.send_error("A login runs. Answer it, or close the dialog.")
                    return
                self.is_logging_in = True
                task_group.start_soon(self.login, message)
            case LoginAnswerMessage():
                if not await self.assistant_service.answer_login(message.prompt_id, message.value):
                    await self.send_error("No login waits for this answer.")
            case PromptMessage():
                if self.is_running:
                    await self.send_error("The AI assistant runs. Send a steer message, or stop the run.")
                    return
                selection = ModelSelection(
                    provider=message.provider, model=message.model, credential_id=message.credential_id
                )
                task_group.start_soon(self.run, self.conversation_id, message.text, selection)
                self.is_running = True
            case SteerMessage():
                if not self.is_running or not await self.assistant_service.steer(self.conversation_id, message.text):
                    await self.send_error("The AI assistant does not run. Send the message as a new prompt.")
            case AbortMessage():
                await self.assistant_service.abort(self.conversation_id)

    async def login(self, message: LoginStartMessage) -> None:
        try:
            async for event in self.assistant_service.login(message.provider, message.method, message.name):
                await self.send(to_login_message(event))
        except AssistantServiceError as error:
            await self.send_error(str(error))
        finally:
            self.is_logging_in = False

    async def run(self, conversation_id: int, text: str, selection: ModelSelection) -> None:
        await self.send(RunStateMessage(state="running"))
        has_answer = False
        try:
            async for event in self.assistant_service.run(conversation_id, text, selection):
                if isinstance(event, MessageEnd):
                    has_answer = True
                    await self.save_last_model(event)
                await self.send(to_socket_message(event))
        except AssistantServiceError as error:
            await self.send_error(str(error))
        finally:
            self.is_running = False
        await self.send(RunStateMessage(state="settled"))
        if has_answer:
            await self.generate_title_once(selection)

    async def save_last_model(self, event: MessageEnd) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await conversation_store.save_last_model(
                connection,
                self.conversation_id,
                provider=event.provider,
                model=event.model,
                credential_name=event.credential_name,
            )

    async def generate_title_once(self, selection: ModelSelection) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if not await conversation_store.claim_title_generation(connection, self.conversation_id):
                return
            title: str | None = None
            try:
                title = await self.assistant_service.generate_title(self.conversation_id, selection)
            except AssistantServiceError as error:
                await self.send_error(f"The title was not generated. {error}")
            finally:
                await conversation_store.end_title_generation(connection, self.conversation_id, title)

    async def stop_active_run(self) -> None:
        if not self.is_running or self.socket_conversation_id is None:
            return
        with anyio.CancelScope(shield=True):
            try:
                await self.assistant_service.abort(self.socket_conversation_id)
            except AssistantServiceError:
                return


async def conversation_exists(database_url: str, conversation_id: int | None) -> bool:
    """True for an existing conversation, and for a socket without a conversation (the Credentials dialog)."""
    if conversation_id is None:
        return True
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await conversation_store.select_conversation(connection, conversation_id) is not None


async def serve_conversation(socket: ConversationSocket) -> None:
    await socket.websocket.accept()
    if not await conversation_exists(socket.database_url, socket.socket_conversation_id):
        await socket.send_error(f"The conversation {socket.socket_conversation_id} does not exist.")
        await socket.websocket.close(code=POLICY_VIOLATION_CODE)
        return
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(socket.send_heartbeats)
        try:
            while True:
                await socket.receive(await socket.websocket.receive_text(), task_group)
        except WebSocketDisconnect:
            await socket.stop_active_run()
        task_group.cancel_scope.cancel()


def create_assistant_socket_router(*, database_url: str, assistant_service: AssistantService) -> APIRouter:
    router = APIRouter()

    @router.websocket(ASSISTANT_SOCKET_PATH)
    async def stream_conversation(websocket: WebSocket, conversation_id: int | None = None) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        socket = ConversationSocket(
            websocket, conversation_id=conversation_id, database_url=database_url, assistant_service=assistant_service
        )
        await serve_conversation(socket)

    return router
