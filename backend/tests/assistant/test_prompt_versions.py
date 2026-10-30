"""The system prompt and the prompt versions (docs/architecture/assistant.md 25.9), with the fake assistant service.

The pi side (the fake model server gets the system prompt of the run) is tested in
assistant/tests/conversations.test.ts.
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import psycopg
import pytest
from httpx_ws import aconnect_ws

from atrade.assistant import MessageEnd
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.backtest.real_runner import save_test_bars
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock

MESSAGE_WAIT_SECONDS = 5
MODEL = {"provider": "fake", "model": "fake-model", "credential_id": "fake-key-1"}
ANSWER = MessageEnd(text="Hello.", provider="fake", model="fake-model", credential_name="Fake key")


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


async def save_prompt_version(client: httpx.AsyncClient, text: str) -> dict[str, Any]:
    response = await client.post("/api/assistant/prompt-versions", json={"text": text})
    assert response.status_code == httpx.codes.CREATED, response.text
    version: dict[str, Any] = response.json()
    return version


async def start_backtest(client: httpx.AsyncClient, strategy_id: int) -> int:
    version = (await client.get(f"/api/strategies/{strategy_id}/versions/1")).json()
    response = await client.post(
        "/api/backtests",
        json={
            "strategy_version_id": version["id"],
            "symbol": "BTEST",
            "exchange": "ARCA",
            "currency": "USD",
            "bar_period": "1-DAY",
            "start_utc": "2026-03-01T00:00:00Z",
            "end_utc": "2026-04-01T00:00:00Z",
            "paper_capital_usd": "10000",
        },
    )
    assert response.status_code == httpx.codes.CREATED, response.text
    backtest_id: int = response.json()["id"]
    return backtest_id


async def run_one_prompt(client: httpx.AsyncClient, conversation_id: int) -> None:
    async with aconnect_ws(f"/ws/assistant?conversation_id={conversation_id}", client) as socket:
        await socket.send_text(json.dumps({"type": "prompt", "text": "Hi.", **MODEL}))
        with anyio.fail_after(MESSAGE_WAIT_SECONDS):
            while json.loads(await socket.receive_text()) != {"type": "run_state", "state": "settled"}:
                pass


@pytest.mark.anyio
async def test_the_first_list_has_the_default_text_as_version_1(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/assistant/prompt-versions")

    assert response.status_code == httpx.codes.OK
    body = response.json()
    assert [version["version_number"] for version in body["prompt_versions"]] == [1]
    assert body["prompt_versions"][0]["text"] == body["default_text"]
    assert body["prompt_versions"][0]["created_at_utc"] == "2026-01-02T03:04:05Z"


@pytest.mark.anyio
async def test_the_default_text_is_english_and_asks_for_the_metrics_and_the_out_of_sample_result(
    client: httpx.AsyncClient,
) -> None:
    default_text: str = (await client.get("/api/assistant/prompt-versions")).json()["default_text"]

    assert default_text.isascii()
    assert "You are the ATrade strategy assistant" in default_text
    assert "When you answer about a backtest result, name its metrics and its out-of-sample result." in default_text
    # The file format and the template of docs/architecture/strategy.md 9.2.
    assert "class MovingAverageConfig(StrategyConfig):" in default_text


@pytest.mark.anyio
async def test_the_fixed_part_has_the_forbidden_actions(client: httpx.AsyncClient) -> None:
    fixed_part: str = (await client.get("/api/assistant/prompt-versions")).json()["fixed_part"]

    assert "Do not send a paper order." in fixed_part
    assert "Do not start a forward test." in fixed_part
    assert "Do not promise returns." in fixed_part


@pytest.mark.anyio
async def test_a_save_adds_a_version_with_the_next_number_and_the_list_has_all_versions(
    client: httpx.AsyncClient,
) -> None:
    await client.get("/api/assistant/prompt-versions")

    second = await save_prompt_version(client, "Answer in short sentences.")
    third = await save_prompt_version(client, "Answer in Chinese.")

    assert (second["version_number"], second["text"]) == (2, "Answer in short sentences.")
    assert third["version_number"] == 3
    versions = (await client.get("/api/assistant/prompt-versions")).json()["prompt_versions"]
    assert [version["version_number"] for version in versions] == [3, 2, 1]


@pytest.mark.anyio
async def test_a_save_before_the_first_list_is_version_1(client: httpx.AsyncClient) -> None:
    first = await save_prompt_version(client, "Answer in short sentences.")

    assert first["version_number"] == 1


@pytest.mark.anyio
async def test_an_empty_text_is_refused(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/assistant/prompt-versions", json={"text": "  "})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_an_update_of_a_prompt_version_fails(client: httpx.AsyncClient, database_url: str) -> None:
    version = await save_prompt_version(client, "Answer in short sentences.")

    with psycopg.connect(database_url, autocommit=True) as connection, pytest.raises(psycopg.errors.RaiseException):
        connection.execute(
            "UPDATE assistant_prompt_version SET text = 'Changed.' WHERE id = %(id)s", {"id": version["id"]}
        )


@pytest.mark.anyio
async def test_a_new_conversation_records_the_latest_version_and_an_old_conversation_keeps_its_version(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    strategy_id = await create_strategy(client, "SMA")
    old_conversation_id = await create_conversation(client, strategy_id)

    await save_prompt_version(client, "Answer in short sentences.")
    new_conversation_id = await create_conversation(client, strategy_id)

    old_conversation = (await client.get(f"/api/assistant/conversations/{old_conversation_id}")).json()
    new_conversation = (await client.get(f"/api/assistant/conversations/{new_conversation_id}")).json()
    assert old_conversation["prompt_version_number"] == 1
    assert new_conversation["prompt_version_number"] == 2
    assistant_service.run_scripts = [[ANSWER], [ANSWER]]
    await run_one_prompt(client, old_conversation_id)
    await run_one_prompt(client, new_conversation_id)
    default_text = (await client.get("/api/assistant/prompt-versions")).json()["default_text"]
    assert assistant_service.system_prompts[0].startswith(default_text)
    assert assistant_service.system_prompts[1].startswith("Answer in short sentences.\n\n")


@pytest.mark.anyio
async def test_the_system_prompt_is_the_editable_part_and_then_the_fixed_part_with_the_start_context(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService, database_url: str
) -> None:
    save_test_bars(database_url)
    strategy_id = await create_strategy(client, "SMA cross")
    other_strategy_id = await create_strategy(client, "RSI")
    backtest_ids = [await start_backtest(client, strategy_id) for _ in range(4)]
    await start_backtest(client, other_strategy_id)
    await save_prompt_version(client, "Answer in short sentences.")
    response = await client.post("/api/assistant/conversations", json={"strategy_id": strategy_id, "version_number": 1})
    conversation_id: int = response.json()["id"]
    assistant_service.run_scripts = [[ANSWER]]

    await run_one_prompt(client, conversation_id)

    [system_prompt] = assistant_service.system_prompts
    editable_part, fixed_part = system_prompt.split("\n\n", 1)
    assert editable_part == "Answer in short sentences."
    assert "Do not send a paper order." in fixed_part
    assert f"The open strategy: ID {strategy_id}, name SMA cross." in fixed_part
    assert "The open version: 1." in fixed_part
    last_three = ", ".join(str(backtest_id) for backtest_id in reversed(backtest_ids[1:]))
    assert f"The last 3 backtests of the strategy: {last_three}." in fixed_part


@pytest.mark.anyio
async def test_a_conversation_without_an_open_version_or_backtests_says_none(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    strategy_id = await create_strategy(client, "SMA cross")
    conversation_id = await create_conversation(client, strategy_id)
    assistant_service.run_scripts = [[ANSWER]]

    await run_one_prompt(client, conversation_id)

    [system_prompt] = assistant_service.system_prompts
    assert "The open version: none." in system_prompt
    assert "The last 3 backtests of the strategy: none." in system_prompt
