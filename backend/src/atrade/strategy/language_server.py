"""Code completion and live type errors: the WebSocket route of the basedpyright language server.

Each WebSocket connection starts 1 basedpyright child process and stops it when the connection closes
(docs/architecture/strategy.md section 9.4). The browser sends Language Server Protocol JSON messages without the
`Content-Length` headers, as `@codemirror/lsp-client` does. This module adds and removes the headers.
"""

import asyncio
import contextlib
import json
import logging
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

STRATEGY_LANGUAGE_SERVER_PATH = "/ws/strategy-language-server"
# Strategy code is user code, not ATrade code: the "standard" mode shows type errors without the strict style rules.
TYPE_CHECKING_MODE = "standard"
STOP_TIMEOUT_SECONDS = 5.0
UNSUPPORTED_DATA_CLOSE_CODE = 1003
HEADER_ENCODING = "ascii"
CONTENT_LENGTH_HEADER = "content-length"

logger = logging.getLogger(__name__)

type JsonObject = dict[str, Any]


def create_strategy_language_server_router() -> APIRouter:
    router = APIRouter()
    router.add_api_websocket_route(STRATEGY_LANGUAGE_SERVER_PATH, serve_language_server)
    return router


async def serve_language_server(websocket: WebSocket) -> None:
    await websocket.accept()
    process = await start_language_server()
    try:
        await relay_messages(websocket, process)
    finally:
        await stop_language_server(process)


def find_language_server_command() -> list[str]:
    # Node.js runs the server directly. The `basedpyright-langserver` script would add a Python parent process.
    node_spec = find_spec("nodejs_wheel")
    server_spec = find_spec("basedpyright")
    if node_spec is None or node_spec.origin is None or server_spec is None or server_spec.origin is None:
        raise RuntimeError("The basedpyright and nodejs-wheel-binaries packages are not installed.")
    node_path = Path(node_spec.origin).parent / "bin" / "node"
    server_script_path = Path(server_spec.origin).parent / "langserver.index.js"
    return [str(node_path), str(server_script_path), "--stdio"]


async def start_language_server() -> asyncio.subprocess.Process:
    command = find_language_server_command()
    return await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )


async def stop_language_server(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), STOP_TIMEOUT_SECONDS)
        except TimeoutError:
            process.kill()
            await process.wait()


async def relay_messages(websocket: WebSocket, process: asyncio.subprocess.Process) -> None:
    browser_task = asyncio.create_task(relay_browser_messages(websocket, process))
    server_task = asyncio.create_task(relay_server_messages(websocket, process))
    done, pending = await asyncio.wait({browser_task, server_task}, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    for task in done:
        task.result()


async def relay_browser_messages(websocket: WebSocket, process: asyncio.subprocess.Process) -> None:
    stdin = cast(asyncio.StreamWriter, process.stdin)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                await websocket.close(code=UNSUPPORTED_DATA_CLOSE_CODE, reason="The message is not JSON.")
                return
            write_message(stdin, adjust_browser_message(message))
            await stdin.drain()
    except WebSocketDisconnect:
        return


async def relay_server_messages(websocket: WebSocket, process: asyncio.subprocess.Process) -> None:
    stdin = cast(asyncio.StreamWriter, process.stdin)
    stdout = cast(asyncio.StreamReader, process.stdout)
    while True:
        message = await read_message(stdout)
        if message is None:
            logger.warning("The basedpyright language server stopped. Exit code: %s.", await process.wait())
            with contextlib.suppress(RuntimeError):
                await websocket.close()
            return
        if message.get("method") == "workspace/configuration":
            # The Web process sets the configuration. The browser does not see these requests.
            write_message(stdin, answer_configuration_request(message))
            await stdin.drain()
            continue
        await websocket.send_text(json.dumps(message))


def adjust_browser_message(message: object) -> object:
    if not isinstance(message, dict):
        return message
    request = cast(JsonObject, message)
    if request.get("method") != "initialize":
        return request
    params = cast(JsonObject, request.setdefault("params", {}))
    capabilities = cast(JsonObject, params.setdefault("capabilities", {}))
    workspace_capabilities = cast(JsonObject, capabilities.setdefault("workspace", {}))
    # basedpyright reads its settings only from a client with this capability.
    workspace_capabilities["configuration"] = True
    return request


def answer_configuration_request(request: JsonObject) -> JsonObject:
    items = cast(list[JsonObject], request.get("params", {}).get("items", []))
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": [read_setting_section(item.get("section")) for item in items],
    }


def read_setting_section(section: object) -> JsonObject | None:
    # basedpyright 1.40 asks for the top sections "python", "basedpyright", and "pyright". It reads the analysis
    # settings from the "analysis" key of the "basedpyright" or "python" section. Without them, basedpyright uses its
    # default "recommended" mode, which marks unknown NautilusTrader types in the strategy template.
    analysis_settings: JsonObject = {"typeCheckingMode": TYPE_CHECKING_MODE, "diagnosticMode": "openFilesOnly"}
    match section:
        case "python":
            # The Web process environment has NautilusTrader 2.0 and its `.pyi` stubs.
            return {"pythonPath": sys.executable, "analysis": analysis_settings}
        case "basedpyright":
            return {"analysis": analysis_settings}
        case "basedpyright.analysis" | "python.analysis":
            return analysis_settings
        case _:
            return None


def write_message(stdin: asyncio.StreamWriter, message: object) -> None:
    body = json.dumps(message).encode()
    stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode(HEADER_ENCODING) + body)


async def read_message(stdout: asyncio.StreamReader) -> JsonObject | None:
    content_length: int | None = None
    while True:
        header_line = await stdout.readline()
        if not header_line:
            return None
        header = header_line.decode(HEADER_ENCODING).strip()
        if not header:
            break
        name, _, value = header.partition(":")
        if name.strip().lower() == CONTENT_LENGTH_HEADER:
            content_length = int(value)
    if content_length is None:
        return None
    try:
        body = await stdout.readexactly(content_length)
    except asyncio.IncompleteReadError:
        return None
    return cast(JsonObject, json.loads(body))
