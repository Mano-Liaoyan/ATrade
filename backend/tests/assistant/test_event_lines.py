"""The contract of the event lines of the assistant service (docs/architecture/assistant.md 25.14).

`web` must read each line of event_lines.json as a known event. An event type that `web` does not know gives no event.
assistant/tests/event_lines.test.ts proves that the assistant service emits the same lines.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from atrade.assistant import AssistantServiceClient, ModelSelection

EVENT_LINES_PATH = Path(__file__).parents[3] / "assistant" / "tests" / "event_lines.json"
EVENT_LINES: dict[str, dict[str, Any]] = json.loads(EVENT_LINES_PATH.read_text(encoding="utf-8"))
SELECTION = ModelSelection(provider="fake", model="fake-model", credential_id="fake-key-1", thinking_level="off")


@pytest.mark.anyio
@pytest.mark.parametrize("line_type", EVENT_LINES)
async def test_each_event_line_becomes_one_event(line_type: str) -> None:
    answer = httpx.Response(200, text=json.dumps(EVENT_LINES[line_type]))
    client = AssistantServiceClient(base_url="http://assistant:8002", transport=httpx.MockTransport(lambda _: answer))

    if line_type.startswith("login_"):
        events = [event async for event in client.login("fake-oauth", "oauth", "Personal")]
    else:
        events = [event async for event in client.run(7, "Hi.", SELECTION, "Be short.")]

    assert len(events) == 1
