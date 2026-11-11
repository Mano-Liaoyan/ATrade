"""/ws/assistant: the conversation with the AI assistant (docs/architecture/assistant.md 25.10).

The browser opens one socket for one conversation: `/ws/assistant?conversation_id=<id>`. `web` forwards the browser
messages to the assistant service and sends the server messages of assistant_service.py to the browser. The frontend
depends only on these messages.

A run belongs to its conversation (conversation_runs.py): it goes on when the browser leaves, and a socket that opens
during a run gets `run_replay` and the messages of the run until now.

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
from anyio.streams.memory import MemoryObjectReceiveStream
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, StringConstraints, TypeAdapter, ValidationError

from atrade.assistant import conversation_store
from atrade.assistant.assistant_service import (
    MAX_PROMPT_IMAGES,
    AssistantErrorMessage,
    AssistantService,
    AssistantServiceError,
    BacktestFinishedMessage,
    LoginEndMessage,
    LoginStepMessage,
    MessageDeltaMessage,
    MessageEndMessage,
    ModelSelection,
    PromptImage,
    ScreenRunFinishedMessage,
    ScreenSavedMessage,
    StrategyVersionSavedMessage,
    ThinkingLevel,
    ToolStepMessage,
)
from atrade.assistant.conversation_runs import ConversationRuns, RunReplayMessage, RunStateMessage
from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage

ASSISTANT_SOCKET_PATH = "/ws/assistant"
POLICY_VIOLATION_CODE = 1008

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PromptMessage(BaseModel):
    """Browser to server: a new user message with its images, and the provider, the model, the credential, and the
    thinking level of this message."""

    type: Literal["prompt"] = "prompt"
    text: NonEmptyText
    images: list[PromptImage] = Field(default_factory=list[PromptImage], max_length=MAX_PROMPT_IMAGES)
    provider: NonEmptyText
    model: NonEmptyText
    credential_id: NonEmptyText
    thinking_level: ThinkingLevel


class AbortMessage(BaseModel):
    """Browser to server: stop the active run (the "Stop" button)."""

    type: Literal["abort"] = "abort"


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
    PromptMessage | AbortMessage | LoginStartMessage | LoginAnswerMessage, Field(discriminator="type")
]
BROWSER_MESSAGE_ADAPTER: TypeAdapter[BrowserMessage] = TypeAdapter(BrowserMessage)

# The messages of /ws/assistant in both directions. The OpenAPI document adds their JSON Schema for the frontend types.
ASSISTANT_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [
    PromptMessage,
    AbortMessage,
    MessageDeltaMessage,
    MessageEndMessage,
    RunStateMessage,
    RunReplayMessage,
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

    At most one login is active. The runs are in `runs`.
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        conversation_id: int | None,
        database_url: str,
        assistant_service: AssistantService,
        runs: ConversationRuns,
    ) -> None:
        self.websocket = websocket
        self.socket_conversation_id = conversation_id
        self.database_url = database_url
        self.assistant_service = assistant_service
        self.runs = runs
        self.send_lock = anyio.Lock()
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

    async def send_run_messages(self, messages: MemoryObjectReceiveStream[BaseModel]) -> None:
        async for message in messages:
            await self.send(message)

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
                if self.runs.is_running(self.conversation_id):
                    await self.send_error("The AI assistant runs. Stop the run first.")
                    return
                selection = ModelSelection(
                    provider=message.provider,
                    model=message.model,
                    credential_id=message.credential_id,
                    thinking_level=message.thinking_level,
                )
                self.runs.start(self.conversation_id, message.text, message.images, selection)
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


async def conversation_exists(database_url: str, conversation_id: int | None) -> bool:
    """True for an existing conversation, and for a socket without a conversation (the Credentials dialog)."""
    if conversation_id is None:
        return True
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await conversation_store.select_conversation(connection, conversation_id) is not None


async def serve_conversation(socket: ConversationSocket) -> None:
    # Before the accept: when the browser sees the open socket, the socket already gets the messages of the runs. So
    # the saved messages that the browser reads after the open, and these messages, have all messages (25.10).
    conversation_id = socket.socket_conversation_id
    subscription = None if conversation_id is None else socket.runs.subscribe(conversation_id)
    try:
        await socket.websocket.accept()
        if not await conversation_exists(socket.database_url, conversation_id):
            await socket.send_error(f"The conversation {conversation_id} does not exist.")
            await socket.websocket.close(code=POLICY_VIOLATION_CODE)
            return
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(socket.send_heartbeats)
            if subscription is not None:
                task_group.start_soon(socket.send_run_messages, subscription.messages)
            try:
                while True:
                    await socket.receive(await socket.websocket.receive_text(), task_group)
            except WebSocketDisconnect:
                pass
            task_group.cancel_scope.cancel()
    finally:
        # The run goes on without this socket (25.10).
        if subscription is not None:
            socket.runs.unsubscribe(subscription)


def create_assistant_socket_router(*, database_url: str, assistant_service: AssistantService) -> APIRouter:
    router = APIRouter()
    runs = ConversationRuns(database_url=database_url, assistant_service=assistant_service)

    @router.websocket(ASSISTANT_SOCKET_PATH)
    async def stream_conversation(websocket: WebSocket, conversation_id: int | None = None) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        socket = ConversationSocket(
            websocket,
            conversation_id=conversation_id,
            database_url=database_url,
            assistant_service=assistant_service,
            runs=runs,
        )
        await serve_conversation(socket)

    return router
