"""/ws/assistant (docs/architecture/assistant.md 25.8, 25.10), with the fake assistant service.

The pi side of the same behavior (fake model server, JSONL file, title call without tools) is tested in
assistant/tests/conversations.test.ts.
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from httpx_ws import AsyncWebSocketSession, aconnect_ws

from atrade.assistant import AssistantServiceError, MessageEnd, ModelSelection, TextDelta
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.fakes.assistant import HOLD, FakeAssistantService
from tests.fakes.clock import FixedClock

MESSAGE_WAIT_SECONDS = 5
FIRST_MODEL = {"provider": "fake", "model": "fake-model", "credential_id": "fake-key-1"}
SECOND_MODEL = {"provider": "fake", "model": "fake-model-2", "credential_id": "fake-key-2"}
FIRST_ANSWER = MessageEnd(text="Hello.", provider="fake", model="fake-model", credential_name="Fake key · first")
SECOND_ANSWER = MessageEnd(text="Again.", provider="fake", model="fake-model-2", credential_name="Fake key · second")

type JsonObject = dict[str, Any]


class AssistantConnection:
    def __init__(self, client: httpx.AsyncClient, socket: AsyncWebSocketSession, conversation_id: int) -> None:
        self.client = client
        self.socket = socket
        self.conversation_id = conversation_id

    async def send(self, message: JsonObject) -> None:
        await self.socket.send_text(json.dumps(message))

    async def prompt(self, text: str, model: dict[str, str]) -> None:
        await self.send({"type": "prompt", "text": text, **model})

    async def receive(self) -> JsonObject:
        """The next message that is not a heartbeat."""
        with anyio.fail_after(MESSAGE_WAIT_SECONDS):
            while True:
                message: JsonObject = json.loads(await self.socket.receive_text())
                if message["type"] != "heartbeat":
                    return message

    async def receive_until_settled(self) -> list[JsonObject]:
        messages = [await self.receive()]
        while messages[-1] != {"type": "run_state", "state": "settled"}:
            messages.append(await self.receive())
        return messages

    async def read_conversation(self) -> JsonObject:
        response = await self.client.get(f"/api/assistant/conversations/{self.conversation_id}")
        conversation: JsonObject = response.json()
        return conversation


@pytest.fixture
def assistant_service() -> FakeAssistantService:
    return FakeAssistantService()


@pytest.fixture
async def connection(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, assistant_service: FakeAssistantService
) -> AsyncIterator[AssistantConnection]:
    async with open_assistant_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        assistant_service=assistant_service,
    ) as client:
        conversation_id = await create_conversation(client, await create_strategy(client, "SMA"))
        async with aconnect_ws(f"/ws/assistant?conversation_id={conversation_id}", client) as socket:
            yield AssistantConnection(client, socket, conversation_id)


async def wait_for_title_attempt(connection: AssistantConnection) -> JsonObject:
    """The conversation after the title generation of the first run ended."""
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while True:
            conversation = await connection.read_conversation()
            if conversation["title_state"] not in {"new", "generating"}:
                return conversation
            await anyio.sleep(0.01)


@pytest.mark.anyio
async def test_a_prompt_streams_the_answer_between_running_and_settled(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[TextDelta(text="Hel"), TextDelta(text="lo."), FIRST_ANSWER]]

    await connection.prompt("Hi.", FIRST_MODEL)

    assert await connection.receive_until_settled() == [
        {"type": "run_state", "state": "running"},
        {"type": "message_delta", "text": "Hel"},
        {"type": "message_delta", "text": "lo."},
        {
            "type": "message_end",
            "text": "Hello.",
            "provider": "fake",
            "model": "fake-model",
            "credential_name": "Fake key · first",
        },
        {"type": "run_state", "state": "settled"},
    ]
    assert assistant_service.runs == [
        (
            connection.conversation_id,
            "Hi.",
            ModelSelection(provider="fake", model="fake-model", credential_id="fake-key-1"),
        )
    ]


@pytest.mark.anyio
async def test_the_next_answer_after_a_model_change_names_the_new_model_and_the_conversation_keeps_it(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[FIRST_ANSWER], [SECOND_ANSWER]]
    await connection.prompt("Hi.", FIRST_MODEL)
    await connection.receive_until_settled()

    await connection.prompt("Again.", SECOND_MODEL)
    messages = await connection.receive_until_settled()

    assert [message["model"] for message in messages if message["type"] == "message_end"] == ["fake-model-2"]
    assert assistant_service.runs[1][2].model == "fake-model-2"
    conversation = await connection.read_conversation()
    assert (conversation["last_provider"], conversation["last_model"], conversation["last_credential_name"]) == (
        "fake",
        "fake-model-2",
        "Fake key · second",
    )


@pytest.mark.anyio
async def test_steer_adds_a_user_message_to_the_active_run(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[TextDelta(text="Work"), HOLD, FIRST_ANSWER]]
    await connection.prompt("Write a strategy.", FIRST_MODEL)
    assert await connection.receive() == {"type": "run_state", "state": "running"}
    assert await connection.receive() == {"type": "message_delta", "text": "Work"}

    await connection.send({"type": "steer", "text": "Use SMA 50."})
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while not assistant_service.steers:
            await anyio.sleep(0.01)
    assistant_service.release()

    assert (await connection.receive_until_settled())[-2]["type"] == "message_end"
    assert assistant_service.steers == [(connection.conversation_id, "Use SMA 50.")]


@pytest.mark.anyio
async def test_steer_without_an_active_run_sends_an_error(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    await connection.send({"type": "steer", "text": "Use SMA 50."})

    assert await connection.receive() == {
        "type": "error",
        "message": "The AI assistant does not run. Send the message as a new prompt.",
    }
    assert assistant_service.steers == []


@pytest.mark.anyio
async def test_abort_stops_the_run_and_sends_settled(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[TextDelta(text="Work"), HOLD, FIRST_ANSWER]]
    await connection.prompt("Write a strategy.", FIRST_MODEL)
    await connection.receive()
    await connection.receive()

    await connection.send({"type": "abort"})

    assert await connection.receive_until_settled() == [{"type": "run_state", "state": "settled"}]
    assert assistant_service.aborts == [connection.conversation_id]


@pytest.mark.anyio
async def test_a_second_prompt_during_a_run_sends_an_error(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[TextDelta(text="Work"), HOLD, FIRST_ANSWER]]
    await connection.prompt("First.", FIRST_MODEL)
    await connection.receive()
    await connection.receive()

    await connection.prompt("Second.", FIRST_MODEL)

    assert await connection.receive() == {
        "type": "error",
        "message": "The AI assistant runs. Send a steer message, or stop the run.",
    }
    assistant_service.release()
    await connection.receive_until_settled()
    assert len(assistant_service.runs) == 1


@pytest.mark.anyio
async def test_a_run_error_reaches_the_browser(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.is_reachable = False

    await connection.prompt("Hi.", FIRST_MODEL)

    assert await connection.receive_until_settled() == [
        {"type": "run_state", "state": "running"},
        {"type": "error", "message": "The assistant service is not reachable: connection refused"},
        {"type": "run_state", "state": "settled"},
    ]


@pytest.mark.anyio
async def test_a_message_that_is_not_valid_sends_an_error(connection: AssistantConnection) -> None:
    await connection.send({"type": "prompt", "text": ""})

    message = await connection.receive()

    assert message["type"] == "error"
    assert message["message"].startswith("The message is not valid:")


@pytest.mark.anyio
async def test_the_title_is_generated_once_after_the_first_settled_run(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[FIRST_ANSWER], [SECOND_ANSWER]]

    await connection.prompt("Write an SMA strategy.", FIRST_MODEL)
    await connection.receive_until_settled()
    conversation = await wait_for_title_attempt(connection)
    await connection.prompt("Again.", SECOND_MODEL)
    await connection.receive_until_settled()

    assert (conversation["title"], conversation["title_state"]) == ("SMA crossover", "generated")
    assert assistant_service.title_requests == [
        (connection.conversation_id, ModelSelection(provider="fake", model="fake-model", credential_id="fake-key-1"))
    ]


@pytest.mark.anyio
async def test_no_title_is_generated_after_a_run_without_an_answer(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[]]

    await connection.prompt("Hi.", FIRST_MODEL)
    await connection.receive_until_settled()

    assert (await connection.read_conversation())["title_state"] == "new"
    assert assistant_service.title_requests == []


@pytest.mark.anyio
async def test_a_failed_title_keeps_the_title_sends_an_error_and_is_not_tried_again(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[FIRST_ANSWER], [SECOND_ANSWER]]
    assistant_service.title = AssistantServiceError("Provider down")

    await connection.prompt("Hi.", FIRST_MODEL)
    await connection.receive_until_settled()
    error = await connection.receive()
    await connection.prompt("Again.", FIRST_MODEL)
    await connection.receive_until_settled()

    assert error == {"type": "error", "message": "The title was not generated. Provider down"}
    conversation = await connection.read_conversation()
    assert (conversation["title"], conversation["title_state"]) == (
        "New conversation 2026-01-02 03:04 UTC",
        "not_generated",
    )
    assert len(assistant_service.title_requests) == 1


@pytest.mark.anyio
async def test_a_rename_before_the_first_settled_run_stops_the_title_generation(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[FIRST_ANSWER]]
    path = f"/api/assistant/conversations/{connection.conversation_id}"
    await connection.client.patch(path, json={"title": "My SMA test"})

    await connection.prompt("Hi.", FIRST_MODEL)
    await connection.receive_until_settled()

    conversation = await connection.read_conversation()
    assert (conversation["title"], conversation["title_state"]) == ("My SMA test", "renamed")
    assert assistant_service.title_requests == []


@pytest.mark.anyio
async def test_a_rename_after_the_generated_title_wins_for_ever(
    connection: AssistantConnection, assistant_service: FakeAssistantService
) -> None:
    assistant_service.run_scripts = [[FIRST_ANSWER], [SECOND_ANSWER]]
    await connection.prompt("Hi.", FIRST_MODEL)
    await connection.receive_until_settled()
    await wait_for_title_attempt(connection)

    await connection.client.patch(f"/api/assistant/conversations/{connection.conversation_id}", json={"title": "Mine"})
    await connection.prompt("Again.", FIRST_MODEL)
    await connection.receive_until_settled()

    assert (await connection.read_conversation())["title"] == "Mine"
    assert len(assistant_service.title_requests) == 1


@pytest.mark.anyio
async def test_a_missing_conversation_sends_an_error_and_closes(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with (
        open_assistant_client(
            database_url=database_url,
            clock=clock,
            frontend_build_dir=frontend_build_dir,
            assistant_service=FakeAssistantService(),
        ) as client,
        aconnect_ws("/ws/assistant?conversation_id=999", client) as socket,
    ):
        message = json.loads(await socket.receive_text())

    assert message == {"type": "error", "message": "The conversation 999 does not exist."}
