"""A small Language Server Protocol client over a test WebSocket. It sends the messages that `@codemirror/lsp-client`
sends: JSON only, no `Content-Length` headers.
"""

import itertools
import json
from typing import Any, cast

from starlette.testclient import WebSocketTestSession

# The browser client sends these capabilities (`@codemirror/lsp-client` 6.3.0, without the workspace part).
CLIENT_CAPABILITIES = {
    "textDocument": {
        "completion": {"completionItem": {"snippetSupport": True}, "contextSupport": True},
        "hover": {"contentFormat": ["markdown", "plaintext"]},
        "publishDiagnostics": {"versionSupport": True},
        "diagnostic": {},
    },
}
MAX_MESSAGES = 500


class LanguageServerSession:
    def __init__(self, websocket: WebSocketTestSession) -> None:
        self.websocket = websocket
        self.next_request_id = 0
        self.notifications: list[dict[str, Any]] = []

    def initialize(self) -> None:
        self.request(
            "initialize",
            {"processId": None, "rootUri": "file:///atrade", "capabilities": CLIENT_CAPABILITIES},
        )
        self.notify("initialized", {})

    def open_document(self, uri: str, text: str) -> None:
        self.notify(
            "textDocument/didOpen",
            {"textDocument": {"uri": uri, "languageId": "python", "version": 1, "text": text}},
        )

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.websocket.send_text(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}))

    def request(self, method: str, params: dict[str, Any]) -> Any:
        self.next_request_id += 1
        request_id = self.next_request_id
        self.websocket.send_text(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}))
        for _ in range(MAX_MESSAGES):
            message = self.receive()
            if message.get("id") == request_id and "method" not in message:
                assert "error" not in message, message
                return message.get("result")
        raise AssertionError(f"No response to {method}.")

    def wait_for_diagnostics(self, uri: str) -> list[dict[str, Any]]:
        received = (self.receive() for _ in range(MAX_MESSAGES))
        for message in itertools.chain(list(self.notifications), received):
            if message.get("method") == "textDocument/publishDiagnostics" and message["params"]["uri"] == uri:
                return cast(list[dict[str, Any]], message["params"]["diagnostics"])
        raise AssertionError(f"No diagnostics for {uri}.")

    def receive(self) -> dict[str, Any]:
        message = cast(dict[str, Any], json.loads(self.websocket.receive_text()))
        if "id" in message and "method" in message:
            # A server request. The browser client answers each one with "method not found".
            error = {"code": -32601, "message": "Method not implemented"}
            self.websocket.send_text(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": error}))
        elif "method" in message:
            self.notifications.append(message)
        return message
