"""Browser routes of the conversations (docs/architecture/assistant.md 25.11), with the fake assistant service.

The clock is 2026-01-02 03:04:05 UTC.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from atrade.assistant import ConversationMessage
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock


@pytest.fixture
def assistant_service() -> FakeAssistantService:
    return FakeAssistantService()


@pytest.fixture
async def client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, assistant_service: FakeAssistantService
) -> AsyncIterator[httpx.AsyncClient]:
    async with open_assistant_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        assistant_service=assistant_service,
    ) as assistant_client:
        yield assistant_client


@pytest.mark.anyio
async def test_a_new_conversation_has_the_title_new_conversation_and_the_utc_creation_time(
    client: httpx.AsyncClient,
) -> None:
    strategy_id = await create_strategy(client, "SMA")

    response = await client.post("/api/assistant/conversations", json={"strategy_id": strategy_id})

    assert response.status_code == httpx.codes.CREATED
    body = response.json()
    assert body["title"] == "New conversation 2026-01-02 03:04 UTC"
    assert body["title_state"] == "new"
    assert body["strategy_id"] == strategy_id
    assert body["created_at_utc"] == "2026-01-02T03:04:05Z"
    assert (body["last_provider"], body["last_model"], body["last_credential_name"]) == (None, None, None)


@pytest.mark.anyio
async def test_a_conversation_of_a_missing_strategy_is_refused_with_404(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/assistant/conversations", json={"strategy_id": 999})

    assert response.status_code == httpx.codes.NOT_FOUND
    assert response.json() == {"detail": "The strategy 999 does not exist."}


@pytest.mark.anyio
async def test_the_list_has_only_the_conversations_of_the_strategy(client: httpx.AsyncClient) -> None:
    first_strategy_id = await create_strategy(client, "SMA")
    second_strategy_id = await create_strategy(client, "RSI")
    first_id = await create_conversation(client, first_strategy_id)
    second_id = await create_conversation(client, first_strategy_id)
    await create_conversation(client, second_strategy_id)

    response = await client.get("/api/assistant/conversations", params={"strategy_id": first_strategy_id})

    assert response.status_code == httpx.codes.OK
    assert [conversation["id"] for conversation in response.json()["conversations"]] == [second_id, first_id]


@pytest.mark.anyio
async def test_read_returns_the_messages_of_the_assistant_service(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    conversation_id = await create_conversation(client, await create_strategy(client, "SMA"))
    assistant_service.messages[conversation_id] = [
        ConversationMessage(role="user", text="Hi.", provider=None, model=None, credential_name=None),
        ConversationMessage(
            role="assistant", text="Hello.", provider="fake", model="fake-model", credential_name="Fake key"
        ),
    ]

    response = await client.get(f"/api/assistant/conversations/{conversation_id}")

    assert response.status_code == httpx.codes.OK
    assert response.json()["messages"] == [
        {"role": "user", "text": "Hi.", "provider": None, "model": None, "credential_name": None},
        {
            "role": "assistant",
            "text": "Hello.",
            "provider": "fake",
            "model": "fake-model",
            "credential_name": "Fake key",
        },
    ]


@pytest.mark.anyio
async def test_read_answers_503_when_the_assistant_service_is_not_reachable(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    conversation_id = await create_conversation(client, await create_strategy(client, "SMA"))
    assistant_service.is_reachable = False

    response = await client.get(f"/api/assistant/conversations/{conversation_id}")

    assert response.status_code == httpx.codes.SERVICE_UNAVAILABLE


@pytest.mark.anyio
async def test_rename_sets_the_title_of_the_user(client: httpx.AsyncClient) -> None:
    conversation_id = await create_conversation(client, await create_strategy(client, "SMA"))

    response = await client.patch(f"/api/assistant/conversations/{conversation_id}", json={"title": " My test "})

    assert response.status_code == httpx.codes.OK
    assert (response.json()["title"], response.json()["title_state"]) == ("My test", "renamed")


@pytest.mark.anyio
async def test_delete_removes_the_row_and_the_jsonl_file(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    strategy_id = await create_strategy(client, "SMA")
    conversation_id = await create_conversation(client, strategy_id)

    response = await client.delete(f"/api/assistant/conversations/{conversation_id}")

    assert response.status_code == httpx.codes.NO_CONTENT
    assert assistant_service.deleted_conversations == [conversation_id]
    listed = await client.get("/api/assistant/conversations", params={"strategy_id": strategy_id})
    assert listed.json()["conversations"] == []


@pytest.mark.anyio
async def test_delete_keeps_the_row_when_the_assistant_service_is_not_reachable(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    conversation_id = await create_conversation(client, await create_strategy(client, "SMA"))
    assistant_service.is_reachable = False

    response = await client.delete(f"/api/assistant/conversations/{conversation_id}")

    assert response.status_code == httpx.codes.SERVICE_UNAVAILABLE
    assistant_service.is_reachable = True
    assert (await client.get(f"/api/assistant/conversations/{conversation_id}")).status_code == httpx.codes.OK


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "body"), [("GET", None), ("PATCH", {"title": "New"}), ("DELETE", None)], ids=["read", "rename", "delete"]
)
async def test_a_missing_conversation_answers_404(
    client: httpx.AsyncClient, method: str, body: dict[str, str] | None
) -> None:
    response = await client.request(method, "/api/assistant/conversations/999", json=body)

    assert response.status_code == httpx.codes.NOT_FOUND
    assert response.json() == {"detail": "The conversation 999 does not exist."}


@pytest.mark.anyio
async def test_a_strategy_delete_deletes_its_conversations(client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(client, "SMA")
    conversation_id = await create_conversation(client, strategy_id)

    assert (await client.delete(f"/api/strategies/{strategy_id}")).status_code == httpx.codes.NO_CONTENT

    assert (await client.get(f"/api/assistant/conversations/{conversation_id}")).status_code == httpx.codes.NOT_FOUND
