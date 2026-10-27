"""Code completion through the language server WebSocket (docs/architecture/strategy.md section 9.4).

The tests talk Language Server Protocol JSON messages over the WebSocket, as `@codemirror/lsp-client` does.
They use the real basedpyright, so they also show that basedpyright resolves NautilusTrader 2.0 `Strategy`.
"""

import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from atrade.strategy import STRATEGY_LANGUAGE_SERVER_PATH, create_strategy_language_server_router
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from tests.strategy.language_server_session import LanguageServerSession

DOCUMENT_URI = "file:///atrade/strategy.py"
STRATEGY_CODE = """from nautilus_trader.trading import Strategy


class EmptyStrategy(Strategy):
    def on_start(self) -> None:
        self.
"""
TYPE_ERROR_CODE = """from nautilus_trader.trading import Strategy

count: int = "not a number"
"""
PROCESS_END_SECONDS = 10.0
# window/logMessage types: 1 error, 2 warning, 3 info, 4 log.
LOG_TYPE_WARNING = 2


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(create_strategy_language_server_router())
    with TestClient(app) as client:
        yield client


def read_language_server_child_ids() -> set[int]:
    """Return the IDs of the running basedpyright processes whose parent is this test process."""
    child_ids: set[int] = set()
    for process_dir in Path("/proc").iterdir():
        if not process_dir.name.isdigit():
            continue
        try:
            stat_fields = (process_dir / "stat").read_text().rsplit(")", 1)[1].split()
            command_line = (process_dir / "cmdline").read_bytes()
        except OSError:
            continue
        state, parent_id = stat_fields[0], int(stat_fields[1])
        if parent_id == os.getpid() and state != "Z" and b"basedpyright" in command_line:
            child_ids.add(int(process_dir.name))
    return child_ids


def is_running(process_id: int) -> bool:
    try:
        state = (Path("/proc") / str(process_id) / "stat").read_text().rsplit(")", 1)[1].split()[0]
    except OSError:
        return False
    return state != "Z"


def test_completion_lists_the_members_of_nautilus_trader_strategy(test_client: TestClient) -> None:
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        session = LanguageServerSession(websocket)
        session.initialize()
        session.open_document(DOCUMENT_URI, STRATEGY_CODE)

        result = session.request(
            "textDocument/completion",
            {"textDocument": {"uri": DOCUMENT_URI}, "position": {"line": 5, "character": 13}},
        )

    items = cast(list[dict[str, Any]], result["items"] if isinstance(result, dict) else result)
    labels = {item["label"] for item in items}
    assert {"subscribe_bars", "submit_order", "order_factory"} <= labels


def test_publishes_type_errors_of_the_document(test_client: TestClient) -> None:
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        session = LanguageServerSession(websocket)
        session.initialize()
        session.open_document(DOCUMENT_URI, TYPE_ERROR_CODE)

        diagnostics = session.wait_for_diagnostics(DOCUMENT_URI)

    error_lines = [item["range"]["start"]["line"] for item in diagnostics if item.get("severity") == 1]
    assert error_lines == [2]


def test_the_strategy_template_has_no_diagnostics(test_client: TestClient) -> None:
    # A new strategy starts with the template. The editor must not mark problems in code that the user did not write.
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        session = LanguageServerSession(websocket)
        session.initialize()
        session.open_document(DOCUMENT_URI, STRATEGY_TEMPLATE)

        diagnostics = session.wait_for_diagnostics(DOCUMENT_URI)

    assert [(item["range"]["start"]["line"], item["message"]) for item in diagnostics] == []


def test_the_language_server_sends_no_warning_or_error_log_to_the_browser(test_client: TestClient) -> None:
    # `@codemirror/lsp-client` writes each warning and error log of the server to the browser console.
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        session = LanguageServerSession(websocket)
        session.initialize()
        session.open_document(DOCUMENT_URI, STRATEGY_TEMPLATE)
        session.wait_for_diagnostics(DOCUMENT_URI)

    log_messages = [
        (item["params"]["type"], item["params"]["message"])
        for item in session.notifications
        if item.get("method") == "window/logMessage"
    ]
    assert log_messages != []
    assert [message for message in log_messages if message[0] <= LOG_TYPE_WARNING] == []


def test_each_connection_starts_one_process_that_ends_when_the_connection_closes(test_client: TestClient) -> None:
    child_ids_before = read_language_server_child_ids()
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        LanguageServerSession(websocket).initialize()
        connection_child_ids = read_language_server_child_ids() - child_ids_before
        assert len(connection_child_ids) == 1

    deadline = time.monotonic() + PROCESS_END_SECONDS
    while any(is_running(process_id) for process_id in connection_child_ids) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not any(is_running(process_id) for process_id in connection_child_ids)


def test_closes_the_connection_when_a_message_is_not_json(test_client: TestClient) -> None:
    with test_client.websocket_connect(STRATEGY_LANGUAGE_SERVER_PATH) as websocket:
        websocket.send_text("not json")

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_text()

    assert error.value.code == 1003  # WebSocket close code "unsupported data".
