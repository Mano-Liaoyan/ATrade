# Strategies and strategy versions

This document is section 9 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It was moved to its own file
when the specification became longer than 1000 lines (section 18). Terms have
the meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Strategy editor and strategy versions](https://github.com/Mano-Liaoyan/ATrade/issues/68),
[UI references: screens, rule builder, and AI assistant](https://github.com/Mano-Liaoyan/ATrade/issues/135),
[Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138),
[Content of the strategy template library](https://github.com/Mano-Liaoyan/ATrade/issues/139).

The user writes strategies in the browser, as code or with the rule builder
(section 9.8). A new strategy starts from a start point: "Blank code",
"Blank rules", or a strategy template (section 9.9). A saved strategy version
can run in a backtest at once, with no deployment.

### Implementation phases of this section

The planning map
[Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129)
puts the new parts of this section in phases.

| Phase | Parts |
|---|---|
| Existing | Sections 9.1 to 9.7, without the parts marked with a phase. |
| Phase 1 | The `source` and `rules` columns (section 9.1.1). The rule builder for one instrument (section 9.8). The single-instrument rule templates S1 to S3 (section 9.9). The "New strategy" dialog (section 9.7.1). Only the existing single-instrument backtest runs them. |
| Phase 2 | The AI assistant values of the version source and the conversation ID (section 9.1.1, [ADR 0004](../adr/0004-ai-assistant-saves-strategy-versions.md)). The AI assistant tool that reads a version also returns its rules. |
| Phase 3 | The universe mode of the rule builder (section 9.8.6) and the multi-instrument code templates M1 to M4 (section 9.9.3). They need the multi-instrument backtest. |

## 9.1 Storage

- PostgreSQL has two tables: `strategy` (the name) and `strategy_version`
  (code text, sha256, sequence number, time). Do not use git or a PostgreSQL
  extension for versions.
- Strategy versions are append-only. They must not change.
- The sequence number starts at 1 in each strategy and goes up by 1.
- When the code is the same as the latest version, no new version is made.
  A rule builder save (section 9.8) makes no new version when the code and
  the rules are both the same as the latest version.
- The UI shows a version as "strategy name v3".
- To go back, open an old version and save it as a new version.
- Unsaved edits exist only in the browser `localStorage`.
- The backtest table and the forward test table each have a
  `strategy_version_id` foreign key. It must not be null.
- Strategy versions cannot be deleted. A strategy that no backtest or forward
  test uses can be deleted. A strategy in use cannot be deleted.

### 9.1.1 Tables

Migrations: `backend/migrations/versions/7c1e4a2b9d30_strategy_create_tables.py`,
`backend/migrations/versions/c4a8e2f6b913_strategy_add_version_source_and_rules.py`,
and `backend/migrations/versions/2f7a9c3e5b14_strategy_add_ai_assistant_source_and_discard.py`.

| Table | Columns |
|---|---|
| `strategy` | `id`, `name` (unique, 1 to 100 characters), `created_at_utc` |
| `strategy_version` | `id`, `strategy_id`, `version_number` (unique in each strategy, from 1), `code`, `code_sha256`, `created_at_utc`, `source` (phase 1), `rules` (phase 1), `conversation_id` (phase 2) |

New columns of `strategy_version`:

| Column | Phase | Type | Content |
|---|---|---|---|
| `source` | 1 | text, not null | The version source: `user`, `rule_builder`, or `ai_assistant` (phase 2). Existing rows get `user`. |
| `rules` | 1 | `jsonb`, null | The rules of the rule builder (section 9.8.2). Only versions with the source `rule_builder` have a value. All other versions have null. |
| `conversation_id` | 2 | `bigint`, null | The conversation that saved the version. Foreign key to `assistant_conversation` with `ON DELETE SET NULL`. Only versions with the source `ai_assistant` have a value (CHECK `strategy_version_conversation_check`). |

- Source: [ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md)
  ([#138](https://github.com/Mano-Liaoyan/ATrade/issues/138)) adds the value
  `rule_builder` to the version source of
  [ADR 0004](../adr/0004-ai-assistant-saves-strategy-versions.md).
- The trigger `strategy_version_append_only` also covers `rules`. The rules
  of a version do not change.
- The migration that adds the columns includes the capability name, for
  example `<revision>_strategy_add_version_source_and_rules.py`.
- Decided (#171): the named CHECK constraint `strategy_version_source_check`
  holds the values of `source`, not a PostgreSQL enum. Phase 2 drops the
  constraint and adds it again with `ai_assistant`.
- Decided (#171): `source` has the default `user`. The default fills the
  existing rows, because an `UPDATE` would hit the trigger. A save sets the
  source explicitly.
- Decided (#171): `read_strategy_version` does not return `source` and
  `rules`. Section 9.6 does not ask for them. A later change can add them
  when a capability needs them.
- Decided (#180): phase 2 adds `ai_assistant` to the constraint
  `strategy_version_source_check`.
- Decided (#180): the table `strategy_version_discard`
  (`strategy_version_id` primary key, foreign key to `strategy_version` with
  `ON DELETE CASCADE`, and `discarded_at_utc`) holds the discarded mark (ADR
  0004). A version is discarded when the table has a row for it. A discard
  does not change the `strategy_version` row.
- Decided (#180): the trigger `strategy_version_append_only` still refuses
  each `UPDATE` statement, also of `conversation_id`. It lets through only
  the `ON DELETE SET NULL` of `conversation_id` when a conversation is
  deleted: PostgreSQL runs that update in the foreign key trigger
  (`pg_trigger_depth() > 1`), and it changes no other column.

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
  configuration. The "Blank code" start point shows it.
- The "Blank code" start point shows how to warm up indicators with
  `request_bars` in `on_start`. The warm-up length is 3 average periods of bars, and 7 days at
  least (`find_warm_up_length`). It is not a fixed 60 days, because 60 days of
  1-minute bars need many IBKR historical data requests. In a backtest,
  `request_bars` gets the saved bars before the start (backtest section
  10.3.1). For a rule builder version, the platform gives the last bars that
  the longest indicator of the rules needs (#164), and the generated code
  asks for them (section 9.8.3).
- A new strategy starts from a start point as version 1 (section 9.9.1).
- The "Blank code" start point is the code in
  `backend/src/atrade/strategy/strategy_template.py`. It is a moving average
  cross strategy: buy 10 shares when the close goes above SMA(20), sell when
  it goes below. It shows only the file format. It cites no research, so it
  is not a strategy template and is not in the template library
  ([#139](https://github.com/Mano-Liaoyan/ATrade/issues/139), T8).
- The "Blank rules" start point and the rule templates make version 1 with
  code from the rule builder (section 9.8). The code templates make version 1
  with their code (section 9.9).
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
  the `workspace/configuration` requests itself. basedpyright 1.40 asks for
  the sections `python`, `basedpyright`, and `pyright`, and reads the analysis
  settings from the `analysis` key of the `python` and `basedpyright` answers:
  - `python.pythonPath` is the Python of the Web process. This environment has
    NautilusTrader 2.0, so basedpyright resolves `Strategy`.
  - `analysis.typeCheckingMode` is `standard`. Strategy code is user code, so
    the strict rules of the ATrade code do not apply. Without this setting,
    basedpyright uses its default `recommended` mode, which marks unknown
    NautilusTrader types in the "Blank code" start point.
  - The "Blank code" start point (section 9.2) has no diagnostics. A backend
    test checks this through the route.
- basedpyright reads `workspaceFolders`, not the `rootUri` that the browser
  sends. Without a workspace folder that exists, it logs the warning
  `File or directory "/<default workspace root>" does not exist.`, and the
  browser client writes it to the console. So the route creates an empty
  temporary directory for each connection and sets it as the only workspace
  folder of the `initialize` request. A backend test checks that the server
  sends no warning or error log.
- The browser client is `@codemirror/lsp-client` with
  `languageServerExtensions()` (completion, hover, signature help, live
  diagnostics). The file URI is `file:///atrade/strategy.py`. The file does not
  exist on the server. The request timeout is 15 seconds.
- The editor works without completion when the connection fails. Type errors
  do not block the save (section 9.3).
- Tab accepts the selected completion. When no completion list is open, Tab
  indents. Escape and then Tab or Shift+Tab moves the focus out of the editor.

## 9.5 Comparison

- Compare only two versions of the same strategy. The user selects 2 backtest
  results. The page shows one key metric row for each backtest
  (`ComparedKeyMetrics`), both equity and drawdown curves on one chart
  (`EquityDrawdownChart`), and the code diff (`@codemirror/merge`).
- For different strategies, the backtest list shows the metrics side by side.
- Implementation (#72): backtest section 10.7.

## 9.6 HTTP routes

The routes are in `backend/src/atrade/strategy/http_routes.py`. The public
entry exports `create_strategy_router(database_url=..., clock=...)`.

| Route | Behavior |
|---|---|
| `POST /api/strategies` | Body `{"name": ..., "start_from": ...}`. `start_from` is `blank_code`, `blank_rules`, or a template ID (section 9.9). Without `start_from`, the start point is `blank_code`. Creates the strategy and version 1 from the start point (section 9.9.1). `201` with the strategy. `409` when the name is in use. `422` when the name is empty or longer than 100 characters, or when `start_from` is not a known start point. |
| `GET /api/strategies` | `200` with `[{"id", "name", "latest_version_number"}]`, sorted by name. |
| `GET /api/strategies/{strategy_id}` | `200` with `{"id", "name", "created_at_utc", "versions": [{"id", "version_number", "code_sha256", "created_at_utc", "source", "conversation_id", "discarded"}]}`. `404` when the strategy does not exist. |
| `GET /api/strategies/{strategy_id}/versions/{version_number}` | `200` with `{"id", "strategy_id", "version_number", "code", "code_sha256", "created_at_utc", "source", "rules", "conversation_id", "discarded"}`. `rules` is null when the version has no rules. `conversation_id` is null when the AI assistant did not save the version. `discarded` is a boolean (the discarded mark). `404` when the version does not exist. |
| `POST /api/strategies/{strategy_id}/versions/{version_number}/discard` (phase 2) | Adds the discarded mark to a version that the AI assistant saved. `200` with the version as `GET .../versions/{version_number}` gives it. A version that is already discarded also gets `200`. `409` when the source of the version is not `ai_assistant`. `404` when the version does not exist. |
| `POST /api/strategies/{strategy_id}/versions` | Body `{"code": ...}` or `{"rules": ...}`, exactly one of the two. With `code`, the source is `user`. With `rules`, the source is `rule_builder`: the route checks the rules (section 9.8.2), makes the code (section 9.8.3), and saves both. The checks of section 9.3 run on the code in both cases. `201` with the new version. `200` with the latest version when the code is the same (and, for a `rules` body, the rules are also the same). `422` with `{"problems": [{"line", "message"}]}` when a check blocks the save. `422` with the FastAPI validation body when the body has both or neither of `code` and `rules`, or when the rules do not match the rules format (section 9.8.2). `404` when the strategy does not exist. Port 8001 (phase 2) accepts only `{"code": ...}`; it saves with the source `ai_assistant` and the conversation ID (`assistant.md` 25.3.2). |
| `POST /api/strategy-rules/code` (phase 1) | Body `{"rules": ...}`. Makes the code from the rules and saves nothing. `200` with `{"code"}`. `422` with the FastAPI validation body when the rules do not match the rules format (section 9.8.2). The "Rules" tab uses it for the read-only code (section 9.8.5). |
| `GET /api/strategy-templates` (phase 1) | `200` with the template list (section 9.9.2): `[{"id", "name", "kind", "entry", "exit", "defaults", "market", "bar_period", "evidence", "sources": [{"label", "url"}], "differs_from_source"}]`, in the order of section 9.9. `kind` is `rules` or `code`. The "New strategy" dialog uses it. |
| `DELETE /api/strategies/{strategy_id}` | `204` when the strategy and its versions are deleted. `409` when a backtest or forward test uses a version. `404` when the strategy does not exist. |

There is no route that changes or deletes one version. `PUT` and `DELETE` on a
version path return `405`.

The public entry also exports `save_ai_assistant_version(*, database_url,
strategy_id, code, conversation_id, created_at_utc)` for port 8001 (#181,
`docs/architecture/assistant.md` 25.5). It runs the checks of section 9.3 and
saves like the code body of `POST .../versions`, with the source
`ai_assistant` and the conversation ID. It returns `SavedVersion`
(`version`, `is_new_version`), the list of `CodeProblem` when a check blocks
the save, or `None` when the strategy does not exist. The route of port 8000
always saves the source `user` (or `rule_builder`) and no conversation.

The public entry also exports `read_strategy_version(*, database_url,
strategy_version_id)` for the capabilities that run strategy versions. It
returns `StrategyVersion` (`id`, `strategy_id`, `strategy_name`,
`version_number`, `code`), or `None` when the version does not exist
(backtest, section 10). `read_strategy_versions(*, database_url,
strategy_version_ids)` reads many versions with one connection and returns
them by ID. A missing ID is not in the result. The forward test list uses it
(section 12.13).

## 9.7 Frontend

- `frontend/src/lib/foundation/code_editor/` holds the `CodeEditor` Svelte
  component: CodeMirror 6 (`codemirror`, `@codemirror/lang-python`). It has
  no domain meaning. Its scroll region has a styled scrollbar.
- `CodeEditor` and `CodeDiff` use one theme, `createCodeTheme()` in
  `code_theme.ts`. The editor parts (gutter, active line, selection, tooltips,
  diff line colors) use the Carbon tokens (`--cds-*`) of the current theme.
  The syntax colors are in `code_colors.ts` (Carbon palette colors). A Vitest
  test checks that each syntax color has WCAG AA contrast (4.5:1) on the code
  background. The theme follows `prefers-color-scheme` and also changes when
  the operating system scheme changes. It sets `EditorView.darkTheme`, so the
  CodeMirror base themes also use their dark variants.
- `CodeEditor` takes more CodeMirror extensions in its `extensions` property.
  The editor page passes the language server extension.
- `frontend/src/lib/strategy/` holds the HTTP client of the strategy routes,
  the version label (`formatVersionLabel`), the drafts in `localStorage`, and
  the language server connection (`connectStrategyLanguageServer`).
- One draft exists for each strategy version. The `localStorage` key is
  `atrade.strategy-draft.<strategy id>.v<version number>`. A save removes the
  draft of the version that the user edited.
- Pages: `/strategies/<id>` is the strategy workbench (list, new strategy,
  editor, version list, save, delete, Run backtest, Start forward test, and
  the backtest results; docs/architecture.md section 13). `/strategies` shows
  the first strategy of the list. `/strategies/<id>` opens the latest version.
  `/strategies/<id>/versions/<n>` (`routes/strategies/[strategyId]/versions/[versionNumber]`)
  opens version n. On this address, a change of the open version (the version
  `Select` or a save) changes the address to that version (a shallow `goto`),
  so a reload opens the same version. The strategy links "<name> vN" of the
  backtest page, the forward test page, and the forward test comparison page
  open this address. The backtest comparison page compares 2 versions, so its
  strategy name link opens `/strategies/<id>`.

### 9.7.1 "New strategy" dialog (phase 1)

Source: [Content of the strategy template library](https://github.com/Mano-Liaoyan/ATrade/issues/139)
(T9, option 3) and [Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138)
(Q6).

- The "New strategy" button of the "Strategies" `SideColumn` opens a wide
  `Dialog` (Bits UI, through `src/lib/foundation/`).
- The left side is the list of start points (section 9.9.1). "Blank code"
  and "Blank rules" are first. The "Templates" group follows, in the order
  of `GET /api/strategy-templates`.
- The right side shows the selected start point. For a strategy template,
  it shows only label and value rows:

  | Label | Value |
  |---|---|
  | Entry | The entry rule. |
  | Exit | The exit rule. |
  | Defaults | The default parameters. |
  | Market | The market that the template is for. |
  | Bar period | The bar period, for example "1 day". |
  | Evidence | The evidence grade (section 9.9.2). |
  | Sources | 1 link for each source. |
  | Differs from source | The differences from the source research. |

- For "Blank code" and "Blank rules", the right side shows only the name.
- The dialog has no help sentence, no subtitle, and no description text
  (AGENTS.md, Frontend Design Rules, rule one).
- The "Strategy name" field and the "Create strategy" button do not change.
  "Create strategy" sends `POST /api/strategies` with `name` and
  `start_from`.
- Phase 1 lists "Blank code", "Blank rules", and the templates S1 to S3.
  Phase 3 adds the code templates M1 to M4.

## 9.8 Rule builder (phase 1)

Sources: [Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138),
[UI references: screens, rule builder, and AI assistant](https://github.com/Mano-Liaoyan/ATrade/issues/135),
[ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md).

The rule builder writes a normal strategy version from rules. The rules are
entry conditions, exit conditions, and a position size. The strategy version
runs in a backtest and in a forward test like all other strategy versions.

### 9.8.1 Scope of phase 1

- One instrument only. The universe mode comes in phase 3 (section 9.8.6).
- Long only.
- The rules are checked at the close of each bar.
- When any indicator of the rules has no value, no rule runs on that bar
  ([ADR 0001](../adr/0001-one-indicator-definition-for-screens-and-strategies.md)).
- Bracket orders (`OrderFactory.bracket`) and trailing stops are not in
  phase 1. They can come later.

### 9.8.2 Rules

One condition is one row: left side, comparison, right side.

| Part | Values |
|---|---|
| Left side | A price (Close, Open, High, Low) or one of the 11 indicators of [#136](https://github.com/Mano-Liaoyan/ATrade/issues/136): SMA, EMA, 12-1 momentum, distance to 52-week high, realized volatility, ATR, average trading value, RSI, MACD, Bollinger Bands, Donchian channel. |
| Line of a multi-line indicator | MACD: MACD line, signal line, histogram. Bollinger Bands and Donchian channel: upper, middle, lower. |
| Comparison | above, below, at or above, at or below, crosses above, crosses below. |
| Right side | A number, a price, or an indicator. |

- "Crosses above": on the previous bar, the left side is at or below the
  right side. On this bar, the left side is above the right side.
- "Crosses below" is the mirror of "crosses above".
- Each block (entry, exit) has 1 group. A group is "All of" or "Any of".
- A group can hold conditions and groups. A group in a group cannot hold a
  group. So the maximum depth is 1 nested group, for example
  `A and (B or C)`.
- Each indicator in a condition has its parameters, for example RSI period
  14.

Position size (Settings block):

| Option | Quantity |
|---|---|
| Fixed shares | The share count. |
| Percent of equity | Equity × percent / close price, rounded down to whole shares. |

Exit items (Exit block). The user can select more than one:

| Exit item | Value |
|---|---|
| Stop loss | Percent. |
| Take profit | Percent. |
| Exit after N bars | N. |
| Exit when the entry conditions are no longer true | None. |
| Exit conditions | 1 group, as in the entry block. |

- When the position is 0 and the entry group is true at the bar close, the
  strategy buys with a market order.
- When the position is above 0 and a selected exit item is true at the bar
  close, the strategy sells the full position. It uses a market order.
- A stop loss checked at the bar close fills below the stop price after a
  gap or a large fall in the bar. This is a known effect of the phase 1
  design (#138, Q4).

The `rules` column (section 9.1.1) holds the rules as JSON. The JSON holds
the Settings block (position size and the template ID, section 9.9.2), the
entry group, and the exit items.

Decided (#172): the rules format. `backend/src/atrade/strategy/strategy_rules.py`
(`StrategyRules`, Pydantic) checks it. An unknown field is a format error.

```json
{
  "format_version": 1,
  "settings": {
    "position_size": {"type": "fixed_shares", "shares": 10},
    "template_id": null
  },
  "entry": {
    "type": "group",
    "match": "all_of",
    "items": [
      {
        "type": "condition",
        "left": {"type": "indicator", "indicator": "rsi", "parameters": {"period": 14}},
        "comparison": "below",
        "right": {"type": "number", "value": 30}
      },
      {"type": "group", "match": "any_of", "items": []}
    ]
  },
  "exits": {
    "stop_loss_percent": 5,
    "take_profit_percent": null,
    "exit_after_bars": null,
    "exit_when_entry_is_false": false,
    "exit_group": null
  }
}
```

| Part | Format |
|---|---|
| `format_version` | `1`. |
| `position_size` | `{"type": "fixed_shares", "shares": <int, 1 or more>}` or `{"type": "percent_of_equity", "percent": <number, more than 0, at most 100>}`. |
| `template_id` | A string of 1 to 100 characters, or null. #175 sets the template IDs. |
| Group | `{"type": "group", "match": "all_of" or "any_of", "items": [...]}`. The items of the top group are conditions and groups. The items of a group in a group are conditions only. |
| Condition | `{"type": "condition", "left", "comparison", "right"}`. `comparison` is `above`, `below`, `at_or_above`, `at_or_below`, `crosses_above`, or `crosses_below`. |
| Operand | `{"type": "price", "price": "close" / "open" / "high" / "low"}`, `{"type": "number", "value": <int or float>}` (right side only), or `{"type": "indicator", ...}` with the fields of a stored indicator reference ([`indicator.md`](indicator.md) section 23.6). `check_indicator_reference` checks the reference. |
| `exits` | Each item is not selected when it is null (or `false`). `stop_loss_percent`: more than 0, less than 100. `take_profit_percent`: more than 0. `exit_after_bars`: an int, 1 or more. `exit_group`: a group, as the entry group. |

- A rules body that does not match the format gets the FastAPI `422`
  validation body (`{"detail": [{"loc", "msg", ...}]}`). `loc` is the path
  of the wrong part in the rules.
- An empty group is false. Empty entry rules never buy.
- The reference price of the stop loss and the take profit is the average
  fill price of the entry (`Position.avg_px_open`). The stop loss is true
  when the close is at or below `avg_px_open × (1 − percent / 100)`. The
  take profit is true when the close is at or above
  `avg_px_open × (1 + percent / 100)`.
- "Exit after N bars" counts the bars that close while the position is open.
  The bar of the entry order is bar 0. The exit is true on bar N.
- The percent of equity uses the account balance total in the account
  currency at the entry bar.

### 9.8.3 Code from the rules

- The backend makes the code from the rules. One function makes it. The
  save route and `POST /api/strategy-rules/code` use the same function.
- The same rules always give the same code.
- The code has the file format of section 9.2: 1 `Strategy` subclass and
  1 `StrategyConfig` subclass with a keyword-only `__init__`.
- Each indicator parameter and each number threshold is a configuration
  field with an `int` or `float` type annotation and a default value. A
  parameter sweep can change these fields without the rule builder (phase 3,
  [#142](https://github.com/Mano-Liaoyan/ATrade/issues/142)).
- The code gets its indicators from `atrade.indicator` (ADR 0001) and
  registers them with `register_indicator_for_bars`.
- When the rules hold a template ID, the first line of the code is the
  template docstring (section 9.9.2). The function writes it each time that
  it makes the code.
- The code must pass the checks of section 9.3. Backend tests check this for
  each rule template and for empty rules.
- Decided (#172): `make_rules_code(rules)` in
  `backend/src/atrade/strategy/rules_code.py` makes the code. The classes are
  `RulesConfig` and `RulesStrategy`. Operands with the same indicator and the
  same parameters share 1 indicator object. The indicator objects are named
  `<catalog key>_<n>` (for example `rsi_1`) in the order of first use: the
  entry group first, then the exit items.
- Decided (#172): the configuration fields are `<indicator object>_<parameter>`
  (for example `rsi_1_period`) for each indicator parameter,
  `threshold_<n>` for each number, and also `stop_loss_percent`,
  `take_profit_percent`, `exit_after_bars`, `position_shares`, and
  `equity_percent` when the rules have them. Each field has the type of its
  JSON value (`int` or `float`).
- Decided (#172): at each bar close, the code reads the prices and the
  indicator outputs of the rules. When an output has no value, or an order
  of the strategy is open or in flight, no rule runs on that bar. A cross
  compares with the values of the previous bar. A cross is false when the
  previous bar had no value. The code warms up the indicators with
  `request_bars` in `on_start`: the bar count is the largest look-back count
  of the indicators ([`indicator.md`](indicator.md) section 23.4). The
  request goes `bar period × count × 6` back, and 7 days at least. The
  platform gives only the last bars of this count (#164,
  [`backtest.md`](backtest.md) section 10.3.1).

### 9.8.4 One-way editing

Source: [ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md).

- The rule builder makes code from rules. It never reads code back into
  rules.
- A save of code (by the user, or in phase 2 by the AI assistant) makes a
  version without rules.
- The "Rules" tab opens the rules of the latest version with rules ("vM").
- When the open version "vN" has no rules and is newer than vM, the tab shows
  a warning: "Code of vN changed. Rules are from vM."
- "Save rules as new version" saves the rules with
  `POST /api/strategies/{strategy_id}/versions` and the body `{"rules": ...}`.
  The new code replaces the code changes of vN.
- In the warning case, ATrade shows the diff (`CodeDiff`) of the vN code and
  the new code before the save.
- In phase 2, the AI assistant does not change rules. Its code changes count
  as code changes by hand. The AI assistant tool that reads a version also
  returns the rules JSON.

### 9.8.5 "Rules" tab

Source: [Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138)
(Q6, layout A). Prototype (private):
<https://claude.ai/artifact/8uqhq4d97NhPX8yVZ4QeTQ>.

- The editor panel of the strategy page (docs/architecture.md section 13)
  has the tab "Rules" next to the tab `strategy.py`.
- The left side of "Rules" is the builder with 3 blocks: Settings, Entry,
  and Exit.
- The right side is the code from the rules, read-only (`CodeEditor`). It
  changes after each rule change (`POST /api/strategy-rules/code`).
- The lines of the code that a rule change changed are highlighted.
- After a rule change, the code region scrolls to the first highlighted
  line. Only the code region scrolls. The page does not scroll.
- The builder region and the code region each scroll in their own
  `ScrollRegion`, with a styled scroll track.
- Selects use Bits UI through `src/lib/foundation/`.
- The tab shows text only where the user must act: the warning of section
  9.8.4 and the "Save rules as new version" button.
- The tab has none of these items (AGENTS.md, Frontend Design Rules, rule one):
  - explanatory sentences, for example "Exits are checked at each bar
    close"
  - status tags, for example "Generated · read-only"
  - an information line or a status list below the code.
- Colors are neutral Carbon tokens only.

### 9.8.6 Universe mode (phase 3)

Source: [Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138) (Q5).
It needs the multi-instrument backtest of
[#142](https://github.com/Mano-Liaoyan/ATrade/issues/142).

- The entry conditions become a filter. At each rebalance, only the
  instruments that pass the filter get a rank.
- Settings: the rank indicator and the direction (high to low, or low to
  high). Also the number of instruments to hold (N) and the rebalance period
  (weekly, monthly, quarterly).
- Equal weight. The strategy sells first. It buys after the sell orders
  fill (#142).
- The exit items are checked on each bar, for each instrument.

### 9.8.7 Left to the implementation

- The rules that "Blank rules" holds (for example the position size).
- What the "Rules" tab shows for a strategy that has no version with rules.
- What the "Rules" tab shows when the open version is an older version with
  rules than vM.
- The code that the line highlight compares with (the code before the last
  rule change, or the code of the open version).
- How Save version and Ctrl S act while the "Rules" tab is open.
- The `localStorage` draft of unsaved rules (section 9.1 keeps all unsaved
  edits in the browser).
- The delay between a rule change and the code request.
- The buttons of the diff before the save.
- Decided (#198): the platform tells the strategy the universe of each
  universe period with NautilusTrader custom data. The strategy calls
  `subscribe_data(DataType("UniverseUpdate"))` and gets the bar types of the
  members in `on_data(data)` as `data.data.bar_types`. Its configuration has
  no `instrument_id`, no `bar_type`, and no universe field
  ([`backtest.md`](backtest.md) section 10.10.8).

## 9.9 Strategy templates

Source: [Content of the strategy template library](https://github.com/Mano-Liaoyan/ATrade/issues/139).
No ADR: the content and the gate of the library can change at low cost.

A strategy template is a named start point for a new strategy, with sources
in published research. A rule template holds rules for the rule builder. A
code template holds strategy code.

### 9.9.1 Start points

| Start point | Phase | Version 1 |
|---|---|---|
| Blank code | Existing | The code of `strategy_template.py` (section 9.2). Source `user`. |
| Blank rules | 1 | Rules with no conditions, and the code from them. Source `rule_builder`. |
| Rule template (S1 to S3) | 1 | The rules of the template, and the code from them. Source `rule_builder`. |
| Code template (M1 to M4) | 3 | The code of the template. |

### 9.9.2 Template list and gate

- The backend has 1 template list in the `strategy` module. Each entry
  holds these items:
  - the ID, the name, and the kind (rules or code)
  - the entry rule, the exit rule, and the default parameters
  - the market and the bar period
  - the evidence grade and the sources (DOI links)
  - the differences from the source research
- A rule template also holds its rules. A code template also holds its code.
- The code of each template starts with a docstring. The docstring holds the
  name, the sources, the evidence grade, the market, the bar period, and the
  differences from the source research.
- The rules JSON of a rule template holds the template ID. So the rule
  builder writes the docstring each time that it makes the code (section
  9.8.3).
- The evidence grades are the 4 grades A to D of
  [Academic and industry evidence for classic indicators and factors](https://github.com/Mano-Liaoyan/ATrade/issues/130).
  A is the strongest. D has only industry use and no reliable peer-reviewed
  evidence.
- Gate: a template holds only rules with grade A or B for its market and its
  use. D-grade indicators (RSI, MACD, Bollinger Bands) stay available in the
  rule builder and in code. They are not templates.
- A template that the rule builder can express exactly is a rule template.
  All other templates are code templates.
- The default parameters are the parameters of the source research. ATrade
  does not tune them on its own data. The user can change them later with a
  parameter sweep, and each run counts in the trial count.

### 9.9.3 Templates

Phase 1: single-instrument rule templates. All use 1-day bars, long only,
and a position of 95% of equity. The market is US index ETFs. The reason for
95%: a market order fills at the open of the next bar, so 5% cash stays for
commissions and the open gap.

| # | Name | Entry | Exit | Defaults | Sources | Evidence |
|---|---|---|---|---|---|---|
| S1 | 200-day trend | Close above SMA | Entry conditions no longer true | SMA 200 | [Brock, Lakonishok & LeBaron 1992](https://doi.org/10.1111/j.1540-6261.1992.tb04681.x), [Faber 2007](https://doi.org/10.3905/jwm.2007.674809) | B (index), C (single stock) |
| S2 | 50-day range break | High at or above Donchian channel upper | Exit after N bars | Donchian 50, N = 10 | [Brock, Lakonishok & LeBaron 1992](https://doi.org/10.1111/j.1540-6261.1992.tb04681.x) | B (index), C (single stock) |
| S3 | 12-month time-series momentum | 12-month momentum above 0 | Entry conditions no longer true | Look back 252 days, skip 0 days | [Moskowitz, Ooi & Pedersen 2012](https://doi.org/10.1016/j.jfineco.2011.11.003) | B (index and futures), C (single stock) |

- Differences from the sources: the rule builder checks on each bar. Faber
  and Moskowitz et al. check 1 time each month. S2 uses the high of the bar
  for the break.
- S1 uses "Close above", not "Close crosses above". A cross is true on one
  bar only, so "Entry conditions no longer true" would sell 1 bar after the
  entry. Brock et al. and Faber hold while the price is above the average.
- S2 uses "High at or above", not "Close crosses above". The Donchian upper
  value at time t includes the high of the bar at t (ADR 0001), so the close
  can never cross above it.
- S3 uses the 12-1 momentum indicator with 0 skipped days. The indicator
  accepts skip 0 (section 21.1 of [`docs/architecture.md`](../architecture.md), #162).
- No Hong Kong templates: tests of moving average rules in Hong Kong show
  small effects (Bessembinder & Chan 1995).

Phase 3: multi-instrument code templates. All use 1-day bars, long only,
equal weight, and a rebalance on the first trading day of each month. The
strategy sells first and buys after the sell orders fill (#142). The default
universe is the US top 500 of the current quarter.

| # | Name | Rule | Defaults | Sources | Evidence | Market |
|---|---|---|---|---|---|---|
| M1 | Cross-sectional momentum | Hold the N instruments with the highest 12-1 momentum. | N = 50 | [Jegadeesh & Titman 1993](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x), Carhart 1997 | A (US), B (HK) | US, HK |
| M2 | Low volatility | Hold the N instruments with the lowest 252-day realized volatility. | N = 50 | [Ang, Hodrick, Xing & Zhang 2006](https://doi.org/10.1111/j.1540-6261.2006.00836.x), [Blitz & van Vliet 2007](https://doi.org/10.3905/jpm.2007.698039), [Frazzini & Pedersen 2014](https://doi.org/10.1016/j.jfineco.2013.10.005) | A (risk-adjusted) | US, HK |
| M3 | 52-week high | Hold the N instruments nearest to their 52-week high. | N = 50 | [George & Hwang 2004](https://doi.org/10.1111/j.1540-6261.2004.00695.x) | B | US |
| M4 | Volatility-adjusted momentum | M1. Total position = target volatility / volatility of the strategy in the last 6 months, at most 100%. | Target annual volatility 12% | [Barroso & Santa-Clara 2015](https://doi.org/10.1016/j.jfineco.2014.11.010) | B | US |

- Differences from the sources: the momentum portfolios of the sources also
  sell the losers short. ATrade is long only. The M4 source can use
  leverage. ATrade stops at 100%.
- Fundamental templates (value, quality, Piotroski) need a financial data
  source. They get their own ticket.

### 9.9.4 Facts to check before the implementation

The defaults come from the sources (section 9.9.2), so the implementation
must check them first.

| Fact | How to check |
|---|---|
| The Brock et al. range break holds for 10 days and uses the close for the break. | Read section II of the paper. |
| Faber 2007 checks "close above the 10-month average" only at the month end. | Read the paper. |
| Moskowitz et al. use a 12-month look-back and a 1-month hold. Blitz & van Vliet use the volatility of the last 3 years. Barroso & Santa-Clara use the daily returns of the last 6 months. | Read the method section of each paper. |
| The IBKR instrument search returns ETFs, for example `SPY`. `backend/src/atrade/ibkr/gateway_connection.py` keeps only contracts with `secType` `STK`. | Search `SPY` on the paper account. |
| A strategy file can import `atrade.indicator` (#136, #138). The code from the rules needs it. | Run 1 import in the backtest child process, in the implementation ticket of #136. |

### 9.9.5 Left to the implementation

- The template IDs and the file of the template list.
- The rows of the dialog (section 9.7.1) for a code template. A code
  template has a rule, not an entry rule and an exit rule.
- The version source of version 1 from a code template.
- The default start point that the dialog selects when it opens.
- The tab that the strategy page opens after "Create strategy" from a rules
  start point.
- Whether `strategy_template.py` gets a new name. The name uses the term
  "strategy template", but the file is the "Blank code" start point.
