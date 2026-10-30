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

The AI assistant is a language model that works with the user on the
strategy page. It reads and writes strategy versions, runs and compares
backtests, and (in phase 3) reads, runs, and creates screens. It uses pi
(the pi coding agent) as its agent runtime. It can call only the ATrade
routes of an allow-list.

This section is the target. Most of it is not implemented. #178 adds the
service skeleton and the networks (25.2, 25.3.1). #179 adds the
conversations, the titles, `/ws/assistant` with `prompt`, `steer`, and
`abort`, and the first 5 browser routes (25.8, 25.10, 25.11). The tickets name facts
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
| Assistant side column on the strategy page (25.12) | 2 |
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
- The app of port 8000 refuses each request that arrives on an address of
  the `atrade-assistant-internal` subnet with `403`. The check reads the
  local address of the request (ASGI `scope["server"]`).
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

The screen paths come from #150. They are proposals. The ticket that
implements the screen routes names the final paths.

| Route on port 8001 | Tool | Phase | Limit on port 8001 |
|---|---|---|---|
| `GET /api/strategies` | `list_strategies` | 2 | None. |
| `GET /api/strategies/{strategy_id}` | `read_strategy` | 2 | None. |
| `GET /api/strategies/{strategy_id}/versions/{version_number}` | `read_strategy_version` | 2 | None. |
| `POST /api/strategies` | `create_strategy` | 2 | None. |
| `POST /api/strategies/{strategy_id}/versions` | `save_strategy_version` | 2 | The version records the source "AI assistant" and the conversation ID (25.5). |
| `POST /api/backtests` | `run_backtest` | 2 (single instrument), 3 (universe fields) | The backtest records the conversation ID. |
| `GET /api/backtests` | `list_backtests` | 2 | None. |
| `GET /api/backtests/{backtest_id}` | `read_backtest`, `run_backtest` (wait) | 2 | None. |
| `GET /api/backtests/{first_id}/comparison/{second_id}` | `compare_backtests` | 2 | None. |
| `GET /api/screens` | `list_screens` | 3 | None. |
| `GET /api/screens/{screen_id}` | `read_screen` | 3 | None. |
| `POST /api/screens` | `create_screen` | 3 | The screen records the conversation ID. Its name is "<name> (AI)" (25.6). |
| `PUT /api/screens/{screen_id}` | `update_screen` | 3 | Only a screen that the same conversation created and that the user has not kept. Else `403`. |
| `POST /api/screens/{screen_id}/runs` | `run_screen` | 3 | The screen result records the conversation ID. |
| `GET /api/screen-results/{screen_result_id}` (with page parameters) | `read_screen_result` | 3 | None. |

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
| `list_backtests` | Lists the backtests. | The answer of `GET /api/backtests`. |
| `read_backtest` | Reads one backtest. | The metrics, a summary of the equity curve, and a summary of the trades. |
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

### 25.4.3 Screen tools (phase 3)

| Tool | Does | Result to the model |
|---|---|---|
| `list_screens` | Lists the screens. | The screen list. |
| `read_screen` | Reads one screen. | The conditions of the screen. |
| `create_screen` | Saves a new screen (25.6). | The new screen. On `422`, the problem list. |
| `update_screen` | Changes a screen that the same conversation created and that the user has not kept. | The changed screen. `403` for each other screen. On `422`, the problem list. |
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

- The user discusses screens with the AI assistant only in the assistant
  side column of the strategy page. The screen page `/screens/<id>` has no
  assistant.
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
  subscription or an API key, and which credential.
- The model list of a provider comes from pi
  (`ModelRuntime.getAvailable(provider)` gives only the models with a
  credential).
- Implemented (#183): `GET /api/assistant/providers` lists each pi provider
  with at least one login method (`login_methods`: `oauth` for a
  subscription login, `api_key`). The `models` of a provider are the union
  of `getAvailable(provider)` over its stored credentials. A provider
  without a credential has no models. pi has no models.json in ATrade
  (`modelsPath: null`).

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
  (logic in `credentials.ts`). The table columns are Name, Provider, Kind,
  and State, and a row menu with "Delete credential". Kind is
  "Subscription" or "API key"; an API key adds its last 4 characters
  (`••••7a9f`). State is "Ready" (success) or "Log in again" (error, the
  reason in the cell title). Below the table: a content switcher
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

Implemented (#179):

| Column | Type | Meaning |
|---|---|---|
| `id` | `bigint` identity | The conversation ID. |
| `strategy_id` | `bigint`, foreign key to `strategy` with `ON DELETE CASCADE` | The strategy of the conversation. |
| `title` | `text`, 1 to 200 characters | The title. |
| `title_state` | `text` | `new`, `generating`, `generated`, `not_generated` (the generation failed), or `renamed`. |
| `created_at_utc` | `timestamptz` | The creation time. |
| `last_provider`, `last_model`, `last_credential_name` | `text`, nullable | The provider, model, and credential name of the last AI assistant message. Null before the first answer. |

- The JSONL file of a conversation is `/data/conversations/<id>.jsonl` in
  the volume `atrade-assistant-pi`. Before each run, `assistant` adds a pi
  custom entry `atrade_credential` with the credential name. So each AI
  assistant message of the file has its model (from pi) and its credential
  name.

- A conversation belongs to at most one strategy.
- The strategy page lists only the conversations of the open strategy.
- These records keep the conversation ID:
  - the strategy versions that the AI assistant saved
  - the backtests that it started
  - (phase 3) the screens and the screen results that it made

### 25.8.2 Model change in a conversation

- The user can change the provider, the model, or the credential in the
  middle of a conversation.
- Each AI assistant message shows its model and its credential name.
- The browser sends the provider, the model, and the credential with each
  `prompt`. `assistant` opens the JSONL file again for each run with this
  model, so a change needs no other message (#179).
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

### 25.9.1 `assistant_prompt_version`

| Table | Columns |
|---|---|
| `assistant_prompt_version` | `id`, `version_number`, `text` (the editable part), `created_at_utc` |

- Each save makes a new prompt version. A prompt version does not change
  after it is saved.
- A new prompt version applies only to new conversations. A new
  conversation uses the latest prompt version.
- Each conversation records its prompt version. The top of the conversation
  shows it, for example "Prompt v3".
- So all answers in one conversation use the same prompt and are easy to
  compare. To use a new prompt, the user starts a new conversation.

### 25.9.2 Prompt dialog

- The "Prompt" icon button of the assistant side column opens a `Dialog`.
- The dialog has: a version `Select`, a text area, the fixed part
  (read-only), the "Restore default" button, and the "Save as new version"
  button.
- "Restore default" puts the default text in the text area. It saves
  nothing. The user must click "Save as new version".

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
  `strategy_version_saved`. See 25.14.

Fields (#179). Each message is a JSON object with `type`.

| `type` | Direction | Fields |
|---|---|---|
| `prompt` | Browser to server | `text`, `provider`, `model`, `credential_id` |
| `steer` | Browser to server | `text` |
| `abort` | Browser to server | — |
| `message_delta` | Server to browser | `text` |
| `message_end` | Server to browser | `text`, `provider`, `model`, `credential_name` |
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
  `BacktestFinishedMessage`, `AssistantErrorMessage`, `HeartbeatMessage`,
  `LoginStartMessage`, `LoginAnswerMessage`, `LoginStepMessage`,
  `LoginEndMessage`.

## 25.11 Browser routes on port 8000

The tickets decide the operations. They do not decide the paths. The paths
below are choices of this document. The implementation can change them.

| Operation | Proposed route | Phase |
|---|---|---|
| List the conversations of a strategy | `GET /api/assistant/conversations?strategy_id=...` | 2 |
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
    first. Each conversation has the columns of 25.8.1.
  - `POST` takes `{"strategy_id"}` and answers `201` with the conversation.
    A strategy that does not exist gets `404`.
  - `GET {conversation_id}` answers the conversation and `messages`: the
    user messages and the AI assistant messages with text, each with
    `role`, `text`, `provider`, `model`, and `credential_name` (the last 3
    only for an AI assistant message).
  - `PATCH {conversation_id}` takes `{"title"}` (1 to 200 characters) and
    sets `title_state` `renamed`.
  - `DELETE {conversation_id}` answers `204`.
  - A conversation that does not exist gets `404`. `GET {conversation_id}`
    and `DELETE` answer `503` when `assistant` is not reachable.
- #183 implements the providers and credentials rows:
  - `GET /api/assistant/providers` answers `{"providers": [{id, name,
    login_methods, models: [{id, name}]}]}` (25.7.1).
  - `GET /api/assistant/credentials` answers `{"credentials": [{id, name,
    provider, type, key_last4, state, state_message}]}`. `key_last4` is the
    last 4 characters of an API key, null for a subscription login.
  - `DELETE /api/assistant/credentials/{credential_id}` answers `204`, or
    `404` for a credential that does not exist.
  - All 3 answer `503` when `assistant` is not reachable.
- None of these routes is on port 8001.
- The login itself runs on `/ws/assistant` (25.7.3), because it asks
  questions and waits for answers.
- The routes declare their error bodies with `responses=`
  (`ErrorResponse`), like the other routes (section 13).

## 25.12 Assistant side column on the strategy page

Source: [AI strategy assistant design](https://github.com/Mano-Liaoyan/ATrade/issues/140) (Q6, Q7),
[UI reference: screens, rule builder, and AI assistant](https://github.com/Mano-Liaoyan/ATrade/issues/135).

The strategy page has a right `SideColumn` with the name "AI assistant".
The default width is 28rem.

### 25.12.1 Layout

| Area | Content |
|---|---|
| Top | Conversation `Select`, "New conversation" button, "Credentials" icon button, "Prompt" icon button. The prompt version of the open conversation, for example "Prompt v3". |
| Middle | The conversation messages (`role="log"`) in a `ScrollRegion`. Tool steps, diff cards, metric cards, and (phase 3) condition cards. |
| Bottom | Provider, model, and credential `Select`s in one row. Below them, the message input and the "Send" button. While the AI assistant runs, "Send" becomes "Stop". |

- A tool step is one `StatusIndicator` line, for example
  "Backtest #42 running".
- A diff card shows a code change (25.5.2).
- A metric card shows the `KeyMetricRow` of a finished backtest. It links to
  the backtest.
- Each AI assistant message shows its model and its credential name
  (25.8.2).
- Copy uses the terms of `GLOSSARY.md`: "conversation", not "chat",
  "thread", or "session".
- The Frontend Design Rules of `AGENTS.md` apply. A heading is a name only.
  The side column has no helper text under its name. A disabled control
  says why it is disabled.

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
  | `POST /conversations/{id}/runs` `{text, provider, model, credential_id}` | One JSON line (`application/x-ndjson`) for each pi event that `web` uses: `text_delta` `{delta}`, `message_end` `{text, provider, model, credential_name}`, `error` `{message}`, and (#182) `tool_step`, `strategy_version_saved`, and `backtest_finished` with the fields of 25.10. The answer ends when the run ends. |
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
  returns `403` after Keep.
- Decided (#179): a delete of the strategy deletes its conversation rows
  (`ON DELETE CASCADE`). The JSONL files stay in the volume.
- Decided (#179): a title generation failure reaches the browser as an
  `error` message (25.8.3).
- Whether the default prompt is saved as prompt version 1, or only exists in
  code until the first save.
- Decided (#182): only the tool `run_backtest` enforces the 5 backtests of
  one user message. Port 8001 does not (backtest section 10.13).
- Decided (#182): no tool and no new route lists the instruments and bar
  periods with saved bars. The AI assistant uses the instrument that the
  user names, or an instrument of `list_backtests`. A range without saved
  bars gets `422`, and the model reads it (backtest section 10.13).
- Decided (#181): `POST /api/backtests` from port 8001 saves the daily
  exchange rates from IBKR like port 8000 (backtest section 10.13). Rates
  are not bars.
- The phase 3 message for the condition card. Decided (#179, #182): the
  field names of the other `/ws/assistant` messages (25.10).
- The field that names the position of a condition in a screen problem
  (25.4.3).
- The pages of `read_screen_result` (page size and parameter names).
- Decided (#182): the summaries in the `read_backtest` result: at most 50
  points of the equity curve and the first 50 trades with all fields
  (25.4.1).
- Decided (#183): the credential delete and rename behavior, and the
  meaning of the credential state column (25.7.2). Delete removes the entry
  from the file. There is no rename. The state is `ready` or `failed` (the
  last OAuth refresh failed).
- The UI copy of each disabled control, for example "Send" without a
  credential.
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
