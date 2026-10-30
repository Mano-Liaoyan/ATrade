"""The HTTP client of the assistant service (docs/architecture/assistant.md 25.14), against a mock transport.

The real service is tested in assistant/tests/assistant_server.test.ts with the same paths and fields.
"""

import json

import httpx
import pytest

from atrade.assistant import (
    AssistantServiceClient,
    AssistantServiceError,
    BacktestFinished,
    ConversationMessage,
    MessageEnd,
    ModelSelection,
    RunError,
    StrategyVersionSaved,
    TextDelta,
    ToolStep,
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

    events = [event async for event in client.run(7, "Hi.", SELECTION)]

    assert events == [
        TextDelta(text="Hel"),
        MessageEnd(text="Hello.", provider="fake", model="fake-model", credential_name="Fake key"),
        RunError(message="Bad key"),
    ]
    assert str(requests[0].url) == "http://assistant:8002/conversations/7/runs"
    assert json.loads(requests[0].content) == {"text": "Hi.", **SELECTION_BODY}


@pytest.mark.anyio
async def test_run_reads_the_tool_events() -> None:
    step = {"type": "tool_step", "tool_call_id": "call_1", "tool_name": "run_backtest", "status": "running"}
    lines = [
        {**step, "backtest_id": None, "backtest_status": None},
        {**step, "backtest_id": 11, "backtest_status": "queued"},
        {"type": "strategy_version_saved", "strategy_id": 3, "strategy_version_id": 103, "version_number": 3},
        {"type": "backtest_finished", "backtest_id": 11},
    ]
    body = "".join(json.dumps(line) + "\n" for line in lines)
    client = client_for(httpx.Response(200, text=body), [])

    events = [event async for event in client.run(7, "Hi.", SELECTION)]

    assert events == [
        ToolStep(
            tool_call_id="call_1", tool_name="run_backtest", status="running", backtest_id=None, backtest_status=None
        ),
        ToolStep(
            tool_call_id="call_1", tool_name="run_backtest", status="running", backtest_id=11, backtest_status="queued"
        ),
        StrategyVersionSaved(strategy_id=3, strategy_version_id=103, version_number=3),
        BacktestFinished(backtest_id=11),
    ]


@pytest.mark.anyio
async def test_a_refused_run_raises_the_reason() -> None:
    client = client_for(httpx.Response(400, json={"detail": "The field text must be a text that is not empty."}), [])

    with pytest.raises(AssistantServiceError, match="The field text must be a text"):
        _ = [event async for event in client.run(7, "Hi.", SELECTION)]


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
