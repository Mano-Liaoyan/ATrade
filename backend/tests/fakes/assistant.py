"""A fake of the assistant service (atrade.assistant.AssistantService). No pi, no model provider, no JSONL file.

Each run plays the next script of `run_scripts`. The item HOLD makes the run wait until `release()` or `abort()`.
An abort ends the run at once, like pi.
"""

from collections.abc import AsyncIterator
from typing import Final

import anyio

from atrade.assistant import AssistantServiceError, ConversationMessage, ModelSelection, RunEvent

HOLD: Final = "hold"

type ScriptItem = RunEvent | str


class FakeAssistantService:
    def __init__(self) -> None:
        self.run_scripts: list[list[ScriptItem]] = []
        self.runs: list[tuple[int, str, ModelSelection]] = []
        # The system prompt of each run, in the order of runs.
        self.system_prompts: list[str] = []
        self.steers: list[tuple[int, str]] = []
        self.aborts: list[int] = []
        self.title_requests: list[tuple[int, ModelSelection]] = []
        # The generated title, or the error text of a failed generation.
        self.title: str | AssistantServiceError = "SMA crossover"
        self.messages: dict[int, list[ConversationMessage]] = {}
        self.deleted_conversations: list[int] = []
        self.is_reachable = True
        self.release_event = anyio.Event()
        self.run_started = anyio.Event()

    def require_reachable(self) -> None:
        if not self.is_reachable:
            message = "The assistant service is not reachable: connection refused"
            raise AssistantServiceError(message)

    def release(self) -> None:
        self.release_event.set()

    async def run(
        self, conversation_id: int, text: str, selection: ModelSelection, system_prompt: str
    ) -> AsyncIterator[RunEvent]:
        self.require_reachable()
        self.runs.append((conversation_id, text, selection))
        self.system_prompts.append(system_prompt)
        script = self.run_scripts.pop(0) if self.run_scripts else []
        self.run_started.set()
        for item in script:
            if isinstance(item, str):
                await self.release_event.wait()
                self.release_event = anyio.Event()
                if self.aborts:
                    return
                continue
            yield item

    async def steer(self, conversation_id: int, text: str) -> bool:
        self.require_reachable()
        self.steers.append((conversation_id, text))
        return True

    async def abort(self, conversation_id: int) -> None:
        self.require_reachable()
        self.aborts.append(conversation_id)
        self.release_event.set()

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str:
        self.require_reachable()
        self.title_requests.append((conversation_id, selection))
        if isinstance(self.title, AssistantServiceError):
            raise self.title
        return self.title

    async def read_messages(self, conversation_id: int) -> list[ConversationMessage]:
        self.require_reachable()
        return self.messages.get(conversation_id, [])

    async def delete_conversation(self, conversation_id: int) -> None:
        self.require_reachable()
        self.deleted_conversations.append(conversation_id)
        self.messages.pop(conversation_id, None)
