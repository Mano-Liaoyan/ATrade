"""A fake of the assistant service (atrade.assistant.AssistantService). No pi, no model provider, no JSONL file.

Each run plays the next script of `run_scripts`. The item HOLD makes the run wait until `release()` or `abort()`.
An abort ends the run at once, like pi.

A login plays `login_script`. After a LoginStep `prompt`, the login waits for `answer_login` with its prompt ID. The
answers are kept in `login_answers`. A deleted credential leaves `credentials`.
"""

from collections.abc import AsyncIterator
from typing import Final, Literal

import anyio

from atrade.assistant import (
    AssistantServiceError,
    ConversationMessage,
    CredentialSummary,
    LoginEnd,
    LoginEvent,
    LoginStep,
    ModelSelection,
    ProviderSummary,
    RunEvent,
)

HOLD: Final = "hold"

type ScriptItem = RunEvent | str


class FakeAssistantService:
    def __init__(self) -> None:
        self.run_scripts: list[list[ScriptItem]] = []
        self.runs: list[tuple[int, str, ModelSelection]] = []
        self.steers: list[tuple[int, str]] = []
        self.aborts: list[int] = []
        self.title_requests: list[tuple[int, ModelSelection]] = []
        # The generated title, or the error text of a failed generation.
        self.title: str | AssistantServiceError = "SMA crossover"
        # True: the title generation waits until it is cancelled (the browser leaves during the model call).
        self.hold_title = False
        self.title_started = anyio.Event()
        self.messages: dict[int, list[ConversationMessage]] = {}
        self.deleted_conversations: list[int] = []
        self.is_reachable = True
        self.release_event = anyio.Event()
        self.run_started = anyio.Event()
        self.providers: list[ProviderSummary] = []
        self.credentials: list[CredentialSummary] = []
        self.login_script: list[LoginEvent] = []
        self.logins: list[tuple[str, str, str]] = []
        self.login_answers: dict[str, str] = {}
        self.answer_event = anyio.Event()
        self.login_closed = False

    def require_reachable(self) -> None:
        if not self.is_reachable:
            message = "The assistant service is not reachable: connection refused"
            raise AssistantServiceError(message)

    def release(self) -> None:
        self.release_event.set()

    async def run(self, conversation_id: int, text: str, selection: ModelSelection) -> AsyncIterator[RunEvent]:
        self.require_reachable()
        self.runs.append((conversation_id, text, selection))
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
        self.title_started.set()
        if self.hold_title:
            await anyio.sleep_forever()
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

    async def list_providers(self) -> list[ProviderSummary]:
        self.require_reachable()
        return self.providers

    async def list_credentials(self) -> list[CredentialSummary]:
        self.require_reachable()
        return self.credentials

    async def delete_credential(self, credential_id: str) -> bool:
        self.require_reachable()
        kept = [credential for credential in self.credentials if credential.id != credential_id]
        deleted = len(kept) < len(self.credentials)
        self.credentials = kept
        return deleted

    async def login(self, provider: str, method: Literal["oauth", "api_key"], name: str) -> AsyncIterator[LoginEvent]:
        self.require_reachable()
        self.logins.append((provider, method, name))
        try:
            for event in self.login_script:
                yield event
                if isinstance(event, LoginStep) and event.prompt_id is not None:
                    while event.prompt_id not in self.login_answers:
                        await self.answer_event.wait()
                        self.answer_event = anyio.Event()
                if isinstance(event, LoginEnd):
                    self.credentials.append(event.credential)
        finally:
            self.login_closed = True

    async def answer_login(self, prompt_id: str, value: str) -> bool:
        self.require_reachable()
        self.login_answers[prompt_id] = value
        self.answer_event.set()
        return True
