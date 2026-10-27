# Strategies and strategy versions

This document is section 9 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
when the specification became longer than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Strategy editor and strategy versions](https://github.com/Mano-Liaoyan/ATrade/issues/68).

The user writes strategies in the browser. A saved strategy version can run in
a backtest at once, with no deployment.

## 9.1 Storage

- PostgreSQL has two tables: `strategy` (the name) and `strategy_version`
  (code text, sha256, sequence number, time). Do not use git or a PostgreSQL
  extension for versions.
- Strategy versions are append-only. They must not change.
- The sequence number starts at 1 in each strategy and goes up by 1.
- When the code is the same as the latest version, no new version is made.
- The UI shows a version as "strategy name v3".
- To go back, open an old version and save it as a new version.
- Unsaved edits exist only in the browser `localStorage`.
- The backtest table and the forward test table each have a
  `strategy_version_id` foreign key. It must not be null.
- Strategy versions cannot be deleted. A strategy that no backtest or forward
  test uses can be deleted. A strategy in use cannot be deleted.

### 9.1.1 Tables

Migration: `backend/migrations/versions/7c1e4a2b9d30_strategy_create_tables.py`.

| Table | Columns |
|---|---|
| `strategy` | `id`, `name` (unique, 1 to 100 characters), `created_at_utc` |
| `strategy_version` | `id`, `strategy_id`, `version_number` (unique in each strategy, from 1), `code`, `code_sha256`, `created_at_utc` |

- The trigger `strategy_version_append_only` refuses each `UPDATE` of
  `strategy_version`.
- `strategy_version.strategy_id` has `ON DELETE CASCADE`. A strategy delete
  also deletes its versions.
- The tables that later use a version (backtest, forward test) reference
  `strategy_version (id)` with no `ON DELETE` action. When such a reference
  exists, PostgreSQL refuses the strategy delete. The `strategy` capability
  does not read the tables of other capabilities for this rule.
- A save locks the `strategy` row (`SELECT ... FOR UPDATE`). Two saves of the
  same strategy cannot get the same version number.

## 9.2 Strategy file format

- The file has exactly 1 `Strategy` subclass and exactly 1 `StrategyConfig`
  subclass.
- The platform fills in `instrument_id` and `bar_type` at run time.
- All other configuration fields must have default values. This stage has no
  parameter input form.
- NautilusTrader 2.0 requires a keyword-only `__init__` in the strategy
  configuration. The template shows it.
- The strategy template shows how to warm up indicators with `request_bars` in
  `on_start`.
- A new strategy starts with the template as version 1. The template is in
  `backend/src/atrade/strategy/strategy_template.py`. It is a moving average
  cross strategy.
- `strategy` exports `load_strategy_classes(code, work_directory)`. It writes
  the code to a file, imports it, and returns the 2 classes. It raises
  `StrategyFileError` when the file does not have exactly 1 of each. The
  backtest child and the forward test child use it (#76). A forward test
  gives `order_id_tag` and `external_order_instrument_ids` to
  `StrategyConfig.__new__`, so the user `__init__` gets only
  `instrument_id` and `bar_type` ([`forward_test.md`](forward_test.md)
  section 12.15).

## 9.3 Checks before save

The checks run in the Web process. They do not import the user code.

| Check | Blocks save |
|---|---|
| `ast.parse` fails | Yes |
| Not exactly 1 `Strategy` subclass and 1 `StrategyConfig` subclass (AST check) | Yes |
| ruff `F` rule errors | Yes |
| basedpyright type errors | No. The editor shows them live. |

- The AST check counts the top-level classes. A class counts when one of its
  bases is the name `Strategy` (or `StrategyConfig`), or an attribute with
  that name, for example `trading.Strategy`.
- The ruff check runs `python -m ruff check --isolated --no-cache --select F`
  on the code through standard input. The project configuration does not
  apply. A `# noqa` comment in the strategy code turns off a rule on its line.
  `ruff` is a runtime dependency of the backend for this reason.
- When `ast.parse` fails, only the syntax error is returned. Otherwise the
  class problems and the ruff problems are returned together, sorted by line.
- Each problem has a line number and a reason, for example
  `{"line": 14, "message": "Syntax error: invalid syntax."}`.
- The checks run before the comparison with the latest version.

## 9.4 Code completion

- basedpyright only does static analysis. It does not run user code, so it
  needs no isolation.
- Each editor WebSocket connection starts 1 basedpyright child process in the
  `web` container. The process stops when the connection closes.
- The route is `/ws/strategy-language-server`, in
  `backend/src/atrade/strategy/language_server.py`. The public entry exports
  `create_strategy_language_server_router()` and
  `STRATEGY_LANGUAGE_SERVER_PATH`.
- Each WebSocket text message is 1 Language Server Protocol JSON message,
  without the `Content-Length` header. The route adds the header for the child
  process and removes it from the answers. A message that is not JSON closes
  the connection with code `1003`.
- The child process is Node.js with `basedpyright/langserver.index.js
  --stdio`. The route starts Node.js directly, so there is no extra Python
  process. `basedpyright` (and with it `nodejs-wheel-binaries`) is a runtime
  dependency of the backend. On close, the route sends `SIGTERM`, waits 5
  seconds, then sends `SIGKILL`.
- The route sets the basedpyright settings, not the browser. It adds the
  `workspace.configuration` capability to the `initialize` request and answers
  the `workspace/configuration` requests itself:
  - `python.pythonPath` is the Python of the Web process. This environment has
    NautilusTrader 2.0, so basedpyright resolves `Strategy`.
  - `typeCheckingMode` is `standard`. Strategy code is user code, so the
    strict rules of the ATrade code do not apply.
- The browser client is `@codemirror/lsp-client` with
  `languageServerExtensions()` (completion, hover, signature help, live
  diagnostics). The file URI is `file:///atrade/strategy.py`. The file does not
  exist on the server. The request timeout is 15 seconds.
- The editor works without completion when the connection fails. Type errors
  do not block the save (section 9.3).

## 9.5 Comparison

- Compare only two versions of the same strategy. The user selects 2 backtest
  results. The page shows the code diff (`@codemirror/merge`), the metric
  table, and both equity curves on one chart.
- For different strategies, the backtest list shows the metrics side by side.

## 9.6 HTTP routes

The routes are in `backend/src/atrade/strategy/http_routes.py`. The public
entry exports `create_strategy_router(database_url=..., clock=...)`.

| Route | Behavior |
|---|---|
| `POST /api/strategies` | Body `{"name": ...}`. Creates the strategy and version 1 from the template. `201` with the strategy. `409` when the name is in use. `422` when the name is empty or longer than 100 characters. |
| `GET /api/strategies` | `200` with `[{"id", "name", "latest_version_number"}]`, sorted by name. |
| `GET /api/strategies/{strategy_id}` | `200` with `{"id", "name", "created_at_utc", "versions": [{"id", "version_number", "code_sha256", "created_at_utc"}]}`. `404` when the strategy does not exist. |
| `GET /api/strategies/{strategy_id}/versions/{version_number}` | `200` with `{"id", "strategy_id", "version_number", "code", "code_sha256", "created_at_utc"}`. `404` when the version does not exist. |
| `POST /api/strategies/{strategy_id}/versions` | Body `{"code": ...}`. `201` with the new version. `200` with the latest version when the code is the same. `422` with `{"problems": [{"line", "message"}]}` when a check blocks the save. `404` when the strategy does not exist. |
| `DELETE /api/strategies/{strategy_id}` | `204` when the strategy and its versions are deleted. `409` when a backtest or forward test uses a version. `404` when the strategy does not exist. |

There is no route that changes or deletes one version. `PUT` and `DELETE` on a
version path return `405`.

The public entry also exports `read_strategy_version(*, database_url,
strategy_version_id)` for the capabilities that run strategy versions. It
returns `StrategyVersion` (`id`, `strategy_id`, `strategy_name`,
`version_number`, `code`), or `None` when the version does not exist
(backtest, section 10).

## 9.7 Frontend

- `frontend/src/lib/foundation/code_editor/` holds the `CodeEditor` Svelte
  component: CodeMirror 6 (`codemirror`, `@codemirror/lang-python`). It has
  no domain meaning. Its scroll region has a styled scrollbar.
- `CodeEditor` takes more CodeMirror extensions in its `extensions` property.
  The editor page passes the language server extension.
- `frontend/src/lib/strategy/` holds the HTTP client of the strategy routes,
  the version label (`formatVersionLabel`), the drafts in `localStorage`, and
  the language server connection (`connectStrategyLanguageServer`).
- One draft exists for each strategy version. The `localStorage` key is
  `atrade.strategy-draft.<strategy id>.v<version number>`. A save removes the
  draft of the version that the user edited.
- Pages: `/strategies` (list and create form) and `/strategies/<id>` (editor,
  version list, save, delete).
