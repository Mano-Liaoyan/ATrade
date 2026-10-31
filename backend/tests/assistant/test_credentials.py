"""Providers, credentials, and the login on /ws/assistant (docs/architecture/assistant.md 25.7, 25.10, 25.11).

`web` uses the fake assistant service. The credential file, the pi login, and the OAuth refresh are tested in
assistant/tests/credential_file.test.ts and assistant/tests/logins.test.ts.
"""

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import psycopg
import pytest
from httpx_ws import aconnect_ws
from psycopg import sql

from atrade.assistant import CredentialSummary, LoginEnd, LoginOption, LoginStep, ProviderModel, ProviderSummary
from tests.assistant.assistant_app import open_assistant_client
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock

pytestmark = pytest.mark.anyio

MESSAGE_WAIT_SECONDS = 5
SECRET_KEY = "sk-test-secret-value-7a9f"
API_KEY_CREDENTIAL = CredentialSummary(
    id="0f6c2a1e-5b7d-4c11-9a0e-3d2f1b4c5e6f",
    name="Anthropic API key · personal",
    provider="anthropic",
    type="api_key",
    key_last4="7a9f",
    state="ready",
    state_message=None,
)
SUBSCRIPTION_CREDENTIAL = CredentialSummary(
    id="7d1e2f3a-4b5c-4d6e-8f70-1a2b3c4d5e6f",
    name="Claude Max",
    provider="anthropic",
    type="oauth",
    key_last4=None,
    state="failed",
    state_message="OAuth refresh failed for anthropic",
)

type JsonObject = dict[str, Any]


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
    ) as opened:
        yield opened


async def receive(socket: Any) -> JsonObject:
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while True:
            message: JsonObject = json.loads(await socket.receive_text())
            if message["type"] != "heartbeat":
                return message


async def test_get_providers_answers_the_providers_of_the_assistant_service(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.providers = [
        ProviderSummary(
            id="anthropic",
            name="Anthropic",
            login_methods=["oauth", "api_key"],
            models=[
                ProviderModel(id="claude-sonnet-4-5", name="Claude Sonnet 4.5", thinking_levels=["off", "low", "high"])
            ],
        ),
        ProviderSummary(id="google", name="Google", login_methods=["api_key"], models=[]),
    ]

    response = await client.get("/api/assistant/providers")

    assert response.json() == {
        "providers": [
            {
                "id": "anthropic",
                "name": "Anthropic",
                "login_methods": ["oauth", "api_key"],
                "models": [
                    {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "thinking_levels": ["off", "low", "high"]}
                ],
            },
            {"id": "google", "name": "Google", "login_methods": ["api_key"], "models": []},
        ]
    }


async def test_get_credentials_answers_the_credentials_without_secrets(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.credentials = [API_KEY_CREDENTIAL, SUBSCRIPTION_CREDENTIAL]

    response = await client.get("/api/assistant/credentials")

    assert response.json()["credentials"] == [
        {
            "id": API_KEY_CREDENTIAL.id,
            "name": "Anthropic API key · personal",
            "provider": "anthropic",
            "type": "api_key",
            "key_last4": "7a9f",
            "state": "ready",
            "state_message": None,
        },
        {
            "id": SUBSCRIPTION_CREDENTIAL.id,
            "name": "Claude Max",
            "provider": "anthropic",
            "type": "oauth",
            "key_last4": None,
            "state": "failed",
            "state_message": "OAuth refresh failed for anthropic",
        },
    ]


async def test_delete_credential_answers_204_and_404_for_a_missing_credential(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.credentials = [API_KEY_CREDENTIAL]

    deleted = await client.delete(f"/api/assistant/credentials/{API_KEY_CREDENTIAL.id}")
    missing = await client.delete(f"/api/assistant/credentials/{API_KEY_CREDENTIAL.id}")

    assert deleted.status_code == httpx.codes.NO_CONTENT
    assert assistant_service.credentials == []
    assert missing.status_code == httpx.codes.NOT_FOUND
    assert missing.json() == {"detail": f"The credential {API_KEY_CREDENTIAL.id} does not exist."}


async def test_the_credential_routes_answer_503_when_the_assistant_service_is_not_reachable(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.is_reachable = False

    for response in [
        await client.get("/api/assistant/providers"),
        await client.get("/api/assistant/credentials"),
        await client.delete(f"/api/assistant/credentials/{API_KEY_CREDENTIAL.id}"),
    ]:
        assert response.status_code == httpx.codes.SERVICE_UNAVAILABLE


async def test_a_subscription_login_sends_each_login_step_and_forwards_the_answer(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.login_script = [
        LoginStep(step="auth_url", url="https://login.example.test/authorize", message="Open the link."),
        LoginStep(step="device_code", url="https://login.example.test/device", user_code="ABCD-1234"),
        LoginStep(step="progress", message="Waiting for the code."),
        LoginStep(step="prompt", prompt_id="p1", prompt_type="manual_code", message="Paste the authorization code"),
        LoginEnd(credential=SUBSCRIPTION_CREDENTIAL),
    ]

    async with aconnect_ws("/ws/assistant", client) as socket:
        await socket.send_text(
            json.dumps({"type": "login_start", "provider": "anthropic", "method": "oauth", "name": "Claude Max"})
        )
        steps = [await receive(socket) for _ in range(4)]
        await socket.send_text(json.dumps({"type": "login_answer", "prompt_id": "p1", "value": "CODE42"}))
        end = await receive(socket)

    assert [step["step"] for step in steps] == ["auth_url", "device_code", "progress", "prompt"]
    assert steps[1] == {
        "type": "login_step",
        "step": "device_code",
        "message": None,
        "url": "https://login.example.test/device",
        "user_code": "ABCD-1234",
        "prompt_id": None,
        "prompt_type": None,
        "options": None,
    }
    assert assistant_service.logins == [("anthropic", "oauth", "Claude Max")]
    assert assistant_service.login_answers == {"p1": "CODE42"}
    assert end["type"] == "login_end"
    assert end["credential"]["name"] == "Claude Max"


async def test_a_select_prompt_sends_its_options(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    options = [LoginOption(id="pro", label="Pro"), LoginOption(id="max", label="Max")]
    assistant_service.login_script = [
        LoginStep(step="prompt", prompt_id="p1", prompt_type="select", message="Plan", options=options)
    ]

    async with aconnect_ws("/ws/assistant", client) as socket:
        await socket.send_text(json.dumps({"type": "login_start", "provider": "x", "method": "oauth", "name": "X"}))
        step = await receive(socket)

    assert step["options"] == [{"id": "pro", "label": "Pro"}, {"id": "max", "label": "Max"}]


async def test_no_secret_reaches_the_browser_the_logs_or_postgresql(
    client: httpx.AsyncClient,
    assistant_service: FakeAssistantService,
    database_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    assistant_service.login_script = [
        LoginStep(step="prompt", prompt_id="p1", prompt_type="secret", message="Enter API key"),
        LoginEnd(credential=API_KEY_CREDENTIAL),
    ]

    async with aconnect_ws("/ws/assistant", client) as socket:
        await socket.send_text(
            json.dumps({"type": "login_start", "provider": "anthropic", "method": "api_key", "name": "Personal"})
        )
        received = [await receive(socket)]
        # A message that is not valid: its error must not repeat the key.
        await socket.send_text(json.dumps({"type": "login_answer", "value": SECRET_KEY}))
        received.append(await receive(socket))
        await socket.send_text(json.dumps({"type": "login_answer", "prompt_id": "p1", "value": SECRET_KEY}))
        received.append(await receive(socket))
    received_text = json.dumps(received)
    listed = (await client.get("/api/assistant/credentials")).text

    assert assistant_service.login_answers == {"p1": SECRET_KEY}
    assert received[1]["type"] == "error"
    assert received[-1]["credential"]["key_last4"] == "7a9f"
    assert SECRET_KEY not in received_text
    assert SECRET_KEY not in listed
    assert SECRET_KEY not in caplog.text
    assert SECRET_KEY not in await dump_all_tables(database_url)


async def dump_all_tables(database_url: str) -> str:
    """The text of each row of each table of the public schema."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        cursor = await connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = [str(row[0]) for row in await cursor.fetchall()]
        texts: list[str] = []
        for table in tables:
            query = sql.SQL("SELECT CAST(t AS text) FROM {} AS t").format(sql.Identifier(table))
            rows = await connection.execute(query)
            texts.extend(str(row[0]) for row in await rows.fetchall())
    return "\n".join(texts)


async def test_leaving_the_dialog_stops_the_login(
    client: httpx.AsyncClient, assistant_service: FakeAssistantService
) -> None:
    assistant_service.login_script = [LoginStep(step="prompt", prompt_id="p1", prompt_type="secret", message="Key")]

    async with aconnect_ws("/ws/assistant", client) as socket:
        await socket.send_text(json.dumps({"type": "login_start", "provider": "x", "method": "api_key", "name": "X"}))
        await receive(socket)

    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while not assistant_service.login_closed:
            await anyio.sleep(0.01)


async def test_a_socket_without_a_conversation_refuses_a_prompt(client: httpx.AsyncClient) -> None:
    async with aconnect_ws("/ws/assistant", client) as socket:
        await socket.send_text(
            json.dumps(
                {
                    "type": "prompt",
                    "text": "Hi.",
                    "provider": "x",
                    "model": "y",
                    "credential_id": "z",
                    "thinking_level": "off",
                }
            )
        )
        message = await receive(socket)

    assert message == {
        "type": "error",
        "message": "This socket has no conversation. Open /ws/assistant with conversation_id.",
    }
