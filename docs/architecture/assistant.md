# AI strategy assistant

This document is section 25 of the architecture specification
([`docs/architecture.md`](../architecture.md)). It is in its own file to keep
the specification shorter than 1000 lines (section 18). Terms have the
meaning that [`GLOSSARY.md`](../../GLOSSARY.md) gives them.

Sources: [pi integration](https://github.com/Mano-Liaoyan/ATrade/issues/133),
[AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140),
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150).
ADRs: [0004 The AI assistant saves strategy versions directly](../adr/0004-ai-assistant-saves-strategy-versions.md),
[0005 AI assistant credentials stay in the assistant service](../adr/0005-assistant-credentials-outside-postgresql.md).
Planning map: [Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129).

The AI assistant is a language model that works with the user in the
"AI assistant" side column of each workbench page (25.12). It reads and writes strategy versions, runs and compares
backtests, and (in phase 3) reads, runs, and creates screens. It uses pi
(the pi coding agent) as its agent runtime. It can call only the ATrade
routes of an allow-list.

This section is the target. Most of it is not implemented. #178 adds the
service skeleton and the networks (25.2, 25.3.1). #179 adds the
conversations, the titles, `/ws/assistant` with `prompt`, `steer`, and
`abort`, and the first 5 browser routes (25.8, 25.10, 25.11). #184 adds the
system prompt, the prompt versions, their 2 routes, and the "Prompt" dialog
component (25.9). The tickets name facts
that nobody ran. Section 25.15 lists them.

## 25.1 Phases

| Part | Phase |
|---|---|
| `assistant` Compose service, networks, and port 8001 (25.2, 25.3) | 2 |
| Strategy and backtest tools (25.4) | 2 |
| Strategy versions saved by the AI assistant, Keep and Discard (25.5) | 2 |
| Credentials and provider login (25.7) | 2 |
| Conversations, titles, and prompt versions (25.8, 25.9) | 2 |
| `/ws/assistant` and the browser routes (25.10, 25.11) | 2 |
| Assistant side column on each workbench page (25.12) | 2 |
| Width splitter and Maximize for each `SideColumn` (25.13) | 2 |
| Screen tools, screens made by the AI assistant, condition card (25.4, 25.6, 25.12.4) | 3 |
| `run_backtest` with a universe (`universe_kind` `screen` or `list`) (25.4.2) | 3 |

Phase 1 has no part of the AI assistant. Phase 1 adds the version source
"rule builder" ([ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md)).
Phase 2 adds the second value "AI assistant" to the same column (25.5).

## 25.2 The `assistant` service

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q1, Q2, Q5),
[pi integration](https://github.com/Mano-Liaoyan/ATrade/issues/133).

- `assistant` is a new Compose service. It runs one small Node.js process
  written in TypeScript. The process uses the pi SDK.
- The npm package is `@earendil-works/pi-coding-agent`. Pin the exact
  version (`1.4.0` when the tickets were written). Do not use the deprecated
  package `@mariozechner/pi-coding-agent`.
- pi needs Node.js 22.19 or later.
- One process serves all conversations.
- pi does not run in the `web` container, because `web` holds the database
  URL and the IBKR settings.
- ATrade uses the SDK, not `pi --mode rpc`. The RPC mode has no login
  command, and the web page must do each login (25.7).
- The browser never connects to `assistant`. The browser connects only to
  `/ws/assistant` of `web` (25.10). `web` forwards the messages to
  `assistant`.

### 25.2.1 What pi can do

- All built-in pi tools are off (`noTools` with `customTools`). pi has no
  `bash`, `read`, `edit`, or `write` tool. #133 ran this: with the built-in
  tools off, a `bash` call returns "Tool bash not found".
- The process also has a `tool_call` handler. It refuses each tool that is
  not in the tool list of section 25.4. This is the second guard.
- pi does not load `AGENTS.md`, skills, or project files.
- pi loads no extension file. The only extension is the `tool_call` guard,
  an inline factory of the process. pi does not load a third-party extension, and the
  AI assistant cannot write an extension. A later ticket designs "the AI
  writes an extension and the user reviews it".
- Strategy code goes to ATrade as a tool argument. pi writes no file outside
  its volume.
- The main control is in ATrade, not in pi: the allow-list of port 8001
  (25.3).

### 25.2.2 Container

| Item | Value |
|---|---|
| Root file system | Read-only. |
| Memory limit | `mem_limit: ${ATRADE_ASSISTANT_MEMORY_LIMIT}`, default `1g`. |
| Environment | No `DATABASE_URL`, no IBKR setting, no other secret of `.env`. |
| Volume | `atrade-assistant-pi`: the credential file (25.7) and the pi conversation files (JSONL, 25.8). |
| Networks | `atrade-assistant-internal` and `atrade-assistant-egress` (25.3). |
| Published ports | None. |

- ATrade never makes an automatic backup of `atrade-assistant-pi`. README
  gives one manual backup command, for example
  `docker run --rm -v atrade-assistant-pi:/data ... tar`.
- The volume holds credentials. Keep each backup of it like `.env`.
- When the volume is lost, the conversation messages and the credentials are
  lost. The user logs in and enters the API keys again.

## 25.3 Networks and the assistant port

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q2, Q9),
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) (A8, B3).

### 25.3.1 Networks

| Network | Settings | Members | Use |
|---|---|---|---|
| `atrade-assistant-internal` | `internal: true`, fixed subnet | `web`, `assistant` | `assistant` calls port 8001 of `web`. `web` forwards `/ws/assistant` to `assistant`. |
| `atrade-assistant-egress` | Not internal | `assistant` only | `assistant` connects to the model providers. |

- `web`, `postgres`, and `ib-gateway` are not on `atrade-assistant-egress`.
- `assistant` cannot connect to `postgres` or `ib-gateway`.

### 25.3.2 Port 8001

- The `web` process starts a second uvicorn listener on port 8001. Compose
  does not publish this port to the host.
- Port 8001 has its own FastAPI app. This app mounts only the routes of the
  allow-list (25.3.3). It has no `/ws/` route and no frontend files.
- The app of port 8000 refuses with `403` each request whose peer address
  (ASGI `scope["client"]`) is in the `atrade-assistant-internal` subnet and
  is not the local address of the request (ASGI `scope["server"]`).
- A peer that is the local address is `web` itself. Rootless Podman sends
  the published port to the address of `web` in the first network by name,
  `atrade-assistant-internal`, and connects from that same address. A check
  of the local address only refused each browser request there.
- `assistant` has no `NET_RAW` capability (`cap_drop` in
  `deploy/compose.yaml`), so it cannot send packets with the address of
  `web`.
- So `assistant` cannot call a route of port 8000.
- A unit test checks the allow-list: the port 8001 app has exactly the
  routes of 25.3.3.
- Done (#181): `app/assistant_port.py` builds the port 8001 app
  (`create_assistant_port_app`) from `create_strategy_assistant_router` and
  `create_backtest_assistant_router`. The app has no OpenAPI document and no
  `/docs` page. A route that is not in the allow-list gets `404`, or `405`
  when an allowed route has the same path.
- Done (#181): each request of `assistant` to port 8001 sends the header
  `X-ATrade-Conversation-Id` with the conversation ID. The 2 routes that
  record the conversation (`POST /api/strategies/{strategy_id}/versions` and
  `POST /api/backtests`) need it. Without the header, or with a value that is
  not a positive integer, the answer is FastAPI's `422` validation body. When
  the conversation does not exist, the answer is `422` with
  `{"detail": "Conversation <id> does not exist."}`. The read routes ignore
  the header.

### 25.3.3 Allow-list

The screen paths come from #150. Decided (#205): they are the final paths
(screen section 24.7).

| Route on port 8001 | Tool | Phase | Limit on port 8001 |
|---|---|---|---|
| `GET /api/strategies` | `list_strategies` | 2 | None. |
| `GET /api/strategies/{strategy_id}` | `read_strategy` | 2 | None. |
| `GET /api/strategies/{strategy_id}/versions/{version_number}` | `read_strategy_version` | 2 | None. |
| `POST /api/strategies` | `create_strategy` | 2 | None. |
| `POST /api/strategies/{strategy_id}/versions` | `save_strategy_version` | 2 | The version records the source "AI assistant" and the conversation ID (25.5). |
| `POST /api/backtests` | `run_backtest` | 2 (single instrument), 3 (universe fields `screen` and `list`, done in #211) | The backtest records the conversation ID. |
| `GET /api/backtests` | `list_backtests` | 2 | None. |
| `GET /api/backtests/{backtest_id}` | `read_backtest`, `run_backtest` (wait) | 2 | None. |
| `GET /api/backtests/{first_id}/comparison/{second_id}` | `compare_backtests` | 2 | None. |
| `GET /api/screens` | `list_screens` | 3 | None. |
| `GET /api/screens/{screen_id}` | `read_screen` | 3 | None. |
| `POST /api/screens` | `create_screen` | 3 | The screen records the conversation ID. Its name is "<name> (AI)" (25.6). |
| `PUT /api/screens/{screen_id}` | `update_screen` | 3 | Only a screen that the same conversation created and that the user has not kept. Else `403`. |
| `POST /api/screens/{screen_id}/runs` | `run_screen` | 3 | The screen result records the conversation ID. |
| `GET /api/screen-results/{screen_result_id}` (with page parameters) | `read_screen_result` | 3 | None. |

Decided (#209): `screen/http_routes.py` has `create_screen_assistant_router`.
`app/assistant_port.py` adds it to the port 8001 app. It has the 6 screen
routes and no `DELETE`. `POST`, `PUT`, and the run route read the
conversation from the header `X-ATrade-Conversation-Id` (25.3.2), as the
strategy and backtest routes do. The `403` body is
`{"detail": "The AI assistant cannot change screen <id>. ..."}`.

These routes are not on port 8001:

- the paper order routes (`/api/paper-trading/...`)
- the forward test routes (`/api/forward-tests/...`), so the AI assistant
  cannot start or stop a forward test
- `PUT /api/backtest-limits`
- `POST /api/watchlist` and `DELETE /api/watchlist` (this includes "Add to
  watchlist")
- `DELETE /api/strategies/{strategy_id}`
- `DELETE /api/screens/{screen_id}`
- the HK instrument list changes
- the daily bar update
- the parameter sweep routes
- all `/ws/` routes

## 25.4 Tools

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q2, Q10),
[How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) (A1–A6, B3, B5),
[Rule builder prototype](https://github.com/Mano-Liaoyan/ATrade/issues/138).

The `assistant` process registers each tool as a pi custom tool. Each tool
calls the routes of 25.3.3 on port 8001. pi sends the name, the
description, and the parameters of each tool to the model, so the system
prompt does not list the tools.

### 25.4.1 Strategy and backtest tools (phase 2)

| Tool | Does | Result to the model |
|---|---|---|
| `list_strategies` | Lists the strategies. | The answer of `GET /api/strategies`. |
| `read_strategy` | Reads one strategy and its version list. | The answer of `GET /api/strategies/{strategy_id}`. |
| `read_strategy_version` | Reads the code of one strategy version. | The code. When the rule builder saved the version, also its rules JSON (#138). |
| `create_strategy` | Creates a strategy with version 1 from the template. | The new strategy. |
| `save_strategy_version` | Saves code as a new strategy version (25.5). | The new version. On `422`, the problem list `{"problems": [{"line", "message"}]}` of the checks before save (strategy section 9.3). |
| `run_backtest` | Queues a backtest of a saved strategy version and waits for its end (25.4.2). | The backtest ID and its status. When it finished, the same content as `read_backtest`. |
| `list_backtests` | Lists the backtests. | The answer of `GET /api/backtests`. Each backtest with an error message also has `error_summary`. |
| `read_backtest` | Reads one backtest. | The metrics, a summary of the equity curve, a summary of the trades, and `error_summary` of a backtest with an error message. |
| `compare_backtests` | Compares 2 backtests. | The answer of the comparison route. |

- The AI assistant does not change the rules of the rule builder. It changes
  only code. ATrade treats a code change of the AI assistant like a code
  change by hand (#138, [ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md)).
- Done (#182): `assistant/src/assistant_tools.ts` (`createAssistantTools`)
  makes the 9 tools for each run. `WebPortClient`
  (`assistant/src/web_port_client.ts`) calls `http://web:8001` with the
  header `X-ATrade-Conversation-Id` of the run. A tool gives a refusal of
  port 8001 to the model as an error with the status and the body, for
  example `Port 8001 answered 422: {"problems": [{"line": 4, "message":
  "..."}]}`.
- Decided (#182): `read_strategy_version` returns `id`, `strategy_id`,
  `version_number`, `source`, and `code`. It adds `rules` only when
  `source` is `rule_builder`.
- Decided (#182): `read_backtest` returns all fields of
  `GET /api/backtests/{backtest_id}` with 2 summaries. `equity_curve` has at
  most 50 points, evenly spread, with the first and the last point.
  `equity_curve_point_count` gives the full count. `trades` has the first 50
  trades with all their fields (`time_utc`, `side`, `quantity_shares`,
  `price_usd`, `commission_usd`). `trade_count_total` gives the full count.
- Decided: a backtest with an error message (for example a failed
  backtest with a Python traceback) also has `error_summary`, the last line
  of `error_message` that is not empty, in `read_backtest`, in the
  `run_backtest` result, and in each item of `list_backtests`.
  `error_message` keeps the full log text. So the AI assistant sees a failure
  in the list and reads the full error itself. The "Ask AI to fix" button of
  the strategy page sends "Backtest #<id> failed. Read it with read_backtest
  and fix the strategy code." (docs/architecture.md section 13).

### 25.4.2 `run_backtest`

- The tool calls `POST /api/backtests`. Then it waits at most 15 minutes for
  the end of the backtest.
- While it waits, the tool sends the queue state and the run state with the
  pi `onUpdate` call. The browser shows them as a tool step (25.10).
- After 15 minutes, the tool returns "still running" and the backtest ID.
  The AI assistant can read the result later with `read_backtest`.
- The backtests of the AI assistant and of the user use one queue and the
  same backtest limits.
- The AI assistant can backtest only an instrument and a bar period with
  saved bars. It cannot download bars. `POST /api/backtests` refuses a range
  without saved bars with `422` (backtest section 10.1).
- One user message can start at most 5 backtests. At the sixth, the tool
  returns an error. The error tells the AI assistant to ask the user first.
- Decided (#182): the tool counts the backtests (backtest section 10.13).
  The error text is "This user message already started 5 backtests. No
  backtest started. Ask the user before you start more backtests."
- Decided (#182): the wait is a parameter of the tools (`BacktestWait` in
  `assistant/src/backtest_tools.ts`: `limitMilliseconds`,
  `pollMilliseconds`, `now`). The service uses 15 minutes and 2 seconds.
  The tests use a few milliseconds.
- Phase 3: the tool takes a universe, with the same choices as the backtest
  form ([#142](https://github.com/Mano-Liaoyan/ATrade/issues/142),
  [#145](https://github.com/Mano-Liaoyan/ATrade/issues/145)):

| `universe_kind` | Parameters | Default |
|---|---|---|
| `single` | One instrument (phase 2 behavior). | — |
| `screen` | Screen ID and rebalance period (each quarter or each month). The screen runs again at each rebalance (a point-in-time rule). | Yes, for a backtest from a screen. |
| `list` | Screen result ID, and optionally a subset of its instruments. The screen result is a fixed list. | No. |

- With `list`, the tool result has a survivorship bias warning. The AI
  assistant must write this warning in its answer.
- One multi-instrument backtest counts as 1 of the 5 backtests of a user
  message. The 15 minute wait is the same.
- Done (#211): `run_backtest` has the optional parameters `universe_kind`
  (`single`, the default, `screen`, or `list`), `screen_id`,
  `rebalance_period` (`quarter` or `month`), `screen_result_id`, and
  `symbols`. `symbol`, `exchange`, and `currency` are optional, because only
  `single` uses them. The tool sends the fields to `POST /api/backtests`
  with no other change, so port 8001 makes the universe checks of backtest
  section 10.10.6 and its `422` goes to the model. A `422` does not count.
- Decided (#211): for `screen` without `rebalance_period`, the tool sends
  `rebalance_period: "quarter"`.
- Decided (#211): the warning of `list` is the constant
  `SURVIVORSHIP_BIAS_WARNING` (`assistant/src/backtest_tools.ts`). It ends
  with "Write this warning in your answer." After a final status, the tool
  result is the `read_backtest` content with the field
  `survivorship_bias_warning`. The "still running" text ends with the
  warning.
- Decided (#211): `run_backtest` does not take `rule` and the watchlist
  (backtest section 10.10.8). The AI assistant backtests a screen.
- Tests: `assistant/tests/assistant_tools.test.ts` ("run_backtest with a
  universe") and `backend/tests/app/test_assistant_port.py`
  (`test_a_multi_instrument_backtest_on_port_8001_records_the_conversation`).

### 25.4.3 Screen tools (phase 3)

| Tool | Does | Result to the model |
|---|---|---|
| `list_screens` | Lists the screens. | The screen list. |
| `read_screen` | Reads one screen. | The conditions of the screen. |
| `create_screen` | Saves a new screen (25.6). The optional `source_screen_id` names the screen that the new screen changes (#210). | The new screen. On `422`, the problem list. |
| `update_screen` | Changes a screen that the same conversation created and that the user has not kept. | The changed screen. `403` for each other screen. On `422`, the problem list. |

Decided (#210): `create_screen` with `source_screen_id` and `update_screen`
first read that screen (`GET /api/screens/{id}`). A saved screen sends the
run event `screen_saved` with that definition as `previous_definition`, for
the condition card (25.12.4). `run_screen` sends `screen_run_finished` with
the funnel counts. A failed save or run sends neither.
| `run_screen` | Runs a screen and saves its screen result. | The screen result ID and the summary of `read_screen_result`. On `422`, the problem list. |
| `read_screen_result` | Reads one screen result. | See below. |

`read_screen_result`:

- By default it returns the first 50 rows and a summary. The AI assistant
  can read more rows page by page.
- The summary has these values:
  - the total row count
  - the count of instruments left after each condition group (the funnel
    counts)
  - the count of each exclusion reason
  - the date of the daily bars
- Each row has all columns of the screen result table.
- Decided (#209): the tool has the parameters `screen_result_id` and
  `offset` (default 0). It calls
  `GET /api/screen-results/{id}?offset=<offset>&limit=50`. The result to the
  model is `{"id", "screen_id", "market", "summary", "definition", "offset",
  "rows", "next_offset"}`. `next_offset` is null on the last page. The
  result leaves out the `exclusions` list, because the summary has the count
  of each exclusion reason. `run_screen` gives the same result for offset 0.
  The code is `assistant/src/screen_tools.ts`.

Problem list of the screen tools (#150 B5):

- `create_screen`, `update_screen`, and `run_screen` return `422` with a
  problem list when a condition is not correct. Examples: the indicator does
  not exist, the base instruments do not belong to the market, or a percent
  is not in 1–100.
- The body has the same form as `CodeCheckFailedResponse`
  (`{"problems": [...]}`). Each problem names the position of the condition
  and the reason.
- The AI assistant corrects the conditions and tries again, like the save
  loop of a strategy version.

## 25.5 Strategy versions saved by the AI assistant

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q2, Q12),
[ADR 0004](../adr/0004-ai-assistant-saves-strategy-versions.md).

- The AI assistant saves each code change as a new strategy version through
  `save_strategy_version`. It does not wait for the user.
- The checks before save run as usual (strategy section 9.3). The AI
  assistant gets the `422` problem list.
- The AI assistant can backtest the new version at once, read the result,
  and change the code again.

### 25.5.1 Columns

| Table | New column | Meaning |
|---|---|---|
| `strategy_version` | `source` | `user`, `ai_assistant` (AI assistant), or `rule_builder` (rule builder, [ADR 0006](../adr/0006-rule-builder-generates-code-one-way.md)). |
| `strategy_version` | `conversation_id` | Nullable. Foreign key to `assistant_conversation` with `ON DELETE SET NULL`. Set when the AI assistant saved the version. |
| `strategy_version_discard` | `strategy_version_id`, `discarded_at_utc` | The discarded mark: one row for each discarded version. Added when the user discards the version. |
| `backtest` | `conversation_id` | Nullable. Foreign key to `assistant_conversation` with `ON DELETE SET NULL`. Set when the AI assistant started the backtest. |

- A discarded strategy version is never deleted. Its backtests stay.
- The trigger `strategy_version_append_only` refuses each `UPDATE`
  (strategy section 9.1.1). The discarded mark cannot be an `UPDATE` of the
  version row, so it is a row of `strategy_version_discard` (#180). The
  trigger lets through only the `ON DELETE SET NULL` of `conversation_id`
  (strategy section 9.1.1).

### 25.5.2 Diff card

- The conversation shows each code change as a diff card. The diff compares
  the new version with the version before it.
- The card has the buttons Keep and Discard.
- A click on the card opens `CodeDiff` in the editor panel.
- Keep: the editor opens the new version.
- Discard: the editor stays on the version that was open before. The new
  version gets the discarded mark.
- When the user clicks neither button, the version stays like a kept
  version. Only Discard changes a version.

### 25.5.3 Version list

- The version `Select` of the strategy page hides discarded strategy
  versions by default.
- A toggle "Show discarded versions" next to the `Select` shows them. Each
  shows the tag "Discarded" after its version number.
- Decided (#180): the toggle is in the toolbar line after the `Select`,
  because the toolbar has one line. It shows only when the strategy has a
  discarded version. When the open version is discarded, the `Select` also
  lists it with the toggle off, so that the `Select` names the open
  version. Without a version address, the strategy page opens the latest
  version that is not discarded.
- The backtest list shows the backtests of discarded strategy versions as
  usual.

## 25.6 Screens made by the AI assistant (phase 3)

Source: [How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) (A1–A3, A7, B2–B4).

- The AI assistant can read, run, and create screens. It never deletes a
  screen.
- It never overwrites a screen that the user saved. To change a screen, it
  saves a new screen.
- Name of the new screen: the old name plus " (AI)". When the name is in
  use, a number follows, for example "Momentum leaders (AI 2)". The user can
  rename it.
- The AI assistant can change a screen only when the same conversation
  created it and the user has not clicked Keep (`update_screen`). Then the
  old condition card links to the latest state.
- Screens stay without versions ([#145](https://github.com/Mano-Liaoyan/ATrade/issues/145) Q6).
- Each backtest keeps a copy of the screen conditions that it used. So a
  later change or delete of a screen does not change an old backtest.
- The conversation shows each new or changed screen as a condition card
  (25.12.4).
  - Keep: the screen stays in the "Screens" side column. After Keep, the AI
    assistant cannot change it.
  - Discard: ATrade deletes this screen.
  - When the user clicks neither button, the screen stays. The user can
    delete it later by hand.
- The new screen shows in the "Screens" side column before the user keeps
  it.
- Deleting a conversation does not delete a screen.

Screen results:

- Each run of the AI assistant saves one screen result. The screen result
  records the conversation ID.
- When the user deletes the conversation, the screen result stays and its
  conversation ID becomes null.
- The recent runs in the side column include the runs of the AI assistant.

Place:

- The user discusses screens with the AI assistant in the assistant side
  column. Each workbench page has it, also the screen page `/screens/<id>`
  (25.12).
- The condition card has "Open screen". It opens `/screens/<id>`.

## 25.7 Credentials and provider login

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (user decisions of 2026-10-28, Q3, Q4),
[ADR 0005](../adr/0005-assistant-credentials-outside-postgresql.md).

### 25.7.1 Providers and methods

- The web page offers each access method that pi supports: each
  subscription login and each API key.
- The page reads the providers from pi (`ModelRuntime.getProviders()`). It
  does not have a fixed list.
- pi 1.4.0 has subscription logins for `anthropic`, `openai` (ChatGPT
  subscription), `openai-codex`, `github-copilot`, `xai`, `kimi-coding`, and
  `meta`. `openrouter` and `radius` have OAuth, but not a subscription.
- The user takes the risk of each provider's terms of service. ATrade does
  not take away a provider because of its terms.
- Google: API key only. pi 1.4.0 has no Google Gemini or Antigravity login.
- The user selects, for each conversation: the provider, the model, a
  subscription or an API key, which credential, and the thinking level.
- The model list of a provider comes from pi
  (`ModelRuntime.getAvailable(provider)` gives only the models with a
  credential).
- Implemented (#183): `GET /api/assistant/providers` lists each pi provider
  with at least one login method (`login_methods`: `oauth` for a
  subscription login, `api_key`). The `models` of a provider are the union
  of `getAvailable(provider)` over its stored credentials. A provider
  without a credential has no models. pi has no models.json in ATrade
  (`modelsPath: null`).
- Decided (side column feedback): each model has `thinking_levels`, the
  thinking levels of pi that the model supports, in the order of pi (`off`,
  `minimal`, `low`, `medium`, `high`, `xhigh`, `max`). The rule is the rule
  of pi-ai `getSupportedThinkingLevels`: a model without `reasoning` has only
  `off`; a level that `thinkingLevelMap` sets to `null` is not supported;
  `xhigh` and `max` only when `thinkingLevelMap` names them.
  pi-coding-agent 1.4.0 does not export the function, so
  `assistant/src/model_selection.ts` has a copy of the rule.

### 25.7.2 Storage

- The `assistant` service keeps the credentials in one file in the volume
  `atrade-assistant-pi`. The file mode is `0600`.
- Credentials never go to PostgreSQL, to `.env`, or to git. This is a
  deliberate exception to section 15 ([ADR 0005](../adr/0005-assistant-credentials-outside-postgresql.md)).
- pi's own `auth.json` keeps only 1 credential for each provider. So ATrade
  keeps its own credential store with many credentials for one provider.
- For each conversation, `assistant` creates a `ModelRuntime` with a
  `CredentialStore` that holds only the selected credential.
- After an OAuth refresh, `assistant` writes the new token back to the same
  file.
- `web` does not keep a credential. The secret value goes from the browser
  through `/ws/assistant` to `assistant`.
- Implemented (#183): the file is `/data/credentials.json`
  (`assistant/src/credential_file.ts`):
  `{"credentials": [{id, name, provider, credential, state, state_message}]}`.
  `credential` is the pi credential (`{type: "api_key", key}` or
  `{type: "oauth", access, refresh, expires, ...}`). The ID is a UUID.
  Each write makes a new file with mode `0600` and renames it.
- `SelectedCredentialStore` is the `CredentialStore` of one run: `read()`
  gives the selected credential only for its provider, and `list()` has 1
  entry. pi refreshes an OAuth token inside `modify()`, and the store writes
  the new token to the same entry. The writes are serialized.
- The state of a credential: `ready`, or `failed` when the last OAuth
  refresh failed (`state_message` has the reason). The user deletes a
  failed credential and logs in again. A good refresh sets `ready` again.
- Delete: `DELETE /api/assistant/credentials/{credential_id}` removes the
  entry from the file (`404` when it does not exist). A credential has no
  rename: delete it and add it again with the new name. The conversations
  keep the old credential name in their messages.

### 25.7.3 Login

- `assistant` calls `ModelRuntime.login(providerId, "oauth" | "api_key",
  interaction)`. The `interaction` object connects pi to the web page.
- pi sends `auth_url`, `device_code`, `progress`, and `info` events through
  `notify()`. `web` sends each as a `login_step` message (25.10).
- pi asks for `text`, `secret`, `select`, and `manual_code` input through
  `prompt()`. The page shows the field. The browser answers with
  `login_answer`.
- A subscription login shows the authorization link, the device code, and a
  field to paste a code, as pi asks for them.
- A new API key uses a password field.
- Implemented (#183): `assistant/src/logins.ts`. A login runs in a
  `ModelRuntime` with an empty credential store in memory. pi returns the
  new credential, and `assistant` adds it to the file with the name that
  the user entered. pi asks for an API key with a `secret` prompt
  ("Enter API key"), so the API key also comes as a `login_answer`.
- Decided (#186): `login()` also gets `getDeviceId`, as in pi's own CLI.
  "Sign in with ChatGPT" refuses a login without a device ID (a UUID). The
  ID is in `/data/device-id` (mode `0600`) and stays the same for each
  login.
- A browser callback login (for example OpenAI with
  `http://127.0.0.1:1455/auth/callback`) cannot reach the callback server
  of pi in `assistant`: the browser shows a connection error. The user
  pastes the full address of that page into the `manual_code` field.
- The Credentials dialog opens its own `/ws/assistant` socket without
  `conversation_id`. Closing the dialog closes the socket and stops the
  login. A cancelled login adds no credential.

### 25.7.4 Credentials dialog

- The "Credentials" icon button of the assistant side column opens a
  `Dialog`.
- The dialog lists the credentials in a `DataTable`: name, provider, kind
  (subscription or API key), and state.
- An API key shows only its last 4 characters.
- A credential has a name, for example "Anthropic API key · personal".
- The dialog has the steps to add a subscription login and to add an API
  key (25.7.3).
- Implemented (#183): `frontend/src/lib/assistant/CredentialsDialog.svelte`
  (logic in `credentials.ts`). The table columns are Name, Provider, and
  Kind, and a row menu with "Delete credential". Kind is "Subscription" or
  "API key"; an API key adds its last 4 characters (`••••7a9f`). A status
  icon before the name gives the state in its tooltip: "Ready" (success) or
  "Log in again: <reason>" (error). While the login waits for the provider,
  an in-progress icon shows with the tooltip "Waiting for the provider". Below the table: a content switcher
  (Subscription, API key), the Provider select (only the providers with the
  method), the Name field, and "Log in" or "Add API key". While a login
  runs, the dialog shows the steps of pi: the link "Open the authorization
  page", the device code, the progress text, and the field of the current
  prompt (a password field for `secret`) with "Save API key", "Send code",
  or "Send answer". #185 puts the "Credentials" icon button in the side
  column and has the Playwright test of the flow.

## 25.8 Conversations

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q4, Q12, Q14).

### 25.8.1 Storage

- The new capability `assistant` has a backend module
  (`backend/src/atrade/assistant/`) and a frontend directory
  (`frontend/src/lib/assistant/`).
- PostgreSQL holds the conversation metadata in `assistant_conversation`.
- pi keeps the messages of each conversation in one JSONL file in the
  volume `atrade-assistant-pi`. The file has all messages, tool arguments,
  and tool results. PostgreSQL does not hold the messages.

| Table | Columns |
|---|---|
| `assistant_conversation` | `id`, `title`, `title_state`, `strategy_id`, `created_at_utc`, `prompt_version_id` (foreign key to `assistant_prompt_version`, added by #184), `last_provider`, `last_model`, `last_credential_name` |
| `assistant_prompt_version` | See 25.9. |

Implemented (#179, #184):

| Column | Type | Meaning |
|---|---|---|
| `id` | `bigint` identity | The conversation ID. |
| `strategy_id` | `bigint`, nullable, foreign key to `strategy` with `ON DELETE CASCADE` | The strategy of the conversation. Null for a conversation that started on a page without an open strategy (25.12). |
| `title` | `text`, 1 to 200 characters | The title. |
| `title_state` | `text` | `new`, `generating`, `generated`, `not_generated` (the generation failed), or `renamed`. |
| `created_at_utc` | `timestamptz` | The creation time. |
| `last_provider`, `last_model`, `last_credential_name` | `text`, nullable | The provider, model, and credential name of the last AI assistant message. Null before the first answer. |
| `prompt_version_id` | `bigint`, foreign key to `assistant_prompt_version` | The prompt version of the conversation (#184). All runs of the conversation use it. |
| `fixed_prompt` | `text` | The fixed part of the system prompt, made when the conversation starts (#184, 25.9). |

- Implemented (#184): the routes of 25.11 answer each conversation also with
  `prompt_version_id` and `prompt_version_number` (for "Prompt v3").
- The JSONL file of a conversation is `/data/conversations/<id>.jsonl` in
  the volume `atrade-assistant-pi`. Before each run, `assistant` adds a pi
  custom entry `atrade_credential` with the credential name. So each AI
  assistant message of the file has its model (from pi) and its credential
  name.
- `assistant_prompt_version`: see 25.9.1.

- A conversation belongs to at most one strategy.
- Each workbench page lists the same conversations: all conversations, the
  newest first (25.12). A conversation is not bound to a page.
- These records keep the conversation ID:
  - the strategy versions that the AI assistant saved
  - the backtests that it started
  - (phase 3) the screens and the screen results that it made

### 25.8.2 Model change in a conversation

- The user can change the provider, the model, or the credential in the
  middle of a conversation.
- Each AI assistant message shows its model, its thinking level, and its
  credential name.
- The browser sends the provider, the model, the credential, and the
  thinking level with each `prompt`. `assistant` opens the JSONL file again
  for each run with this model and thinking level, so a change needs no
  other message (#179).
- Decided (side column feedback): `assistant` gives the thinking level to
  `createAgentSession` (`thinkingLevel`). pi lowers a level that the model
  does not support (pi-ai `clampThinkingLevel`): to the next higher level of
  the model, else to its highest level. A model without reasoning runs with
  `off`. `message_end` has the level that pi uses. The custom entry
  `atrade_credential` of each run has `credential_name` and
  `thinking_level`, so the saved messages show the level too. A message of
  a run before this change has `thinking_level` null.
- So the answers of 2 models in one conversation are easy to compare.

### 25.8.3 Title

- ATrade generates the title after the first AI assistant answer ends
  (`run_state` becomes `settled`).
- It uses the current model and credential of the conversation.
- This model call has no tools. It is not saved in the JSONL file of the
  conversation.
- Input: the first user message and the first 2000 characters of the first
  AI assistant answer.
- The title has the language of the user message. A Chinese title has at
  most 20 characters. An English title has at most 8 words.
- Before the title exists, the title is "New conversation" and the creation
  time in UTC, for example "New conversation 2026-01-02 03:04 UTC".
- The generation runs only after a run with an AI assistant answer
  (a `message_end`). A run that ends with an error does not use up the
  generation.
- `assistant` takes the first line of the model answer without quotes. When
  it has a Chinese character, it keeps the first 20 characters. Else it
  keeps the first 8 words.
- When the generation fails, the title stays "New conversation" and the
  creation time. `web` sends an `error` message "The title was not
  generated. <reason>" on `/ws/assistant`. The Output tab of the "Problems
  and output" panel records it. ATrade does not try again (`title_state`
  `not_generated`).
- The user can rename a conversation. After a rename, ATrade never changes
  the title again.
- The model call costs a small amount on the credential that the user
  selected.

### 25.8.4 Delete

- Delete opens a danger `Dialog` first.
- A delete deletes the `assistant_conversation` row and the JSONL file.
  `web` asks `assistant` to stop the run and delete the file first. When
  `assistant` is not reachable, the route answers `503` and the row stays,
  so the user can delete again.
- A delete of the strategy deletes its conversation rows
  (`ON DELETE CASCADE`). Their JSONL files stay in the volume (#179).
- The strategy versions, backtests, screens, and screen results stay. Their
  conversation ID becomes null (`ON DELETE SET NULL`).

## 25.9 System prompt and prompt versions

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q11, Q13).

The system prompt has 2 parts. The code adds the fixed part after the
editable part.

| Part | Content | The user can edit it |
|---|---|---|
| Editable part | The role of the AI assistant, how to write a strategy (the file format and the template of strategy section 9.2), and the answer rules. One answer rule: an answer about a backtest result names the metrics. It also names the out-of-sample result. | Yes. Each save makes a prompt version. |
| Fixed part | The forbidden actions: no paper order, no forward test start, no promise of returns. The context of the conversation start: the ID and name of the open strategy, the open version number, and the IDs of the last 3 backtests. | No. The page shows it read-only. |

- The default editable part is in English and is in the code.
- The forbidden actions in the prompt only tell the model. They are not a
  security control. The allow-list of port 8001 is the control (25.3).

Implemented (#184):

- `web` makes the system prompt, not `assistant`. The default editable part
  is `make_default_text()` in `backend/src/atrade/assistant/system_prompt.py`.
  It has the role, the rules of strategy section 9.2 with the "Blank code"
  start point (`STRATEGY_TEMPLATE`, which `app/` gives to `assistant`), and
  the answer rules.
- The system prompt is the editable part, an empty line, and the fixed part.
  The fixed part is the forbidden actions and these lines:

  ```text
  The context at the start of this conversation:
  - The open strategy: ID <strategy ID>, name <strategy name>.
  - The open version: <version number>.
  - The last 3 backtests of the strategy: <backtest IDs>.
  ```

  A missing version or no backtest gives `none`. The backtest IDs are the
  newest first, from all versions of the strategy. A conversation that
  starts on a page without an open strategy gives `none` for each of the 3
  values. The page itself is not in the context.
- The browser sends the open version number in the body of
  `POST /api/assistant/conversations`: `{"strategy_id", "version_number"}`.
  Both are optional. A page without an open strategy sends `{}`. A
  `version_number` without `strategy_id` gets `422`. Only the strategy page
  sends a strategy. `web` reads the strategy name and the last 3
  backtests when the conversation starts, and saves the fixed part in
  `assistant_conversation.fixed_prompt`. So all runs of one conversation get
  the same system prompt, also after a rename of the strategy or a new
  backtest.
- `assistant` imports only `foundation` (section 6.2). `app/web.py` gives
  `create_assistant_router()` a start context reader that calls
  `strategy.read_strategy_outline()` and `backtest.read_last_backtest_ids()`.
- `web` sends the system prompt with each run (`system_prompt` in
  `POST /conversations/{id}/runs`, 25.14). pi adds one section after it:
  `<cwd>` with the pi directory. pi adds nothing else, because the prompt is
  a custom prompt.

### 25.9.1 `assistant_prompt_version`

| Table | Columns |
|---|---|
| `assistant_prompt_version` | `id`, `version_number`, `text` (the editable part), `created_at_utc` |

- Each save makes a new prompt version. A prompt version does not change
  after it is saved.
- A new prompt version applies only to new conversations. A new
  conversation uses the latest prompt version.
- Each conversation records its prompt version. The tooltip and the
  accessible name of the "Prompt" icon button show it, for example
  "Prompt v3".
- So all answers in one conversation use the same prompt and are easy to
  compare. To use a new prompt, the user starts a new conversation.

Implemented (#184):

| Column | Type | Meaning |
|---|---|---|
| `id` | `bigint` identity | The prompt version ID. |
| `version_number` | `integer`, unique, 1 or more | 1, 2, 3, … The next save takes the highest number plus 1. |
| `text` | `text`, 1 to 50000 characters | The editable part. |
| `created_at_utc` | `timestamptz` | The save time. |

- The trigger `assistant_prompt_version_append_only` refuses each `UPDATE`,
  like `strategy_version_append_only`.
- A save locks the table (`EXCLUSIVE` mode) in its transaction, so 2 saves
  cannot take the same number.
- The default text is saved as version 1 when no version exists and a
  conversation starts or the dialog lists the versions. So the list is never
  empty. A later change of the default text in the code does not change
  version 1. "Restore default" puts the default of the code in the text area.
- The conversations of #179 got version 1 with their old system prompt "You
  are the ATrade strategy assistant." in the migration.

### 25.9.2 Prompt dialog

- The "Prompt" icon button of the assistant side column opens a `Dialog`.
- The dialog has: a version `Select`, a text area, the fixed part
  (read-only), the "Restore default" button, and the "Save as new version"
  button.
- "Restore default" puts the default text in the text area. It saves
  nothing. The user must click "Save as new version".
- Implemented (#184): `PromptDialog` in `frontend/src/lib/assistant/`, with
  its logic in `prompt_dialog.ts`. The dialog opens with the latest version.
  A version of the `Select` puts its text in the text area. The text area
  and the fixed part each scroll in a `ScrollRegion`. The 2 buttons are in
  the dialog content, so the dialog has no other button than Close. A save
  of an empty text shows the error "Enter the prompt text.". #185 puts the
  dialog in the assistant side column.

## 25.10 `/ws/assistant`

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q8).

- `/ws/assistant` is the WebSocket path of the `assistant` capability on
  port 8000.
- `web` changes the pi events into a small set of ATrade messages. The
  frontend depends only on these message types. When pi changes, only
  `assistant` and the change code in `web` change.
- The `assistant` capability exports its message models for the OpenAPI
  document, like the other capabilities (section 13), for example
  `ASSISTANT_SOCKET_MESSAGE_MODELS`. The list has `HeartbeatMessage`.

Server to browser:

| `type` | Content |
|---|---|
| `message_delta` | A part of the streamed text of an AI assistant message. |
| `message_end` | The end of one AI assistant message, with its model and credential name. |
| `tool_step` | The start or the end of one tool call, with its status. For `run_backtest`, the queue state and the run state. |
| `strategy_version_saved` | The strategy version ID, for the diff card. |
| `backtest_finished` | The backtest ID, for the metric card. |
| `run_state` | `running` or `settled`. |
| `error` | An error of the conversation. |
| `login_step` | One login step: `auth_url`, `device_code`, `prompt`, or `progress`. |

Browser to server:

| `type` | Content |
|---|---|
| `prompt` | A new user message. |
| `steer` | A user message while the AI assistant runs. |
| `abort` | Stop the current run (the "Stop" button). |
| `login_answer` | The answer to a `login_step` of kind `prompt`. |
| `login_start` | Start a login (#183). |

- Phase 3 adds a message for the condition card (a screen ID), like
  `strategy_version_saved`. See 25.14. Decided (#210):

  | `type` | Direction | Fields |
  |---|---|---|
  | `screen_saved` | Server to browser | `screen_id`, `name`, `market`, `definition`, `previous_definition` |
  | `screen_run_finished` | Server to browser | `screen_id`, `screen_result_id`, `start_count`, `after_filters_count`, `after_indicator_conditions_count`, `result_count` |

  `screen_saved` comes for each screen that `create_screen` or
  `update_screen` saved. `previous_definition` is the definition before
  `update_screen`, or the definition of the source screen of
  `create_screen`. It is null for a new screen without a source screen.
  `screen_run_finished` comes for each screen result of `run_screen`. The
  `assistant` service sends both events with the same fields as JSON lines
  of `POST /conversations/{id}/runs`. The message models are
  `ScreenSavedMessage` and `ScreenRunFinishedMessage`.

Fields (#179). Each message is a JSON object with `type`.

| `type` | Direction | Fields |
|---|---|---|
| `prompt` | Browser to server | `text`, `provider`, `model`, `credential_id`, `thinking_level` |
| `steer` | Browser to server | `text` |
| `abort` | Browser to server | — |
| `message_delta` | Server to browser | `text` |
| `message_end` | Server to browser | `text`, `provider`, `model`, `credential_name`, `thinking_level` |
| `run_state` | Server to browser | `state`: `running` or `settled` |
| `error` | Server to browser | `message` |
| `heartbeat` | Server to browser | — (every 10 seconds) |

- The browser opens one socket for one conversation:
  `/ws/assistant?conversation_id=<id>`. For a conversation that does not
  exist, the server sends `error` and closes the socket with code 1008.
- `web` sends `run_state` `running` before the run and `settled` after the
  run, also after an `abort` or an error.
- A `prompt` during a run, a `steer` without a run, and a message that is
  not valid each get an `error` message. A `prompt` during a run does not
  start a second run.
- When the browser leaves during a run, `web` stops the run (`abort`).
- Decided (#182): the fields of the tool messages:

  | `type` | Direction | Fields |
  |---|---|---|
  | `tool_step` | Server to browser | `tool_call_id`, `tool_name`, `status` (`running`, `succeeded`, or `failed`), `backtest_id`, `backtest_status` |
  | `strategy_version_saved` | Server to browser | `strategy_id`, `strategy_version_id`, `version_number` |
  | `backtest_finished` | Server to browser | `backtest_id` |

  One `tool_call_id` is one tool step. `status` is `running` at the start
  and at each `onUpdate`, then `succeeded` or `failed`. `backtest_id` and
  `backtest_status` are set only for `run_backtest` after its start:
  `backtest_status` is the queue state (`queued`) or the run state
  (`running`, then `finished`, `failed`, or `timed_out`). They are null
  for the other tools. `strategy_version_saved` comes only for a save that
  made a new version (`201`). `backtest_finished` comes when
  `run_backtest` saw a final status in its wait. The `assistant` service
  sends the same 3 events, with the same fields, as JSON lines of
  `POST /conversations/{id}/runs` (25.14).
Login fields (#183):

| `type` | Direction | Fields |
|---|---|---|
| `login_start` | Browser to server | `provider`, `method` (`oauth` or `api_key`), `name` (the credential name) |
| `login_answer` | Browser to server | `prompt_id`, `value` (for `select`, the option ID) |
| `login_step` | Server to browser | `step` (`auth_url`, `device_code`, `progress`, `info`, `prompt`), `message`, `url`, `user_code`, `prompt_id`, `prompt_type` (`text`, `secret`, `select`, `manual_code`), `options` (`[{id, label}]`); a field that the step does not use is null |
| `login_end` | Server to browser | `credential` (the fields of `GET /api/assistant/credentials`) |

- A socket without `conversation_id` is for the login only. A `prompt`,
  `steer`, or `abort` on it gets an `error`.
- One login runs at a time on one socket. A failed login sends `error`.
- No message to the browser holds a secret. The error of a message that is
  not valid does not repeat its input, because a `login_answer` can hold an
  API key. `web` does not log the answers.
- `ASSISTANT_SOCKET_MESSAGE_MODELS` (`atrade.assistant`) lists the messages
  of both directions. Message model names: `PromptMessage`, `SteerMessage`,
  `AbortMessage`, `MessageDeltaMessage`, `MessageEndMessage`,
  `RunStateMessage`, `ToolStepMessage`, `StrategyVersionSavedMessage`,
  `BacktestFinishedMessage`, `ScreenSavedMessage`,
  `ScreenRunFinishedMessage`, `AssistantErrorMessage`, `HeartbeatMessage`,
  `LoginStartMessage`, `LoginAnswerMessage`, `LoginStepMessage`,
  `LoginEndMessage`.

## 25.11 Browser routes on port 8000

The tickets decide the operations. They do not decide the paths. The paths
below are choices of this document. The implementation can change them.

| Operation | Proposed route | Phase |
|---|---|---|
| List the conversations (all, or of a strategy) | `GET /api/assistant/conversations[?strategy_id=...]` | 2 |
| Create a conversation | `POST /api/assistant/conversations` | 2 |
| Read the messages of a conversation | `GET /api/assistant/conversations/{conversation_id}` | 2 |
| Rename a conversation | `PATCH /api/assistant/conversations/{conversation_id}` | 2 |
| Delete a conversation | `DELETE /api/assistant/conversations/{conversation_id}` | 2 |
| List providers and models | `GET /api/assistant/providers` | 2 |
| List credentials | `GET /api/assistant/credentials` | 2 |
| Delete a credential | `DELETE /api/assistant/credentials/{credential_id}` | 2 |
| List prompt versions | `GET /api/assistant/prompt-versions` | 2 |
| Save a prompt version | `POST /api/assistant/prompt-versions` | 2 |
| Discard a strategy version | `POST /api/strategies/{strategy_id}/versions/{version_number}/discard` (done, #180, strategy section 9.6) | 2 |
| Keep a screen of the AI assistant | `POST /api/screens/{screen_id}/keep` | 3 |
| Discard a screen of the AI assistant | `DELETE /api/screens/{screen_id}` (the user route) | 3 |

- #179 implements the first 5 rows:
  - `GET ?strategy_id=` answers `{"conversations": [...]}`, the newest
    first. Each conversation has the columns of 25.8.1. Without
    `strategy_id`, the answer has all conversations. The side column uses
    this form (25.12).
  - `POST` takes `{"strategy_id"}` and answers `201` with the conversation.
    A strategy that does not exist gets `404`. `strategy_id` is optional:
    without it, the conversation has no strategy (`strategy_id` null).
  - `GET {conversation_id}` answers the conversation and `messages`: the
    user messages and the AI assistant messages with text, each with
    `role`, `text`, `provider`, `model`, `credential_name`, and
    `thinking_level` (the last 4 only for an AI assistant message;
    `thinking_level` is null for a run before the level was recorded).
  - `PATCH {conversation_id}` takes `{"title"}` (1 to 200 characters) and
    sets `title_state` `renamed`.
  - `DELETE {conversation_id}` answers `204`.
  - A conversation that does not exist gets `404`. `GET {conversation_id}`
    and `DELETE` answer `503` when `assistant` is not reachable.
- #184 implements the prompt version rows:
  - `GET` answers `{"prompt_versions": [...], "default_text", "fixed_part"}`.
    The versions are the newest first. Each has `id`, `version_number`,
    `text`, and `created_at_utc`. `fixed_part` has the names of the values
    (`<strategy ID>`, …) in the place of the values.
  - `POST` takes `{"text"}` (1 to 50000 characters after the trim) and
    answers `201` with the new version. These routes refuse nothing else, so
    they declare no `ErrorResponse`. A text that is not valid gets FastAPI's
    `422`.
  - `POST /api/assistant/conversations` also takes the optional
    `version_number` (25.9).
- #183 implements the providers and credentials rows:
  - `GET /api/assistant/providers` answers `{"providers": [{id, name,
    login_methods, models: [{id, name, thinking_levels}]}]}` (25.7.1).
  - `GET /api/assistant/credentials` answers `{"credentials": [{id, name,
    provider, type, key_last4, state, state_message}]}`. `key_last4` is the
    last 4 characters of an API key, null for a subscription login.
  - `DELETE /api/assistant/credentials/{credential_id}` answers `204`, or
    `404` for a credential that does not exist.
  - All 3 answer `503` when `assistant` is not reachable.
- #184 implements the prompt version rows:
  - `GET` answers `{"prompt_versions": [...], "default_text", "fixed_part"}`.
    The versions are the newest first. Each has `id`, `version_number`,
    `text`, and `created_at_utc`. `fixed_part` has the names of the values
    (`<strategy ID>`, …) in the place of the values.
  - `POST` takes `{"text"}` (1 to 50000 characters after the trim) and
    answers `201` with the new version. These routes refuse nothing else, so
    they declare no `ErrorResponse`. A text that is not valid gets FastAPI's
    `422`.
  - `POST /api/assistant/conversations` also takes the optional
    `version_number` (25.9).
- None of these routes is on port 8001.
- The login itself runs on `/ws/assistant` (25.7.3), because it asks
  questions and waits for answers.
- The routes declare their error bodies with `responses=`
  (`ErrorResponse`), like the other routes (section 13).

## 25.12 Assistant side column on each workbench page

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q6, Q7),
[UI reference: screens, rule builder, and AI assistant](https://github.com/Mano-Liaoyan/ATrade/issues/135).

Each workbench page has a right `SideColumn` with the name "AI assistant":
Screens, Strategies, Backtests, Parameter sweeps, and Forward tests. The
default width is 28rem. All pages show the same column with the same
conversations. A page change keeps the open conversation, its socket, its
log, the message input, and Minimize.

### 25.12.1 Layout

| Area | Content |
|---|---|
| Top | Conversation `Select`, "New conversation" button, "Credentials" icon button, "Prompt" icon button. The tooltip of "Prompt" names the prompt version of the open conversation, for example "Prompt v3". |
| Middle | The conversation messages (`role="log"`) in a `ScrollRegion`. Tool steps, diff cards, metric cards, and (phase 3) condition cards. |
| Bottom | The composer: one box with the message input, and under the input the inline model `Select` (the full model name), the inline thinking `Select`, and the "Send" icon button. While the AI assistant runs, "Send" becomes "Stop". Under the box: the inline provider and credential `Select`s. |

- A tool step is one line: a status icon (`StatusIndicator`, the state in
  its tooltip, for example "Running") before the title, for example
  "Backtest #42". 2 or more consecutive tool steps are one group
  (25.12.5).
- A diff card shows a code change (25.5.2).
- A metric card shows the `KeyMetricRow` of a finished backtest. It links to
  the backtest.
- Each AI assistant message shows its model, its thinking level, and its
  credential name (25.8.2).
- Copy uses the terms of `GLOSSARY.md`: "conversation", not "chat",
  "thread", or "session".
- The Frontend Design Rules of `AGENTS.md` apply. A heading is a name only.
  The side column has no helper text under its name. A disabled control
  says why it is disabled.

Implemented (#185):

- `AssistantColumn` (`frontend/src/routes/assistant/`) puts the side column
  together. It is a route component, not a part of `src/lib/assistant/`,
  because its metric card imports `#lib/backtest` (a capability imports only
  `foundation`). Each workbench page mounts it as the last child of its
  `Workbench`. The header line of the column has the icon buttons
  "Credentials", "Prompt", "Maximize AI assistant", and "Minimize AI
  assistant". The rail has the `ai-agent` icon.
- Top line: the conversation `Select` (the titles, the newest first), the
  icon buttons "New conversation", "Rename conversation" (a `Dialog` with
  the title), and "Delete conversation" (a danger `Dialog`). The "Prompt"
  icon button has the label "Prompt v<n>" for the open conversation.
- `AssistantLog` shows the log with `ChatLog`. A message of the AI assistant
  ends with a line "<model> · <thinking level> · <credential name>". The
  level `off` (or no recorded level) is not in the line, for example
  "gpt-a · Work key". The log of
  `frontend/src/lib/assistant/conversation_log.ts` keeps one line for each
  `tool_call_id`. The line title is "Backtest #<id>" for `run_backtest` with
  a backtest, else the tool name, for example "Save strategy version". The
  status icon before it has the state as its name and tooltip, for example
  "Succeeded".
- A diff card has the link button "v<n-1> → v<n>" and the buttons "Keep" and
  "Discard". After a click, the buttons go, and a status icon "Kept" or
  "Discarded" (`StatusIndicator`, no word) stands before the link button.
- A metric card has the link "Backtest #<id>" to the backtest page and the
  `KeyMetricRow` of the backtest.
- Bottom: the Selects "Provider" (only the providers with a credential),
  "Model", and "Credential". A conversation starts with its last
  model and credential, else with the first credential and the first model
  of its provider. Enter sends; Shift Enter adds a line.
- Decided (side column feedback, then the conversation design of 25.12.5):
  the composer replaces the 2 lines of Selects. The open list of each
  `Select` is at least as wide as its field and as wide as its longest
  label, not wider than the viewport. A field that cuts its label shows the
  full label in a native `title` tooltip.
- Decided (side column feedback): "Thinking" lists only the
  `thinking_levels` of the selected model ("Off", "Minimal", "Low",
  "Medium", "High", "Extra high", "Max"). The browser keeps the last chosen
  level under `atrade.assistant-column.thinking-level` for all
  conversations. Default: `medium`, the default of pi. For a model without
  the chosen level, the field shows the level that pi uses (25.8.2). For a
  model without reasoning, the field shows "No thinking", is disabled, and
  says "The model has no thinking levels." (tooltip and accessible
  description).
- The browser opens one `/ws/assistant` socket for the open conversation
  (`conversation_socket.ts`). The socket does not connect again after a
  close. Each `error` message goes to the Output tab of the "Problems and
  output" panel with the UTC time. After `run_state` `settled`, the page
  reads the conversation list again after 1 second for the generated title.

Decided (each workbench page has the column):

- The state of the column is one module object
  (`routes/assistant/assistant_session.svelte.ts`): the conversation list,
  the open conversation and its `/ws/assistant` socket, the log, the model
  selection, the message input, and the Keep and Discard choices. Each page
  mounts its own `AssistantColumn`, so the page layout does not change. A
  page change does not close the socket, so it does not stop a run (25.10).
- All pages use the storage key `atrade.assistant-column`, so the width and
  Minimize stay across pages. The browser keeps the open conversation under
  `atrade.assistant-column.conversation`, so a reload opens it again.
  Without an open or a stored conversation, the column opens no
  conversation: the newest one can be the conversation of another browser
  tab, and a socket that closes stops its run (25.10). After a delete, the
  column opens the newest conversation.
- Each page reads the conversation list again when it opens. When the
  socket of the open conversation is closed, the page opens a new socket.
- "Send" stays disabled ("connecting") until the socket is open and the
  saved messages are read, so a sent message is not lost when the saved
  messages replace the log.
- "New conversation" on the strategy page sends the open strategy and
  version (25.9). On the other pages, and on `/strategies` without a
  strategy, it sends none.
- The strategy page sends the errors of the conversation to the Output tab
  of the "Problems and output" panel. The other pages have no Output tab:
  the column shows the last error in a low-contrast error
  `InlineNotification` above the log. Its close button removes it.
- A diff card of the open strategy on the strategy page works as before. A
  diff card on another page, or of another strategy: a click opens
  `/strategies/<id>` and then the diff tab; Keep opens
  `/strategies/<id>/versions/<n>`; Discard adds the discarded mark.

### 25.12.2 Message components

- ATrade does not add the package `carbon-components-svelte` (section 13).
- `foundation/carbon` gets new components that follow the HTML structure
  and the behavior of `ChatLog`, `ChatMessage`, and `ChatDivider` of
  `carbon-components-svelte` (GitHub `main`, `src/Chat/`). They use Bits UI
  and `@carbon/styles` v11 (`cds--` classes).
- Behavior:
  - messages align by author
  - consecutive messages of one author form a group
  - a divider shows each new date
  - the answer streams in
  - a typing indicator shows while the AI assistant writes
  - at the end of the log, the log scrolls to each new message
  - while the user reads older messages, the log does not scroll
  - the log has `role="log"`
- The components are `ChatLog`, `ChatMessage`, `ChatDivider`, and the
  function `arrangeChatLog` (groups and date dividers). Their properties are
  in `docs/architecture.md` section 13. "At the end" means at most 48px
  from the end (section 22). A message that the user sends always scrolls
  the log to the end.
- License: the source repository uses Apache-2.0. Each file that copies or
  adapts its code has a header with the source link and the Apache-2.0
  copyright notice.
- The repository root gets `THIRD_PARTY_NOTICES.md`: the component source,
  the copyright line, and a link to the full license text. `LICENSE` does
  not change.

### 25.12.3 Width, Minimize, and Maximize

- The assistant side column has the width splitter of each `SideColumn`
  (25.13).
- Minimize makes it a 32px rail. The rail has the assistant icon. The rail
  button restores the width from before Minimize.
- The assistant side column also has Maximize. Maximize gives it all the
  width of the workbench except the left side column. The center area then
  shows only a 32px rail.
- A second click on Maximize, or Escape, restores the earlier width. This
  is the same as Maximize of a `Panel`.
- The `Workbench` makes the rail: while a side column is maximized, each
  other child of the workbench that is not a side column is a 32px rail,
  and its content stays in the page. So each page gets the rail without its
  own code. The other side columns keep their width.

### 25.12.4 Condition card (phase 3)

Source: [How the AI assistant uses screens](https://github.com/Mano-Liaoyan/ATrade/issues/150) (B1).

- The card shows the full condition strip of the screen. The style is the
  style of the screen page ([#145](https://github.com/Mano-Liaoyan/ATrade/issues/145)):
  4 groups (base instruments › filters › indicator conditions › order),
  neutral colors, and the count of instruments left at the end of each
  group.
- The card marks each change:

| Change | Mark |
|---|---|
| Added condition | A + icon and a dark border. |
| Removed condition | A − icon, a dashed border, and a line through the text. |
| Changed value | The old value with a line through it, then the new value. |

- The card ends with the buttons "Open screen", "Discard", and "Keep".
- After a click, the buttons change into a state: "Kept" (green check icon)
  or "Discarded" (an icon, and the conditions fade).
- The prototype of #150 is private. The real page must obey the first
  Frontend Design Rule.

Implemented (#210, prototype variant A):

- `AssistantScreenCard` (`frontend/src/routes/assistant/`): the screen name
  and the market, the read-only `ConditionBar` of `#lib/screen` with
  `compareWith`, and the buttons "Open screen", "Discard", and "Keep". The
  bar wraps, and a long tag wraps its text, so all conditions stay visible.
- The change marks come from `markConditionChanges`
  (`frontend/src/lib/screen/condition_changes.ts`). A tag with the same
  subject and operation and another value is a changed value; it has the
  Edit icon and a dark border too. In the start group and the order group,
  each other tag is a changed value. A removed tag stays in its old place.
  Each mark icon has the name "Added", "Removed", or "Changed".
- The card compares with `previous_definition` of `screen_saved` (25.10).
  Without it, the card has no marks.
- The funnel counts come from the next `run_screen` of the same screen
  (`screen_run_finished`). Before a run, the card has no counts.
- After `update_screen`, the old card stays as it was. Its "Open screen"
  opens the latest state of the screen.
- Keep and Discard apply to the screen, so all cards of one screen show the
  same state. The state is a status icon before the screen name, with no
  word: "Kept" is the green check `StatusIndicator` and keeps "Open screen".
  "Discarded" is the neutral `StatusIndicator`, and the conditions fade.

### 25.12.5 Conversation design (option A)

Source: the side column design choice of the user (#159, option A of the
mockups). It takes the patterns of the Codex and Claude Code desktop apps
and of the open-source apps t3code and orca (stablyai/orca). ATrade copies
no code or asset of them.

- A message of the user is a bubble at the end of the line (Carbon
  `chat-bubble-user` token), at most 85% of the width.
- A message of the AI assistant has no bubble. It is text over the full
  width of the log, so tables and code have room. Its model line stays
  under it.
- 2 or more consecutive tool steps are one group. The group line is a
  status icon (`StatusIndicator`, tooltip "Running", "Failed", "Succeeded",
  or "Done") and a button with a chevron and "<n> tool steps": in progress
  while a step runs, error when a step failed, else success. The
  group is open while a step runs and closes when all steps end. A click
  opens or closes it, and the choice stays while the page is open. A single
  tool step stays its own line. Code: `groupToolSteps` and
  `describeToolStepGroup` (`frontend/src/lib/assistant/tool_step_groups.ts`).
- The composer is one box with the Carbon field look (`field-01`, the
  bottom border `border-strong-01`, the focus outline around the whole box),
  with the accessible name "New message". In it: the message input, and a
  line with the inline `Select`s "Model" and "Thinking" and the "Send" icon
  button (Carbon primary, `send--filled` icon). While the AI assistant runs,
  the button is "Stop" (Carbon danger, `stop--filled--alt` icon).
  "Thinking" keeps its width; "Model" gets the rest and cuts a long name
  with an ellipsis and the `title` tooltip.
- Under the box: the inline `Select`s "Provider" and "Credential". Under
  them, the reason when "Send" is disabled.
- `Select` has the property `inline` (the Carbon inline dropdown classes),
  and `IconButton` has `kind` (`ghost`, `primary`, `danger`) and
  `describedBy`.
- The answers render their markdown (25.12.6).

### 25.12.6 Message rendering

The text of an AI assistant message is markdown (GFM). A message of the
user stays plain text. `foundation/markdown` has the `Markdown` component;
`AssistantLog` uses it in `ChatMessage`.

- Blocks: headings, paragraphs, bold, italic, strikethrough, lists, links,
  inline code, block quotes, tables, horizontal rules, and code blocks.
- Security: the text is untrusted. `marked` (lexer only) reads it into
  blocks that hold text only. Svelte renders the text as text nodes, so raw
  HTML of the message shows as text. A link keeps only an `http`, `https`,
  or `mailto` address; another address (for example `javascript:`) shows
  only the link text. A link opens in a new tab with
  `rel="noreferrer noopener"`. An image is a link with its alternative
  text; no image loads.
- Table: the Carbon data table structure (`cds--data-table--xs`). A column
  where each body cell is a number is right aligned with tabular numbers. A
  wide table scrolls in its own styled track.
- Code block: the code and a "Copy" icon button at the top end. No
  label shows; the language is the accessible name of the block. After a
  click, the icon changes for 2 seconds: a checkmark ("Copied") or a
  warning icon ("Not copied"), each with its accessible name and tooltip
  and no text next to it. A closed block gets
  syntax colors from `@pierre/diffs` (loaded on demand): a code block shows
  in its `File` view (no file header, no line numbers), and a shell block
  uses the tokens of its shared highlighter, so the `$` prompts stay. One
  highlighter and one theme for all code and diffs. Languages: Python,
  shell, JSON, YAML, SQL, TypeScript, JavaScript, and TOML. The
  colors are the colors of the code editor (CSS variables, so a theme
  change needs no new highlight).
- Shell block (`bash`, `sh`, `zsh`, `shell`, `console`, `shellsession`):
  each command shows after a `$` prompt. In a block with prompts, a line
  without a prompt is output. "Copy" copies the commands without the prompt
  and without the output.
- Diff block (`diff` or `patch`, or a code block without a language that
  holds a unified diff): a closed block with file headers and a hunk shows
  in the diff view of `@pierre/diffs` (vanilla `FileDiff`, unified, "+" and
  "-" markers, Carbon token colors). The "Copy" icon button is at the end
  of its file header line. Else the block shows each line with
  its "+" or "-" marker and a line color.
- Mermaid block: a closed block shows the diagram of `pele` (loaded on
  demand). Links and images in the diagram are off, and the SVG is cleaned
  (no scripts, event attributes, or external references) before it enters
  the page. The pele colors are Carbon tokens, so the diagram follows the
  theme. While the text streams in, and when pele cannot read the text, the
  block shows the Mermaid code.
- Streaming: the component reads the full text again at each part. An open
  code fence shows as plain code until it closes, so the lines do not
  flicker. A half table shows as text until its delimiter row arrives.

## 25.13 Side column width splitter (all pages)

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q7).

This changes `SideColumn` of `foundation/workbench` on all pages
(watchlist, paper order, strategies, backtests, forward tests), so all side
columns behave the same (section 13).

- Each `SideColumn` gets a vertical `Splitter` on its inner edge:
  `role="separator"`, `aria-orientation="vertical"`.
- The user drags it with the mouse, or moves it 16px with Arrow Left and
  Arrow Right. Home sets the minimum width. End sets the maximum width.
- A double-click on the splitter restores the default width.
- Minimum width: 16rem. Maximum width: 60% of the workbench width. The
  center area keeps at least 24rem.
- The browser keeps the width in `localStorage` under the `storageKey` of
  the side column.
- The Collapse button becomes Minimize. A minimized side column is a 32px
  rail. The rail button restores the width from before Minimize.
- The existing `SideColumn` tests must change.
- Only the assistant side column has Maximize (25.12.3).

## 25.14 Left to the implementation

- Decided (#178): the service code is in `assistant/` (`src/` and
  `tests/`), with its own `package.json` and pnpm lock file. Node.js runs
  `src/main.ts` directly (type stripping). The Dockerfile is
  `deploy/assistant.Dockerfile`. `./scripts/check assistant` runs ESLint,
  `tsc --noEmit`, and Vitest. The CI job is `assistant`. The tests use a
  local fake OpenAI-compatible model server (`assistant/tests/fake_model_server.ts`).
- Decided (#178): `assistant` listens on port 8002 in
  `atrade-assistant-internal`. In #178 it has only `GET /health` for the
  Compose health check. The process does not start a pi session yet. #179
  starts the session with the tool guard. Decided (#179): the routes of
  `/conversations/...` are on the same port.
- Decided (#179): the protocol between `web` and `assistant` for the
  conversations. `web` calls `http://assistant:8002` with
  `AssistantServiceClient` (`backend/src/atrade/assistant/assistant_service.py`,
  `httpx`). The server is `assistant/src/assistant_server.ts`:

  | Request | Answer |
  |---|---|
  | `POST /conversations/{id}/runs` `{text, provider, model, credential_id, thinking_level, system_prompt}` (`system_prompt` since #184). A `thinking_level` that is not a level of pi gets `400`. | One JSON line (`application/x-ndjson`) for each pi event that `web` uses: `text_delta` `{delta}`, `message_end` `{text, provider, model, credential_name, thinking_level}`, `error` `{message}`, and (#182) `tool_step`, `strategy_version_saved`, and `backtest_finished` with the fields of 25.10. The answer ends when the run ends. |
  | `POST /conversations/{id}/steer` `{text}` | `204`, or `409` without an active run. |
  | `POST /conversations/{id}/abort` | `204`. |
  | `POST /conversations/{id}/title` `{provider, model, credential_id}` | `{title}`, or `502` `{detail}`. |
  | `GET /conversations/{id}/messages` | `{messages}`. |
  | `DELETE /conversations/{id}` | Stops the run and deletes the JSONL file. `204`. |

  The conversation ID has only digits, so it cannot name a path outside
  `/data/conversations/`. A wrong body gets `400`. The run has no read
  timeout, because a tool can wait 15 minutes (25.4.2). `web` changes the
  events into the messages of 25.10.
- Decided (#183): the credential and login part of the same protocol:

  | Request | Answer |
  |---|---|
  | `GET /providers` | `{providers}` (25.11). |
  | `GET /credentials` | `{credentials}`, without secrets. |
  | `DELETE /credentials/{id}` | `204`, or `404`. |
  | `POST /logins` `{provider, method, name}` | One JSON line for each login event: `login_step`, then `login_end` `{credential}` or `error` `{message}`. When `web` closes the request, the login stops. |
  | `POST /login-answers` `{prompt_id, value}` | `204`, or `404` when no login waits for the prompt. |

  A run uses the stored credential: `openStoredModel`
  (`assistant/src/providers.ts`) refuses a credential that does not exist
  or that is for another provider. The conversation tests still use
  `createFakeOpenModel` in `assistant/tests/fake_model.ts`. The credential
  and login tests register fake providers (`assistant/tests/fake_providers.ts`):
  `fake-oauth` (each login step, a refresh that fails for the refresh token
  "revoked") and `fake-key`. The test values are only in the test code.
  `web` has its tests with a fake of `AssistantService`
  (`backend/tests/fakes/assistant.py`).
- Decided (#178): the subnet of `atrade-assistant-internal` is
  `172.31.250.0/24`. It is fixed in `deploy/compose.yaml` and is not a
  setting.
- Decided (#181): port 8001 knows the conversation of a request from the
  header `X-ATrade-Conversation-Id` (25.3.2). The constant is
  `CONVERSATION_HEADER` in `backend/src/atrade/foundation/assistant_conversation.py`.
  A missing header gets `422` (FastAPI validation), and an unknown
  conversation gets `422` with a text `detail`. The check of the
  conversation is `conversation_exists` of the `assistant` public entry.
  `app/` gives it to the routers, so `strategy` and `backtest` do not import
  `assistant`.
- Decided (#181): `app/web.py` runs 2 `uvicorn.Server` objects in 1 event
  loop (`serve_both`): port 8000 with the lifespan, and port 8001 with
  `lifespan="off"`. When one server stops, the other stops too.
- Decided (#180): the discarded mark is a row of the table
  `strategy_version_discard` (25.5.1). The trigger
  `strategy_version_append_only` still refuses each `UPDATE` statement.
- Decided (#180): the version source is the `text` column `source` with
  the CHECK constraint `strategy_version_source_check` (`user`,
  `rule_builder`, `ai_assistant`). Decided (#179): the title state and the
  last provider, model, and credential name (25.8.1).
- Decided (#180): Keep of a diff card is not recorded on the server. Only
  Discard changes a version (25.5.2), so a reload shows a version without
  the discarded mark as kept.
- Decided (#180): the discard route answers `409` for a version that the AI
  assistant did not save, and `200` for a version that is already
  discarded (25.11).
- How the server records that the user kept a screen, so `update_screen`
  returns `403` after Keep. Decided (#209): `update_screen` reads the column
  `kept` of the screen. Decided (#210): the Keep route is
  `POST /api/screens/{id}/keep` on port 8000. It sets `kept` (screen section
  24.13).
- Decided (#210): a reload shows no condition card, like the other cards
  (#185: the messages route gives only the text messages). Keep and Discard
  stay on the server: a kept screen has `kept` true, and a discarded screen
  does not exist.
- Decided (#179): a delete of the strategy deletes its conversation rows
  (`ON DELETE CASCADE`). The JSONL files stay in the volume.
- Decided (#179): a title generation failure reaches the browser as an
  `error` message (25.8.3).
- Decided (#184): the default prompt is saved as prompt version 1 when no
  version exists and a conversation starts or the Prompt dialog lists the
  versions. The browser sends the open version number in the body of the
  new conversation request. A trigger refuses each `UPDATE` of a prompt
  version. See 25.9.
- Decided (#182): only the tool `run_backtest` enforces the 5 backtests of
  one user message. Port 8001 does not (backtest section 10.13).
- Decided (#182): no tool and no new route lists the instruments and bar
  periods with saved bars. The AI assistant uses the instrument that the
  user names, or an instrument of `list_backtests`. A range without saved
  bars gets `422`, and the model reads it (backtest section 10.13).
- Decided (#181): `POST /api/backtests` from port 8001 saves the daily
  exchange rates from IBKR like port 8000 (backtest section 10.13). Rates
  are not bars.
- Decided (#210): the phase 3 messages for the condition card are
  `screen_saved` and `screen_run_finished` (25.10). Decided (#179, #182): the
  field names of the other `/ws/assistant` messages (25.10).
- Decided (#205): the field that names the position of a condition in a
  screen problem (25.4.3) is `location`, the path in the request body (screen
  section 24.6).
- Decided (#209): the pages of `read_screen_result`: page size 50 and the
  parameter `offset` (25.4.3).
- Decided (#182): the summaries in the `read_backtest` result: at most 50
  points of the equity curve and the first 50 trades with all fields
  (25.4.1).
- Decided (#183): the credential delete and rename behavior, and the
  meaning of the credential state column (25.7.2). Delete removes the entry
  from the file. There is no rename. The state is `ready` or `failed` (the
  last OAuth refresh failed).
- Decided (#185): the copy of the disabled controls. "Send" is disabled with
  a helper text under the input: "Start a new conversation to send.", "Add a
  credential to send.", "Connecting to the AI assistant.", or (after the
  socket closed) "The connection to the AI assistant closed. Reload the page
  to send.". "Rename
  conversation" and "Delete conversation" are "No conversation to rename" and
  "No conversation to delete" without a conversation. A Select without items
  shows "No credential" or "No model".
- Decided (#185): rename and delete are icon buttons in the top line of the
  side column, after "New conversation".
- Decided (#185): the messages route gives only the text messages (25.11).
  So a reopened conversation shows no tool step, diff card, or metric card.
  Keep is not recorded (#180). A discarded version shows in the version
  `Select` with the toggle "Show discarded versions" (25.5.3).
- Decided (#185): the e2e server (`backend/tests/e2e_server.py`) gives
  `create_web_app` the fake `E2EAssistantService`
  (`backend/tests/fakes/e2e_assistant.py`). The prompt text selects the
  answer: "wait" waits for the abort, "change" saves a version of the AI
  assistant, "backtest" adds a finished backtest, "notitle" makes the title
  generation fail. No real model provider. Decided (#210): "screen" saves a
  screen of the user and a changed screen of the AI assistant, and sends a
  condition card with each change mark and fixed funnel counts.
- Decided (#178): the `tool_call` handler that refuses unknown tools is
  `createToolGuard` in `assistant/src/tool_guard.ts`. It returns
  `{ block: true }` with the reason "<name> is not an ATrade assistant
  tool." for each tool name that is not in `ASSISTANT_TOOL_NAMES`
  (`assistant/src/assistant_tools.ts`, the tools of 25.4.1). It is an inline
  extension factory of the `assistant` process, given to pi through
  `DefaultResourceLoader` with `noExtensions`, `noSkills`,
  `noPromptTemplates`, `noThemes`, and `noContextFiles`. pi loads no
  extension file. The settings of pi are in memory (`SettingsManager.inMemory`),
  so pi reads no `settings.json`.

## 25.15 Facts to check

| Ticket | Fact | How to check |
|---|---|---|
| #133 | The real subscription logins and model calls of each provider. Only a fake OpenAI-compatible model server was used. | Log in through the Credentials dialog with each provider that the user has, and send one message. |
| #140, #133 | OpenAI may count a self-hosted single-user server as "remotely hosted" for the ChatGPT subscription login. The OpenAI pages read on 2026-10-30 do not settle it (`docs/architecture.md` section 21.1). | Ask OpenAI. |
| #140 | Community Antigravity extensions may not work in pi 1.4.0. Not needed in this stage. | Only for the later extension ticket: install the extension in a temporary container, and let the user log in one time. |
| #140 | `ModelRuntime.login()` with an `AuthInteraction` object does each login step from a web page. Checked with fake login flows (#183), not with a real provider. | The first login in the Credentials dialog (#186). |
| #140 | An OAuth refresh of a real provider writes back through ATrade's `CredentialStore`. Checked with a fake refresh and 2 credentials of one provider (#183). | Wait for a real OAuth token refresh and read `/data/credentials.json` (#186). |
| #150 | The run time of a point-in-time backtest from a screen (34 quarters, a screen of 500 instruments, and a multi-instrument backtest). It can be longer than the 15 minute wait. | After the implementation, run one with real data and measure the time. |
| #150 | The token count of a screen result with 500 rows. | After the implementation, count the tokens of one real result. |
| #140 | The VS Code secondary side bar resize and Maximize behavior, which the side column follows. | Read `src/vs/workbench/browser/layout.ts` of VS Code. |
