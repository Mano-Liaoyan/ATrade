"""The HTTP client of the assistant service (docs/architecture/assistant.md 25.14), against a mock transport.

The real service is tested in assistant/tests/assistant_server.test.ts with the same paths and fields.
"""

import dataclasses
import json

import httpx
import pytest

from atrade.assistant import (
    AssistantServiceClient,
    AssistantServiceError,
    ConversationMessage,
    CredentialSummary,
    LoginEnd,
    LoginStep,
    MessageEnd,
    ModelSelection,
    ProviderModel,
    ProviderSummary,
    RunError,
    TextDelta,
)

SELECTION = ModelSelection(provider="fake", model="fake-model", credential_id="fake-key-1")
SELECTION_BODY = {"provider": "fake", "model": "fake-model", "credential_id": "fake-key-1"}


def client_for(answer: httpx.Response, requests: list[httpx.Request]) -> AssistantServiceClient:
    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return answer

    return AssistantServiceClient(base_url="http://assistant:8002", transport=httpx.MockTransport(handle_request))


@pytest.mark.anyio
async def test_run_reads_the_json_lines_and_skips_unknown_events() -> None:
    lines = [
        {"type": "text_delta", "delta": "Hel"},
        {"type": "turn_start"},
        {
            "type": "message_end",
            "text": "Hello.",
            "provider": "fake",
            "model": "fake-model",
            "credential_name": "Fake key",
        },
        {"type": "error", "message": "Bad key"},
    ]
    requests: list[httpx.Request] = []
    body = "".join(json.dumps(line) + "\n" for line in lines)
    client = client_for(httpx.Response(200, text=body), requests)

    events = [event async for event in client.run(7, "Hi.", SELECTION, "Be short.")]

    assert events == [
        TextDelta(text="Hel"),
        MessageEnd(text="Hello.", provider="fake", model="fake-model", credential_name="Fake key"),
        RunError(message="Bad key"),
    ]
    assert str(requests[0].url) == "http://assistant:8002/conversations/7/runs"
    assert json.loads(requests[0].content) == {"text": "Hi.", **SELECTION_BODY, "system_prompt": "Be short."}


@pytest.mark.anyio
async def test_a_refused_run_raises_the_reason() -> None:
    client = client_for(httpx.Response(400, json={"detail": "The field text must be a text that is not empty."}), [])

    with pytest.raises(AssistantServiceError, match="The field text must be a text"):
        _ = [event async for event in client.run(7, "Hi.", SELECTION, "Be short.")]


@pytest.mark.anyio
async def test_a_service_that_is_not_reachable_raises() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = AssistantServiceClient(transport=httpx.MockTransport(refuse))

    with pytest.raises(AssistantServiceError, match="not reachable"):
        await client.read_messages(7)


@pytest.mark.anyio
async def test_title_returns_the_title_or_raises_the_reason() -> None:
    requests: list[httpx.Request] = []
    assert await client_for(httpx.Response(200, json={"title": "SMA"}), requests).generate_title(7, SELECTION) == "SMA"
    assert str(requests[0].url) == "http://assistant:8002/conversations/7/title"
    assert json.loads(requests[0].content) == SELECTION_BODY

    with pytest.raises(AssistantServiceError, match="Provider down"):
        await client_for(httpx.Response(502, json={"detail": "Provider down"}), []).generate_title(7, SELECTION)


@pytest.mark.anyio
async def test_read_messages_and_steer_and_delete_use_the_conversation_paths() -> None:
    requests: list[httpx.Request] = []
    message = {"role": "user", "text": "Hi.", "provider": None, "model": None, "credential_name": None}

    messages = await client_for(httpx.Response(200, json={"messages": [message]}), requests).read_messages(7)
    is_steered = await client_for(httpx.Response(409, json={"detail": "No run."}), requests).steer(7, "Use SMA 50.")
    await client_for(httpx.Response(204), requests).delete_conversation(7)

    assert messages == [ConversationMessage(role="user", text="Hi.", provider=None, model=None, credential_name=None)]
    assert is_steered is False
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/conversations/7/messages"),
        ("POST", "/conversations/7/steer"),
        ("DELETE", "/conversations/7"),
    ]


CREDENTIAL = CredentialSummary(
    id="c1", name="Work", provider="anthropic", type="api_key", key_last4="7a9f", state="ready", state_message=None
)
CREDENTIAL_BODY = dataclasses.asdict(CREDENTIAL)


@pytest.mark.anyio
async def test_login_reads_the_login_steps_and_the_end() -> None:
    lines = [
        {
            "type": "login_step",
            "step": "prompt",
            "message": "Enter API key",
            "url": None,
            "user_code": None,
            "prompt_id": "p1",
            "prompt_type": "secret",
            "options": None,
        },
        {"type": "login_end", "credential": CREDENTIAL_BODY},
    ]
    requests: list[httpx.Request] = []
    body = "".join(json.dumps(line) + "\n" for line in lines)
    client = client_for(httpx.Response(200, text=body), requests)

    events = [event async for event in client.login("anthropic", "api_key", "Work")]

    assert events == [
        LoginStep(step="prompt", message="Enter API key", prompt_id="p1", prompt_type="secret"),
        LoginEnd(credential=CREDENTIAL),
    ]
    assert str(requests[0].url) == "http://assistant:8002/logins"
    assert json.loads(requests[0].content) == {"provider": "anthropic", "method": "api_key", "name": "Work"}


@pytest.mark.anyio
async def test_answer_login_posts_the_answer() -> None:
    requests: list[httpx.Request] = []
    client = client_for(httpx.Response(204), requests)

    assert await client.answer_login("p1", "sk-test") is True
    assert str(requests[0].url) == "http://assistant:8002/login-answers"
    assert json.loads(requests[0].content) == {"prompt_id": "p1", "value": "sk-test"}


@pytest.mark.anyio
async def test_credentials_and_providers_are_read_and_a_missing_credential_is_false() -> None:
    requests: list[httpx.Request] = []
    credentials = client_for(httpx.Response(200, json={"credentials": [CREDENTIAL_BODY]}), requests)
    provider_body = {
        "id": "google",
        "name": "Google",
        "login_methods": ["api_key"],
        "models": [{"id": "gemini", "name": "Gemini"}],
    }
    providers = client_for(httpx.Response(200, json={"providers": [provider_body]}), requests)
    missing = client_for(httpx.Response(404, json={"detail": "The credential c1 does not exist."}), requests)

    assert await credentials.list_credentials() == [CREDENTIAL]
    assert await providers.list_providers() == [
        ProviderSummary(
            id="google", name="Google", login_methods=["api_key"], models=[ProviderModel(id="gemini", name="Gemini")]
        )
    ]
    assert await missing.delete_credential("c1") is False
    assert str(requests[-1].url) == "http://assistant:8002/credentials/c1"
