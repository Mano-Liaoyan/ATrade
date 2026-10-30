"""/ws/assistant: the conversation with the AI assistant (docs/architecture/assistant.md 25.10).

The browser opens one socket for one conversation: `/ws/assistant?conversation_id=<id>`. `web` forwards the browser
messages to the assistant service and changes the run events of the service into the ATrade messages below. The
frontend depends only on these messages.

After the first run with an answer, `web` generates the title once (25.8.3). A failure sends an `error` message and
leaves the title. A rename before or during the generation wins. When the browser leaves, `web` stops the active run.
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
    MessageEnd,
    ModelSelection,
    RunError,
    RunEvent,
    TextDelta,
)
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


type BrowserMessage = Annotated[PromptMessage | SteerMessage | AbortMessage, Field(discriminator="type")]
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


class ConversationSocket:
    """One browser socket of one conversation. At most one run is active."""

    def __init__(
        self, websocket: WebSocket, *, conversation_id: int, database_url: str, assistant_service: AssistantService
    ) -> None:
        self.websocket = websocket
        self.conversation_id = conversation_id
        self.database_url = database_url
        self.assistant_service = assistant_service
        self.send_lock = anyio.Lock()
        self.is_running = False

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
            await self.send_error(f"The message is not valid: {error.errors(include_url=False)}")
            return
        try:
            await self.answer(message, task_group)
        except AssistantServiceError as error:
            await self.send_error(str(error))

    async def answer(self, message: BrowserMessage, task_group: TaskGroup) -> None:
        match message:
            case PromptMessage():
                if self.is_running:
                    await self.send_error("The AI assistant runs. Send a steer message, or stop the run.")
                    return
                self.is_running = True
                selection = ModelSelection(
                    provider=message.provider, model=message.model, credential_id=message.credential_id
                )
                task_group.start_soon(self.run, message.text, selection)
            case SteerMessage():
                if not self.is_running or not await self.assistant_service.steer(self.conversation_id, message.text):
                    await self.send_error("The AI assistant does not run. Send the message as a new prompt.")
            case AbortMessage():
                await self.assistant_service.abort(self.conversation_id)

    async def run(self, text: str, selection: ModelSelection) -> None:
        await self.send(RunStateMessage(state="running"))
        has_answer = False
        try:
            async for event in self.assistant_service.run(self.conversation_id, text, selection):
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
        if not self.is_running:
            return
        with anyio.CancelScope(shield=True):
            try:
                await self.assistant_service.abort(self.conversation_id)
            except AssistantServiceError:
                return


async def conversation_exists(database_url: str, conversation_id: int) -> bool:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await conversation_store.select_conversation(connection, conversation_id) is not None


async def serve_conversation(socket: ConversationSocket) -> None:
    await socket.websocket.accept()
    if not await conversation_exists(socket.database_url, socket.conversation_id):
        await socket.send_error(f"The conversation {socket.conversation_id} does not exist.")
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
    async def stream_conversation(websocket: WebSocket, conversation_id: int) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        socket = ConversationSocket(
            websocket, conversation_id=conversation_id, database_url=database_url, assistant_service=assistant_service
        )
        await serve_conversation(socket)

    return router
