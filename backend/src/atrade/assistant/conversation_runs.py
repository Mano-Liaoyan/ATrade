"""The runs of the conversations with the AI assistant (docs/architecture/assistant.md 25.10).

A run belongs to its conversation, not to the browser socket that sent the prompt. It goes on when the browser leaves
(a reload, a lost connection), so the answer is not lost. Each socket of a conversation gets the messages of its
runs. A socket that opens during a run first gets `run_replay` and then all messages of the run until now.

After the first run with an answer, `web` generates the title once (25.8.3). A failure sends an `error` message and
leaves the title. A rename before or during the generation wins.
"""

import asyncio
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import anyio
import psycopg
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel

from atrade.assistant import conversation_store
from atrade.assistant.assistant_service import (
    AssistantErrorMessage,
    AssistantService,
    AssistantServiceError,
    MessageEndMessage,
    ModelSelection,
    PromptImage,
)
from atrade.assistant.system_prompt import join_system_prompt

logger = logging.getLogger("atrade.assistant")


class RunStateMessage(BaseModel):
    """The state of the run of the conversation: `running` from the prompt, `settled` after the end of the run."""

    type: Literal["run_state"] = "run_state"
    state: Literal["running", "settled"]


class RunReplayMessage(BaseModel):
    """The socket opened during a run. The messages of the run until now come after this message.

    The conversation log is then: the first `saved_message_count` saved messages (the messages before the run), the
    user message `text` of the run, and the messages that follow.
    """

    type: Literal["run_replay"] = "run_replay"
    saved_message_count: int
    text: str


@dataclass
class ActiveRun:
    text: str
    # The count of the saved messages before the run. None until the assistant service answers.
    saved_message_count: int | None = None
    events: list[BaseModel] = field(default_factory=list[BaseModel])
    # The sockets that opened before `saved_message_count` was known.
    waiting: list[MemoryObjectSendStream[BaseModel]] = field(default_factory=list[MemoryObjectSendStream[BaseModel]])


@dataclass(frozen=True)
class Subscription:
    conversation_id: int
    send_stream: MemoryObjectSendStream[BaseModel]
    messages: MemoryObjectReceiveStream[BaseModel]


class ConversationRuns:
    """The active runs of all conversations, and the sockets that get their messages. At most one run for each
    conversation."""

    def __init__(self, *, database_url: str, assistant_service: AssistantService) -> None:
        self.database_url = database_url
        self.assistant_service = assistant_service
        self.active: dict[int, ActiveRun] = {}
        self.listeners: dict[int, set[MemoryObjectSendStream[BaseModel]]] = {}
        # asyncio keeps only a weak reference to a task.
        self.tasks: set[asyncio.Task[None]] = set()

    def is_running(self, conversation_id: int) -> bool:
        return conversation_id in self.active

    def subscribe(self, conversation_id: int) -> Subscription:
        """Has no await: the socket misses no message between the replay and the next message of the run."""
        send_stream, messages = anyio.create_memory_object_stream[BaseModel](math.inf)
        run = self.active.get(conversation_id)
        if run is not None and run.saved_message_count is None:
            run.waiting.append(send_stream)
        else:
            self.join(conversation_id, run, send_stream)
        return Subscription(conversation_id, send_stream, messages)

    def join(self, conversation_id: int, run: ActiveRun | None, send_stream: MemoryObjectSendStream[BaseModel]) -> None:
        if run is not None and run.saved_message_count is not None:
            send_stream.send_nowait(RunReplayMessage(saved_message_count=run.saved_message_count, text=run.text))
            for event in run.events:
                send_stream.send_nowait(event)
        self.listeners.setdefault(conversation_id, set()).add(send_stream)

    def unsubscribe(self, subscription: Subscription) -> None:
        self.listeners.get(subscription.conversation_id, set()).discard(subscription.send_stream)
        run = self.active.get(subscription.conversation_id)
        if run is not None and subscription.send_stream in run.waiting:
            run.waiting.remove(subscription.send_stream)
        subscription.send_stream.close()

    def publish(self, conversation_id: int, message: BaseModel) -> None:
        run = self.active.get(conversation_id)
        if run is not None:
            run.events.append(message)
        for send_stream in self.listeners.get(conversation_id, set()):
            send_stream.send_nowait(message)

    def admit_waiting(self, conversation_id: int, run: ActiveRun) -> None:
        for send_stream in run.waiting:
            self.join(conversation_id, run, send_stream)
        run.waiting.clear()

    def start(self, conversation_id: int, text: str, images: Sequence[PromptImage], selection: ModelSelection) -> None:
        """Starts the run as a task of its own. The caller makes sure that the conversation has no run."""
        run = ActiveRun(text=text)
        self.active[conversation_id] = run
        task = asyncio.create_task(self.run(conversation_id, run, images, selection))
        self.tasks.add(task)
        task.add_done_callback(self.end_task)

    def end_task(self, task: asyncio.Task[None]) -> None:
        self.tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("A run of the AI assistant failed.", exc_info=task.exception())

    async def run(
        self, conversation_id: int, run: ActiveRun, images: Sequence[PromptImage], selection: ModelSelection
    ) -> None:
        has_answer = False
        try:
            self.publish(conversation_id, RunStateMessage(state="running"))
            try:
                run.saved_message_count = len(await self.assistant_service.read_messages(conversation_id))
                self.admit_waiting(conversation_id, run)
                system_prompt = await self.read_system_prompt(conversation_id)
                events = self.assistant_service.run(conversation_id, run.text, selection, system_prompt, images)
                async for event in events:
                    if isinstance(event, MessageEndMessage):
                        has_answer = True
                        await self.save_last_model(conversation_id, event)
                    self.publish(conversation_id, event)
            except AssistantServiceError as error:
                self.publish(conversation_id, AssistantErrorMessage(message=str(error)))
            except Exception:
                # web cannot follow the run after an error of its own (the database), so the run stops.
                self.publish(conversation_id, AssistantErrorMessage(message="The run stopped: web failed."))
                await self.stop(conversation_id)
                raise
        finally:
            del self.active[conversation_id]
            # Without the message count, a waiting socket gets no replay: it gets `settled` and the next runs.
            self.admit_waiting(conversation_id, run)
            self.publish(conversation_id, RunStateMessage(state="settled"))
        if has_answer:
            await self.generate_title_once(conversation_id, selection)

    async def stop(self, conversation_id: int) -> None:
        with anyio.CancelScope(shield=True):
            try:
                await self.assistant_service.abort(conversation_id)
            except AssistantServiceError:
                return

    async def read_system_prompt(self, conversation_id: int) -> str:
        """The prompt version of the conversation and the fixed part of its start (25.9)."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            parts = await conversation_store.select_system_prompt_parts(connection, conversation_id)
        if parts is None:
            message = f"The conversation {conversation_id} does not exist."
            raise AssistantServiceError(message)
        return join_system_prompt(parts.editable_part, parts.fixed_part)

    async def save_last_model(self, conversation_id: int, event: MessageEndMessage) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await conversation_store.save_last_model(
                connection,
                conversation_id,
                provider=event.provider,
                model=event.model,
                credential_name=event.credential_name,
            )

    async def generate_title_once(self, conversation_id: int, selection: ModelSelection) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            if not await conversation_store.claim_title_generation(connection, conversation_id):
                return
        title: str | None = None
        try:
            title = await self.assistant_service.generate_title(conversation_id, selection)
        except AssistantServiceError as error:
            self.publish(conversation_id, AssistantErrorMessage(message=f"The title was not generated. {error}"))
        finally:
            # The shutdown can cancel the model call. The state must not stay `generating` (25.8.3).
            with anyio.CancelScope(shield=True):
                await self.end_title_generation(conversation_id, title)

    async def end_title_generation(self, conversation_id: int, title: str | None) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await conversation_store.end_title_generation(connection, conversation_id, title)
