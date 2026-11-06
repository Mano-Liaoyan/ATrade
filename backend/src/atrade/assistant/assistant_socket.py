"""/ws/assistant: the conversation with the AI assistant (docs/architecture/assistant.md 25.10).

The browser opens one socket for one conversation: `/ws/assistant?conversation_id=<id>`. `web` forwards the browser
messages to the assistant service and sends the server messages of assistant_service.py to the browser. The frontend
depends only on these messages.

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
    AssistantErrorMessage,
    AssistantService,
    AssistantServiceError,
    BacktestFinishedMessage,
    LoginEndMessage,
    LoginStepMessage,
    MessageDeltaMessage,
    MessageEndMessage,
    ModelSelection,
    ScreenRunFinishedMessage,
    ScreenSavedMessage,
    StrategyVersionSavedMessage,
    ThinkingLevel,
    ToolStepMessage,
)
from atrade.assistant.system_prompt import join_system_prompt
from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage

ASSISTANT_SOCKET_PATH = "/ws/assistant"
POLICY_VIOLATION_CODE = 1008

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PromptMessage(BaseModel):
    """Browser to server: a new user message, with the provider, the model, the credential, and the thinking level of
    this message."""

    type: Literal["prompt"] = "prompt"
    text: NonEmptyText
    provider: NonEmptyText
    model: NonEmptyText
    credential_id: NonEmptyText
    thinking_level: ThinkingLevel


class SteerMessage(BaseModel):
    """Browser to server: a user message while the AI assistant runs."""

    type: Literal["steer"] = "steer"
    text: NonEmptyText


class AbortMessage(BaseModel):
    """Browser to server: stop the active run (the "Stop" button)."""

    type: Literal["abort"] = "abort"


class RunStateMessage(BaseModel):
    """The state of the run of the conversation: `running` from the prompt, `settled` after the end of the run."""

    type: Literal["run_state"] = "run_state"
    state: Literal["running", "settled"]


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
    ToolStepMessage,
    StrategyVersionSavedMessage,
    BacktestFinishedMessage,
    ScreenSavedMessage,
    ScreenRunFinishedMessage,
    AssistantErrorMessage,
    HeartbeatMessage,
    LoginStartMessage,
    LoginAnswerMessage,
    LoginStepMessage,
    LoginEndMessage,
]


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
                    provider=message.provider,
                    model=message.model,
                    credential_id=message.credential_id,
                    thinking_level=message.thinking_level,
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
                await self.send(event)
        except AssistantServiceError as error:
            await self.send_error(str(error))
        finally:
            self.is_logging_in = False

    async def read_system_prompt(self, conversation_id: int) -> str:
        """The prompt version of the conversation and the fixed part of its start (25.9)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            parts = await conversation_store.select_system_prompt_parts(connection, conversation_id)
        if parts is None:
            message = f"The conversation {conversation_id} does not exist."
            raise AssistantServiceError(message)
        return join_system_prompt(parts.editable_part, parts.fixed_part)

    async def run(self, conversation_id: int, text: str, selection: ModelSelection) -> None:
        await self.send(RunStateMessage(state="running"))
        has_answer = False
        try:
            system_prompt = await self.read_system_prompt(conversation_id)
            async for event in self.assistant_service.run(conversation_id, text, selection, system_prompt):
                if isinstance(event, MessageEndMessage):
                    has_answer = True
                    await self.save_last_model(event)
                await self.send(event)
        except AssistantServiceError as error:
            await self.send_error(str(error))
        # Only a run that ends here is settled. After a cancellation, is_running stays True, so stop_active_run stops it.
        self.is_running = False
        await self.send(RunStateMessage(state="settled"))
        if has_answer:
            await self.generate_title_once(selection)

    async def save_last_model(self, event: MessageEndMessage) -> None:
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
            # The browser can leave during the model call. The state must not stay `generating` (25.8.3).
            with anyio.CancelScope(shield=True):
                await self.end_title_generation(title)

    async def end_title_generation(self, title: str | None) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
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
    try:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(socket.send_heartbeats)
            try:
                while True:
                    await socket.receive(await socket.websocket.receive_text(), task_group)
            except WebSocketDisconnect:
                pass
            task_group.cancel_scope.cancel()
    finally:
        # Also when a send to the closed socket ends the task group first (25.10: web stops the run).
        await socket.stop_active_run()


def create_assistant_socket_router(*, database_url: str, assistant_service: AssistantService) -> APIRouter:
    router = APIRouter()

    @router.websocket(ASSISTANT_SOCKET_PATH)
    async def stream_conversation(websocket: WebSocket, conversation_id: int | None = None) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        socket = ConversationSocket(
            websocket, conversation_id=conversation_id, database_url=database_url, assistant_service=assistant_service
        )
        await serve_conversation(socket)

    return router
