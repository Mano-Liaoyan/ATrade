# ATrade Target Architecture

This document is the target architecture for the full rewrite of ATrade. It
sets the technology stack, the modules, the readability rules, and the test
method. It covers the three capabilities of this stage:

1. Get market data.
2. Run backtests.
3. Paper trading: paper orders sent by hand, and forward tests.

The map [Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129) adds these capabilities. Section 20.1 gives their phases.

4. The indicator library (section 23).
5. Screens (section 24) and the data sources that they need (section 8).
6. Strategy help: the rule builder and the strategy templates (section 9),
   more metrics and robustness checks, multi-instrument backtests, and
   parameter sweeps (section 10), and multi-instrument forward tests with the
   owner ledger (sections 11 and 12).
7. The AI assistant (section 25).

The old system is not a constraint. The rewrite does not reuse old code.

Terms in this document have the meaning that [`GLOSSARY.md`](../GLOSSARY.md)
gives them. Each decision links to the GitHub issue that holds its full
reasoning. The planning map is
[Wayfinder: ATrade rewrite target architecture](https://github.com/Mano-Liaoyan/ATrade/issues/29).

## 1. Design priorities

- Principles: KISS, SOLID, YAGNI.
- Priority order: readability > maintainability > extensibility > performance.
  No design can skip this order.
- Readability means engineering readability. Code must read as plainly as a
  document. Do not use clever or obscure programming techniques.

## 2. Fixed constraints

- ATrade runs on Unix only. On Windows, use WSL.
- The repository is public. Secrets, IBKR account numbers, and tokens must not
  go into git.
- ATrade must support the IBKR paper account.
- A configuration switch must be able to turn on live orders without a change
  to the structure. This stage does not implement live orders.
- The latest desktop versions of Safari, Firefox, Chrome, and Edge must behave
  the same.
- There is one user. ATrade runs on the user's own server. The user reaches it
  from the internet.
- The user lives in the Netherlands and has an IBKR account. The IBKR customer
  type is "Individual (Demo)" and the account number starts with `DU`. Target
  markets are open, for example US and Hong Kong stocks.

## 3. Out of scope

- Local order simulation with fake prices (the old `POST /api/orders/simulate`).
- The 6 disabled modules of the old system: news, portfolio, research,
  econ, node, orders. The rewrite has no page and no entry for them. The old
  `screener` and `ai` modules are also not used: screens (section 24) and the
  AI assistant (section 25) are new designs and reuse no old code.
- The implementation of live orders. That is the next stage, with its own map.
- Tick data. Parameter optimization other than the parameter sweep of
  section 10.
- The AI assistant does not send paper orders and does not start forward
  tests. Only the user does these actions in the UI.
- The AI assistant does not turn natural language into trades that run.
- AI assistant extensions that the AI writes and the user reviews before
  use. A security review of them needs its own design.
- Indicators from financial data, financial data sources (SEC EDGAR or
  others), and financial data of Hong Kong instruments. No data source is
  selected. Phases 1 to 3 use only bars. A later map can add them.
- More than one user.
- Native Windows start scripts.
- Mobile layout.
- The choice of a secret tool after the Enpass membership ends. The
  architecture does not depend on it (see section 15).

## 4. Technology stack

Source: [Technology stack decision](https://github.com/Mano-Liaoyan/ATrade/issues/37)
and its revision comments.

| Area | Decision | Main reason |
|---|---|---|
| Backend language | Python. CPython 3.14, standard GIL build. One exception: the `assistant` service is TypeScript on Node.js 22.19 or later, because the pi SDK is TypeScript (section 25). | NautilusTrader has a Python interface. One language is easiest to read. |
| Backend framework | FastAPI, Pydantic v2, uvicorn with 1 worker. | Plain functions with type hints. Automatic OpenAPI. |
| Backtest and forward test engine | NautilusTrader 2.0. Pin the exact version (`==2.0.0rcN`, then `==2.0.0`). | See section 4.1. |
| IBKR library for the Web process | `ib_async==2.1.0`. Upgrade to 3.0.0 after its release on PyPI. | See section 7. |
| Database | One plain PostgreSQL. No TimescaleDB, Redis, or NATS. | One store covers all data ([storage research](https://github.com/Mano-Liaoyan/ATrade/issues/34)). |
| Database access | psycopg 3 with plain SQL. Use `class_row` to read rows into dataclasses. No ORM. | Each query is SQL that a reader can read directly. |
| Database migrations | Alembic. Migration files contain only SQL. No autogenerate. | The tool chain stays Python only. |
| Python tools | uv, ruff, basedpyright (strict), import-linter. | See section 16. |
| Frontend tools | Vite+ (`vp`, `vite-plus` 1.4.0) runs install, dev, build, and Vitest. pnpm 10 is the package manager. ESLint, not Oxlint, checks the readability rules. | One tool installs Node.js and pnpm and runs Vite and Vitest. Oxlint does not check Svelte templates, type-aware rules in `.svelte` files, or `naming-convention`. |
| Frontend | SvelteKit 3 (`>=3.1.0`) in SPA mode (`ssr = false`, `adapter-static`), TypeScript strict, TypeScript `6.0.3`. | The official router makes one file one page. The 3.0 breaking changes cost nothing for a new project. Svelte 5 is also about 1.5 times faster than React and about 1/5 of the size ([frontend research](https://github.com/Mano-Liaoyan/ATrade/issues/45)). |
| Frontend API types | `openapi-typescript` generates types from the OpenAPI document. Pydantic exports JSON Schema for WebSocket messages, and types come from that schema. The frontend does no runtime validation. | Data types have one definition, in the backend. |
| Bar chart | `lightweight-charts`. | It does not depend on the framework. |
| Code editor | CodeMirror 6, `@codemirror/lang-python`, `@codemirror/merge`, in our own Svelte component. | Small size, low Safari risk, official diff and LSP extensions. |
| Code completion | basedpyright language server in the backend, `@codemirror/lsp-client` in the frontend. | NautilusTrader 2.0 ships `.pyi` stubs, so basedpyright can resolve `Strategy`. |
| Real-time communication | WebSocket. | One technology for live data and for the language server. |
| IBKR connection | TWS API through IB Gateway. Image `ghcr.io/gnzsnz/ib-gateway:stable`, pinned by digest. | IB Gateway is the official IBKR program. The Client Portal Web API has a lower rate limit. |
| AI agent runtime | pi SDK `@earendil-works/pi-coding-agent` (MIT), exact version pinned. Built-in tools off, only custom tools (section 25). | The SDK does each provider login from the web page. RPC mode has no login command ([#133](https://github.com/Mano-Liaoyan/ATrade/issues/133), [#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)). |
| History bars | `databento` Python client for the one-time history import and the quarterly EQUS.SUMMARY download (section 8). | Point-in-time US data with instruments that stopped trading ([#141](https://github.com/Mano-Liaoyan/ATrade/issues/141)). |
| Deployment | User's own server, one Docker Compose project, Cloudflare proxy and Cloudflare Access, Nginx Proxy Manager, GitHub Actions deployment through Tailscale and SSH. | See section 14. |
| Effect-TS | Not used. | Its HTTP and SQL modules are unstable, it has no Svelte binding, and its style conflicts with the readability rules ([Effect-TS evaluation](https://github.com/Mano-Liaoyan/ATrade/issues/47)). |

### 4.1 NautilusTrader 2.0

Sources: [Backtest engine prototype comparison](https://github.com/Mano-Liaoyan/ATrade/issues/42),
[NautilusTrader 2.0 migration evaluation](https://github.com/Mano-Liaoyan/ATrade/issues/49).

- NautilusTrader won the prototype comparison against Lumibot. Its backtests
  were about 9 times faster, it has fewer dependencies, and its license is
  LGPL. The cost is about 50% more code and the need for IB Gateway.
- Phase 1 and phase 2 both use 2.0. The 1.x line gets no fixes after
  2026-08-02.
- 2.0 has no stable release yet (`2.0.0rc7` on 2026-10-15). Each release
  candidate has breaking changes. These rules apply:
  1. Pin the exact version.
  2. Upgrade one version at a time.
  3. After each upgrade, run the IBKR contract tests against the paper account
     (section 17).
- One process can run only one `LiveNode`.
- The IB adapter of 2.0 uses the Rust crate `ibapi`. NautilusTrader 2.0 has no
  required Python dependency. It does not conflict with `ib_async`.
- An IB `client_id` must not be a multiple of 1000. Each process must use a
  different `client_id`.

## 5. Repository layout

Sources: [Module division](https://github.com/Mano-Liaoyan/ATrade/issues/38),
[Readability rules for Python and TypeScript](https://github.com/Mano-Liaoyan/ATrade/issues/51).

The rewrite stays in this repository.

```
backend/
  src/atrade/          # Python package, one directory per capability
  tests/               # backend tests, one directory per capability
  migrations/          # Alembic, one directory for all capabilities
  pyproject.toml
frontend/
  src/lib/             # one directory per capability, plus foundation/
  src/routes/          # pages, the only place that combines capabilities
  e2e/                 # Playwright tests
assistant/             # TypeScript pi SDK service (section 25)
  src/                 # Node.js runs these files directly (type stripping); no build step
  tests/               # Vitest tests, with a fake OpenAI-compatible model server
  package.json         # own pnpm project, run with Vite+ like frontend/
deploy/                # compose.yaml, web.Dockerfile, assistant.Dockerfile
scripts/check          # the quality gate: the same checks as CI (section 17.7)
scripts/deploy         # deploys one commit of main on the server (section 14.2)
docs/
  architecture.md      # this document
  architecture/        # sections moved to their own file (section 18)
  adr/                 # decisions that are hard to reverse
start                  # Unix only: ./start run calls docker compose up
README.md
AGENTS.md
GLOSSARY.md
.env.example
```

The first implementation PR (#62) deleted the old code and the old documents.
This included the .NET code, `workers/`, the old `frontend/`, `start.cmd`,
`start.ps1`, `PLAN.md`, `docs/INDEX.md`, and the old Windows workflow. Git
history keeps the old content.

## 6. Backend modules

### 6.1 Directories

Path: `backend/src/atrade/<module>/`. The directory depth limit (rule F5)
counts from `atrade/`.

| Module | Responsibility |
|---|---|
| `market_data/` | Search instruments. Read bars and daily exchange rates from IBKR and save them in PostgreSQL. Import Databento history bars. Keep the bar tables of each bar source, the source order, the quarterly US universe, the HK instrument list, the daily bar summary, and the stock splits of the stored bars. Push live market data. |
| `watchlist/` | Add, delete, and list watchlist instruments. |
| `strategy/` | Save, check, and compare strategies and strategy versions. Make strategy code from rule builder rules. Hold the strategy template list. |
| `indicator/` | The indicators of screens and strategies (section 23). One class for each indicator. It reads no database and has no table. |
| `screen/` | Save, check, and run screens. Save and read screen results (section 24). |
| `backtest/` | Run backtests and parameter sweeps. Save and read backtest results. Provide the metric functions and the robustness checks (in-sample and out-of-sample split, probabilistic and deflated Sharpe ratio). |
| `paper_trading/` | Paper orders sent by hand, order status, positions, account balance, paper capital, the paper account check, the owner ledger, the ledger changes at a stock split, and the "Split check needed" state. |
| `forward_test/` | Start and stop forward tests. Record forward test results. The ATrade NautilusTrader execution and data clients, the bar fetcher, the quarterly universe job, and the daily stock split check. |
| `assistant/` | Conversations and prompt versions, `/ws/assistant`, the change of pi events into ATrade messages, and the routes of section 25. It holds no credential. |
| `ibkr/` | IB Gateway connection, client IDs, reconnection, request rate limits. Protocol details only, no business rules. |
| `foundation/` | `money`, `clock`, `instrument`, `bar`, `settings`, `order_ref`, `socket_push` (`HeartbeatMessage`, `ChangedMessageSender`, `serve_until_disconnect`, `wait_for_disconnect` for the `/ws/` routes), `error_response` (`ErrorResponse`, the `{"detail": "<reason>"}` body that routes declare with `responses=`). |
| `app/` | Program entry points. They create and connect all dependencies. |

### 6.2 Dependency direction

An arrow means "imports the public entry of". import-linter checks these
rules.

```
market_data   -> ibkr
watchlist     -> market_data
strategy      -> (foundation only)
indicator     -> (foundation only)
screen        -> indicator, market_data, watchlist
backtest      -> strategy, market_data, screen
assistant     -> (foundation only)
paper_trading -> ibkr
forward_test  -> strategy, paper_trading, backtest, market_data, ibkr
all modules   -> foundation
app           -> all modules
```

- `ibkr` depends on no capability.
- `forward_test -> paper_trading` is for the paper account check
  (`require_paper_account()`, and `PaperAccountMonitor` for the balance at
  start). From phase 3 (section 20.1) it is also for the owner ledger
  (`check_owner_order()`, `record_owner_fill()`, `read_owner_positions()`,
  `transfer_owner_to_by_hand()`, `apply_stock_split()`).
- `forward_test -> ibkr` is only for the `GatewayConnection` protocol of the
  child process: the connection for the paper account check, the warm-up
  bars (`read_historical_bars()`), and the stop steps
  (`read_own_open_orders()`, `cancel_order_and_wait()`) (#76, section 22).
  From phase 3 it is also for the connections of the bar fetcher and of the
  stock split check.
- `forward_test -> market_data` is only to save the bars that a forward test
  receives (`save_received_bars()` for the warm-up bars,
  `save_received_bars_blocking()` for each live bar), so a same-period
  backtest finds them (`docs/architecture/forward_test.md` sections 12.8 and
  12.15). From phase 3 it is also for the bar fetcher, the quarterly
  universe update, the warm-up reads in the source order, and the change of
  the stored bars at a stock split (`docs/architecture/market_data.md`).
- `market_data` holds the Databento client. `ibkr` stays IBKR only.
- `backtest -> screen` is only for the point-in-time screen runs of a
  backtest universe (`docs/architecture/screen.md` section 24.9).
- `backtest -> strategy` also reads the sweep parameters of a strategy
  version with the Python AST (`docs/architecture/backtest.md` section
  10.11.1).
- `indicator` imports `nautilus_trader` for the built-in indicators. Strategy
  code imports `atrade.indicator` at run time in the backtest child and the
  forward test child. import-linter does not check user code.
- import-linter puts `indicator` in one layer with `ibkr`, just above
  `foundation`. So `indicator` can import only `foundation`, and `indicator`
  and `ibkr` do not import each other. A contract keeps the internal files
  of `indicator` private (#160).
- `assistant` does not import other capabilities. `app/` builds the port 8001
  app from the routers of `strategy`, `backtest`, and `screen`
  (`docs/architecture/assistant.md`). The `conversation_id` foreign keys of
  `strategy_version`, `backtest`, and the screen tables point at
  `assistant_conversation` (section 6.3 allows a foreign key).
- `paper_trading` does not import `forward_test`. Until phase 3, the refusal
  of paper orders by hand on the instrument of a running forward test
  (section 12.2) gets a function from `app/web.py`, which calls
  `forward_test.find_forward_test_on_instrument()`. From phase 3, the owner
  ledger replaces this refusal, and `app/web.py` gives `paper_trading` the
  function `forward_test.read_allocated_capital()` for the "By hand" capital.
- `forward_test -> backtest` is only for the comparison, the metric
  functions, and the look-back of `request_bars` (`find_look_back_length()`,
  `write_look_back_catalog()`).
- `backtest` does not depend on `paper_trading`. A backtest request carries
  `paper_capital_usd` as an input.
- `forward_test` and `paper_trading` do not depend on each other for order
  sources. Both use `foundation/order_ref.py`.

### 6.3 Module rules

- Each capability has exactly one public entry file. Other files are internal.
- Each table belongs to one capability. Only the code of that capability reads
  or writes the table. Do not JOIN across capabilities. A foreign key to a
  table of another capability is allowed, for example `strategy_version_id`
  (section 9.1).
- Alembic migration file names include the capability name.
- HTTP routes live in their capability, for example
  `backtest/http_routes.py` with `create_backtest_router(backtest)`. The
  public entry exports the router factory. `app/web.py` only mounts routers and
  passes dependencies.
- Each capability has its own WebSocket path, for example `/ws/market-data`,
  `/ws/paper-trading`, `/ws/forward-tests`. There is no general message
  dispatcher.
- `app/` creates all dependencies by hand and passes them as arguments. There
  is no dependency injection container. FastAPI `Depends` is only for simple
  values.

### 6.4 Program entry points

| Entry point | Runs in | Purpose |
|---|---|---|
| `app/web.py` | Compose service `web` | HTTP API, WebSocket, language server processes. 1 uvicorn worker on port 8000. A second listener on port 8001 has only the allow-list routes for the `assistant` service (section 25). Runs the daily bar update after the close of each trading day (section 8). |
| `app/backtest_process.py` | Child process of `web` | Runs one backtest. Gets only a backtest ID. Reads the request and the strategy version from PostgreSQL. Writes the result to PostgreSQL. A run of a parameter sweep is a backtest row with its own `parameters`. For `universe_kind=screen`, it runs the saved copy of the screen at each rebalance (section 24.9). |
| `app/forward_test_worker.py` | Compose service `forward-test` | Reads forward test state from PostgreSQL. Starts and stops one child process per forward test. From phase 3 it also runs the bar fetcher (client ID `ATRADE_IBKR_BAR_FETCHER_CLIENT_ID`, after each daily close), the quarterly universe update (06:00 ET on the first trading day of each quarter), and the daily stock split check (08:00 ET, 08:30 HKT). |
| Databento import program (name left to the implementation) | One-time run by the user | Imports the bought Databento files into `databento_bar`. Writes `stock_split` and `databento_symbol_link` rows for the user check (section 8). |
| `assistant` service (TypeScript) | Compose service `assistant` | Runs the pi SDK for all conversations. Calls only port 8001 of `web`. Keeps the credentials in the volume `atrade-assistant-pi` (section 25). |
| `app/forward_test_process.py` | Child process of `forward-test` | Runs one forward test (`run`) or only cancels its open orders (`cancel_orders`). Gets the forward test ID and the mode. Stops at `SIGTERM`. |

A restart of `web` does not stop forward tests.

### 6.5 Web app routes outside the capabilities

`app/` owns three routers that belong to no capability:

| Route | Behavior |
|---|---|
| `GET /api/access-session` | `200` with `{"logout_url": "/cdn-cgi/access/logout"}` when the request has the header `Cf-Access-Jwt-Assertion` (it came through Cloudflare Access, section 14), else `{"logout_url": null}`. The Web process does not check the token. The answer only decides if the header shows the Log out link. |
| `GET /api/health` | `200` with `{"status": "ok", "database": "ok", "time_utc": ...}` when the Web process can connect to PostgreSQL. `503` with `"status": "degraded"` and `"database": "unreachable"` when it cannot. The time comes from `foundation/clock`. |
| `GET /{path}` | The built frontend (section 14.1). It is mounted after all other routers. |

Port 8000 refuses with `403` each request that comes from an address of the
`atrade-assistant-internal` subnet (section 25).

## 7. IBKR access

Section 7 is in [`docs/architecture/ibkr.md`](architecture/ibkr.md). It holds
the IBKR decisions, the `ibkr` module, `GET /api/ibkr/gateway`, the
`ib-gateway` Compose service, and the contract tests.

## 8. Market data and watchlist

Section 8 is in [`docs/architecture/market_data.md`](architecture/market_data.md).
It holds the bar storage decisions, the watchlist decisions, the
instrument search (`GET /api/market-data/instrument-search`), the
watchlist routes (`/api/watchlist`), the daily exchange rates of
backtests, the bar sources and the source order, the Databento history
import, the quarterly US universe, the HK instrument list, the daily bar
update and the daily bar summary, and the change of the stored bars at a
stock split.

## 9. Strategies and strategy versions

Section 9 is in [`docs/architecture/strategy.md`](architecture/strategy.md).
It holds the storage rules, the `strategy` and `strategy_version` tables, the
strategy file format and the start points (Blank code, Blank rules, strategy
templates), the rule builder, the strategy template library, the checks
before save, the strategy HTTP routes, and the editor pages.

## 10. Backtest

Section 10 is in [`docs/architecture/backtest.md`](architecture/backtest.md).
It holds the backtest decisions and isolation controls, the backtest tables,
the run flow in the child process, the metric functions and the robustness
checks, multi-instrument backtests and universes, parameter sweeps
(`/api/sweeps`, `/sweeps/<id>`), walk-forward, the backtest HTTP routes
(`/api/backtests`), and the backtest pages.

## 11. Paper trading

Section 11 is in [`docs/architecture/paper_trading.md`](architecture/paper_trading.md).
It holds the live order switch, the paper account check, paper orders sent by
hand, the order list, the `paper_trading` module, `/ws/paper-trading`, the
account overview and the paper order form (11.7), the order routes (11.8), and the balance in USD for any base
currency (11.9), the owner ledger (11.10), stock splits in the owner ledger
(11.11), and the limits of the owner ledger (11.12).

## 12. Forward test

Section 12 is in [`docs/architecture/forward_test.md`](architecture/forward_test.md).
It holds the forward test decisions (input, shared instruments and the owner
ledger, Web and worker, client IDs, paper account check, stop, recovery,
records, order source, comparison, the multi-instrument forward test,
allocated capital, the ATrade execution and data clients, the bar fetcher,
the quarterly universe, the stock split check) and the implementation: the `forward_test` table,
the routes under `/api/forward-tests`, `/ws/forward-tests`, the worker, the
child process, and the forward test page.

## 13. Frontend

Sources: [Technology stack decision](https://github.com/Mano-Liaoyan/ATrade/issues/37),
[Readability rules for Python and TypeScript](https://github.com/Mano-Liaoyan/ATrade/issues/51).

- SvelteKit 3 in SPA mode. Do not use the SvelteKit server features:
  `+page.server.*`, `+layout.server.*`, `+server.*`, `hooks.server.*`,
  `*.remote.*`, and form actions. ESLint fails on these file names.
- SvelteKit 3 reads configuration from `vite.config.ts` in `sveltekit({...})`.
  It does not read `svelte.config.js`. `defineConfig` comes from `vite-plus`,
  and tests import from `vite-plus/test`. `pnpm-workspace.yaml` maps `vite`
  to `@voidzero-dev/vite-plus-core`.
- `#lib` replaces `$lib`. `package.json` declares it in `imports`.
  `#lib/*` maps to `./src/lib/*/index.ts`. A deep import fails at type check
  and build time.
- `src/lib/` has one directory per capability (`lib/market_data/`,
  `lib/backtest/`, and so on) and `lib/foundation/`.
- A capability can import only `#lib/foundation/<module>` and the generated
  API types `#lib/api`. Capabilities must not import each other. Only
  `src/routes/` combines capabilities.
- Generic UI with no domain meaning goes in `foundation/`, for example
  `foundation/code_editor/`. Parts with domain meaning stay in the capability.
- The UI uses IBM Carbon Design System v11 for the look and Bits UI 2 for
  the behavior ([#84](https://github.com/Mano-Liaoyan/ATrade/issues/84)).
  The look comes from the official `@carbon/styles` SCSS. Bits UI gives the
  keyboard control, the focus control, the ARIA attributes, and the
  positioning of floating content. Do not use `carbon-components-svelte` or
  `@carbon/web-components`.
- `foundation/carbon` combines Carbon and Bits UI into general components,
  for example `Tag`, `Tooltip`, and `TooltipProvider`. A component writes the
  Carbon HTML structure and class names (`cds--*`). Carbon CSS shows a state
  with a class, for example `cds--popover--open`, not with `data-state`. The
  component changes the Bits UI state into the Carbon class.
  `foundation/carbon/carbon_state.ts` has these changes as functions with unit
  tests, for example `dropdownClasses({ open, disabled })`.
- Form components of `foundation/carbon`: `Button` (`kind`, `size`, bindable
  `ref`), `TextInput` (`label`, bindable `value`, `invalidText`), `Select`
  (Carbon dropdown on Bits UI Select: `label`, `items`, `value`,
  `onValueChange`), `ContentSwitcher` (on Bits UI Tabs without panels:
  `label`, `items` with an optional `accessibleLabel` for a short name,
  `value`, `onValueChange`, `size`; size `sm` and `lg` also write
  `cds--layout--size-<size>`), and `Dialog` (Carbon modal on
  Bits UI Dialog: `open`, `onOpenChange`, `title`, `label`, `primaryText`,
  `secondaryText`, `busy`, `returnFocus`, `onPrimary`). The `Dialog` title is
  the accessible name of the dialog. Without `primaryText`, the `Dialog` is a
  Carbon passive modal: no footer, and its content has its own controls.
- `foundation/carbon` `DataTable` writes the Carbon data table: `columns`
  (`header`, `align: 'right'` for a number column, `isMenu` for the column
  of row menus), `size`, and a `rows` snippet for the body rows. A number
  cell has `align="right"` and tabular numbers.
- `foundation/carbon` `OverflowMenu` is the Carbon overflow menu on Bits UI
  DropdownMenu: `label` (the trigger name), `items` (`label`, `disabled`,
  `danger`, `onSelect`), and `size`. The menu goes under `<body>`, so a
  scroll region does not clip it.
- `foundation/carbon` `InlineNotification` is the Carbon inline
  notification: `kind` (`success` and `info` are a status, `error` and
  `warning` are an alert), `title`, `subtitle`, `lowContrast`, and
  `onClose` (it adds the close button "Close notification"). A page keeps
  the result of an action as a `NotificationMessage` (`kind`, `title`,
  `subtitle`) and spreads it on the component.
- `foundation/live_socket` has `LiveUpdatesNotification` (`isConnected`): the
  "Live updates paused" warning that a page shows while its live socket is
  not connected.
- The global class `atrade-auto-grid` of `carbon.scss` is the grid of the
  fields of a form or of a list of values: as many columns as fit, each at
  least 12rem wide (9rem with `atrade-auto-grid--narrow`, 14rem with
  `atrade-auto-grid--wide`), with a `--cds-spacing-05` gap.
- While a button action runs, the button is disabled and its text says why,
  for example "Saving…", "Creating…", or "Starting…".
- `foundation/carbon` `StatusIndicator` shows a status as an icon and a word
  with a color: `kind` (`success`, `in-progress`, `warning`, `error`,
  `neutral`; each kind has its own icon shape) and `label`. `Select` takes
  `placeholder` (the trigger text while no item is selected). `TextInput`
  takes `type` `datetime-local` for a native date and time input.
- The forward test page (`/forward-tests/<id>`, spec #99, ticket
  [#105](https://github.com/Mano-Liaoyan/ATrade/issues/105)) is a workbench
  with the structure of the backtest page: the "Forward tests" `SideColumn`
  with the live list (`routes/forward-tests/ForwardTestList.svelte`, 32px
  rows, from `ForwardTestsOnInstrumentsFeed.forwardTests`) and the
  "New forward test" dialog (form id `start-forward-test`); the forward test
  panel (header line with the status, the red "Stop forward test" icon button
  while the forward test can stop, and the "Backtest the same period" icon
  button; `KeyMetricRow`; `EquityDrawdownChart`, which lists the
  interruptions under the chart and marks grey the recorded bar ends inside
  one) over
  the Fills / Comparison / Logs panel. `/forward-tests` opens the newest
  forward test. The status of a forward test is a `StatusIndicator`
  (`findForwardTestStatusKind` of `forward_test`).
- Only `src/lib/foundation/` can import `bits-ui`. ESLint fails on an import
  of `bits-ui` in a capability or in `src/routes/`. Capabilities and routes
  use the components of `#lib/foundation/carbon`.
- `foundation/carbon/carbon.scss` is the one global SCSS entry.
  `foundation/carbon/index.ts` imports it, so each importer of
  `#lib/foundation/carbon` gets the styles. The entry loads `config` (with
  `$css--font-face: false`), `themes`, `theme`, `reset`, `zone` (only g100),
  `layer`, `layout`, and the components that ATrade uses. `layer` and
  `layout` are necessary: buttons, tabs, text inputs, and content switchers
  read their sizes from them. Do not load the full Carbon `styles.css`, and
  load the Carbon grid only when a page uses it.
- To add a Carbon component, add
  `@use '@carbon/styles/scss/components/<name>';` to the component list in
  `carbon.scss`. Keep each `@use` above the theme rules: a component adds its
  component tokens (for example `--cds-button-*`) when Sass loads it, and the
  theme rules then write these tokens for each theme.
- The Sass settings are in `css.preprocessorOptions.scss` of
  `vite.config.ts`. The Carbon SCSS loads packages that are not direct
  dependencies, for example `@carbon/layout`. pnpm keeps them in
  `node_modules/.pnpm/node_modules`, so `loadPaths` includes that directory.
- The fonts are IBM Plex Sans and IBM Plex Mono from the `@ibm/plex-sans`
  and `@ibm/plex-mono` packages. `foundation/carbon/index.ts` imports their
  CSS, and the build contains the font files. ATrade does not load fonts
  from the IBM font server.
- Themes: `:root` has the Carbon g10 tokens (light). With
  `prefers-color-scheme: dark` and no `data-theme="light"` on `<html>`, it has
  the g100 tokens (dark). `data-theme="dark"` on `<html>` also gives g100.
- The theme button (`ThemeButton` of `foundation/color_scheme`) is a Carbon
  header action button in `cds--header__global` with a Carbon tooltip. A
  click changes the theme choice: System, Light, Dark, then System again.
  System is the default. The icon (`@carbon/icons` Screen, Light, Asleep),
  the accessible name, and the tooltip show the current choice, for example
  "Theme: System". Light sets `data-theme="light"` (g10 with a dark system),
  Dark sets `data-theme="dark"` (g100 with a light system), and System
  removes the attribute. The choice is in `localStorage` (key
  `atrade.theme`). A small script in `src/app.html` applies the saved choice
  before the first paint. When the storage is not available, the page starts
  with System and the button works until the page reloads.
- `foundation/carbon` has `Icon`: it renders an icon descriptor of
  `@carbon/icons`, for example `@carbon/icons/es/light/20.js`.
  `carbon_icons.d.ts` declares these modules with the type `CarbonIcon`.
- The app shell header (`src/routes/+layout.svelte`) is the Carbon UI shell
  header in a `cds--g100` zone in all themes. It shows the product name, the
  page links (Home, Screens, Strategies, Backtests, Forward tests) with
  `aria-current="page"` on the current page, the backend status, the IB
  Gateway status, the server time, and the Paper tag. The Paper tag is a
  Carbon operational tag with a tooltip. The tooltip shows the checked paper
  account number with its middle hidden, for example `DU****567`. The header
  reads the account check from `/ws/paper-trading`. Carbon hides the header
  navigation below 1056 px. ATrade is a desktop app, so it keeps the
  navigation at all widths. Header buttons go in `cds--header__global`.
- The Log out link (`LogOutButton` of `foundation/access_session`) is the
  last header action, after the theme button: a Carbon header action with
  the `@carbon/icons` Logout icon, the accessible name "Log out", and a
  Carbon tooltip. It shows only when `GET /api/access-session` gives a
  logout URL, so a development machine has no Log out link. A click opens
  `/cdn-cgi/access/logout`: Cloudflare answers this path, deletes the
  Access cookie, and ends the Access session in all Access applications.
  When the browser is still logged in to GitHub, the next visit logs in
  again without a passkey (section 14).
- The command palette shell is `CommandPalette` of
  `foundation/command_palette`: a header search icon button ("Open command
  palette") and a Carbon modal with a large Carbon search field and Carbon
  contained lists, on Bits UI Dialog and Command. Ctrl K or Cmd K opens and
  closes it on each page, and Escape closes it. Bits UI Command has
  `vimBindings` off, because they take Ctrl K. The text filters the commands,
  Arrow Up and Arrow Down move the highlight, and Enter runs the command. When
  no command matches, the palette shows "No results". `src/routes/` gives the
  commands (`palette_commands.ts`): go to a page, go to the instrument page of
  a watchlist instrument, open the start form of a backtest or a forward test
  (the form ids `start-backtest` and `start-forward-test`; the backtest page
  opens its "New backtest" dialog for `#start-backtest`, and the forward test
  page opens its "New forward test" dialog for `#start-forward-test`), and change the
  theme (`selectThemeChoice` of `foundation/color_scheme`). A command only
  opens a page or a form. No command sends a paper order or starts a backtest
  or a forward test. The layout reads the watchlist each time the palette
  opens. While the read runs, the command list has `aria-busy="true"` (prop
  `busy`). New commands make Bits UI Command move the highlight to the first
  command, so the e2e tests wait until `aria-busy` is `false`.
- `foundation/carbon` has `Combobox` (Carbon combo box on Bits UI
  Combobox). The page gives the candidates as `items` (`value`, `label`,
  `disabled`). The list is a Bits UI `ContentStatic` in the
  `cds--list-box__menu` and scrolls in a `ScrollRegion` named by
  `listLabel`. `statusText` and `invalidText` show below the field.
  `hideLabel` keeps the label for screen readers only, and `size` `sm` gives
  the 32px field (`cds--layout--size-sm`).
- Generated API types go in `lib/api/`. `python -m atrade.app.openapi_document`
  writes the OpenAPI document to `lib/api/openapi.json`, and
  `openapi-typescript` writes `lib/api/index.ts`. `vp run generate:api` runs
  both. Both files are committed. The backend test
  `tests/app/test_openapi_document.py` fails when `openapi.json` does not
  match the routes, and `vp run check:api` fails when `index.ts` does not match
  `openapi.json`. Use `components['schemas'][...]`; do not write API types by
  hand. OpenAPI does not describe WebSocket messages, so
  `app/openapi_document.py` adds the Pydantic JSON Schema (serialization mode)
  of each WebSocket message model to `components.schemas`. A capability
  exports its models, for example `MARKET_DATA_SOCKET_MESSAGE_MODELS`,
  `FORWARD_TEST_SOCKET_MESSAGE_MODELS`, and
  `PAPER_TRADING_SOCKET_MESSAGE_MODELS`. Each list has `HeartbeatMessage` of
  `foundation/socket_push`. A message schema must not have the name of a
  different schema. Routes declare their error bodies with `responses=`
  (`ErrorResponse` of `foundation/error_response`), so the frontend does not
  write error types by hand.
- `foundation/http_request` sends the HTTP requests of the capabilities:
  `sendRequest`, `requestJson`, `readJsonBody`, `readErrorMessage`,
  `describeErrorBody`, `BACKEND_NOT_REACHABLE`, and the type `RequestResult`.
  An error message is the `detail` text, the first field error of a list
  `detail` ("<field>: <message>"), or "<action> failed with HTTP status N.".
- `foundation/live_socket` also has `readSocketMessage`: it returns a parsed
  socket message with its generated type when its `type` matches, else
  `null`.
- `foundation/scroll_region/` has `ScrollRegion`: a region that scrolls inside
  itself. It hides the native scrollbar and draws its own track and thumb
  (`role="scrollbar"`, named "<region label> scroll bar"). The thumb can be
  dragged, a click on the track scrolls one page, and the track takes Arrow,
  Page Up, Page Down, Home, and End keys. Use it for each region that can
  overflow (section 13.1).
  The track and the thumb use Carbon tokens. With `fill` (no `maxHeight`), the
  region takes the full height of its parent, for example a workbench panel.
  `role` is `region` (the default) or `log`. The bindable `viewport` gives
  the scrolling element to a parent that scrolls it, for example `ChatLog`.
- WebSocket reconnection and heartbeat are our own code. Reconnection is
  required, because browsers suspend background tabs in different ways.
  `foundation/live_socket` does it: a server heartbeat every 10 seconds, a
  reconnection after 25 seconds without a message or after a close, and a
  delay from 1 to 10 seconds between attempts. A background tab can delay
  the timers, so when the page becomes visible (`visibilitychange`), it
  connects again at once if the last message is 25 seconds old or more, or
  if it waits for a reconnection. After stop, a message of the closing
  socket is not passed on.
- `lightweight-charts` uses the Apache 2.0 license. The UI must show the
  TradingView attribution. Each chart uses `ChartFrame` of
  `foundation/chart_frame`: the canvas container (`role="img"`, `label`,
  bindable `canvas`) and the one attribution line under it ("Chart by
  TradingView Lightweight Charts™"), so all charts show the same attribution.
  With `fill`, the frame fills the height of its parent, and the chart
  (`autoSize`) follows each size change of its container, for example after a
  side column is minimized or resized. Without `fill`, `height` and `minHeight` set the
  canvas height. `readChartThemeOptions(container)` and
  `readChartColor(container, token)` of `foundation/chart_frame` read the
  Carbon tokens for each chart. The price scales use the number formats of
  the tables and tiles: `CHART_PRICE_FORMAT` ("11,000.00", prices and equity)
  and `CHART_PERCENT_FORMAT` ("-37.71 %", the drawdown, `formatSignedPercent`).
- A chart draws on a canvas and reads the color tokens only when it draws.
  `foundation/color_scheme` has `watchColorScheme(onChange)`. It calls
  `onChange` after a change of `prefers-color-scheme` and after a change of
  `data-theme` on `<html>` (the theme button). Each chart applies the new
  colors to the chart and its series, without a page reload and without a
  new chart. The code editor and the code diff use the same watch and
  `isDarkColorScheme()` to change their syntax colors.
- The bar chart reads only Carbon tokens: `--cds-layer-01` (background),
  `--cds-text-secondary` (text), `--cds-border-subtle-01` (grid and scale
  borders), `--cds-support-success` (up bars), and `--cds-support-error`
  (down bars).
- Workbench pages (spec [#99](https://github.com/Mano-Liaoyan/ATrade/issues/99),
  [#102](https://github.com/Mano-Liaoyan/ATrade/issues/102)) fill the window
  below the header and do not scroll as a page. Each region that can overflow
  scrolls in itself (`ScrollRegion`). `foundation/workbench` has the shared
  parts, and each workbench page uses them, so all pages have the same header
  lines, buttons, and splitter:
  - `Workbench`: the frame, a row of side columns and panels. When the main
    region has a workbench (`.atrade-workbench`), the app shell gives it the
    window height below the header (`:has()`), without padding.
  - `SideColumn` (`label`, `side` `start` or `end`, `storageKey`, `width`,
    default 17.5rem): a 32px header line with the name and the Minimize
    button ("Minimize <label>"). A vertical `Splitter` on the inner edge
    (`role="separator"`, `aria-orientation="vertical"`) changes the width:
    drag, or Arrow Left and Arrow Right 16px, Home minimum, End maximum,
    double-click default. The width is 16rem to 60% of the workbench, and the
    center keeps at least 24rem. `localStorage` keeps the width under
    `storageKey`. A minimized column is a 32px wide rail with the Open button
    ("Open <label>"), and it opens with the width from before. The body stays
    in the page while the column is minimized, so a form keeps its values.
    Only the AI assistant column has Maximize (section 25)
    ([#140](https://github.com/Mano-Liaoyan/ATrade/issues/140)).
  - `PanelSplit` (`storageKey`, `panels`, and the snippet `panel(id,
    state)`): 2 or more stacked panels. Each `PanelSpec` has `id`,
    `minPixels`, `defaultPixels` (not for the first panel), and
    `splitterLabel` (the name of the splitter above it). The first open panel
    fills the rest of the height; each other open panel has its own height.
    A `Splitter` shows between 2 open panels while no panel is maximized. The
    snippet gets a `PanelState` (`size`, `headerOnly`, `onToggleMinimized`,
    `onToggleMaximized`, `onRestore`) to spread on a `Panel`. Several panels
    can be minimized, but one panel stays open. One panel at a time is
    maximized, and the other panels show only their header lines. A second
    click on the same button restores the panel. A minimized panel stays
    minimized through a maximize of another panel and its restore. Escape restores a maximized
    panel of the split that has the focus (the innermost split first), or of
    each split when the focus is outside all splits. `panel_split.ts` has the
    state as functions with unit tests.
  - `Panel` (`label`, `PanelState`, and `tabs` or a `header` snippet): a
    region with a 32px header line and a body that fills the rest. The header
    line has Carbon tabs (size `sm`) or other content, and at its right end
    the Minimize and Maximize icon buttons ("Minimize panel", "Maximize
    panel", "Restore panel"). A double-click on an empty part of the header
    line toggles Maximize. A tab of a panel that shows only its header line
    opens the panel again. With a `statusBar` snippet, the panel works like
    the VS Code panel: a 24px status bar is always at its bottom, a panel
    that shows only its header line shows only the status bar, and a click
    on the selected tab minimizes the panel. Status bar controls have the
    class `atrade-status-bar__item`. A `PanelSpec` with `startsMinimized` is
    minimized in the default layout, and also when a stored layout has no
    height for it (a layout stored before the panel existed). `PanelSplit` exports `openPanel(id)`
    (through `bind:this`): it opens a panel that shows only its header line
    or its status bar.
  - `PanelHeader` (`end` snippet): the 32px header line with the class
    `atrade-panel-header`. `Splitter` (`label`, `controls`, `value`, `min`,
    `max`, `grow`, `onValueChange`, `ondblclick`): a `role="separator"`
    (WAI-ARIA window splitter) with `aria-controls` on the region that it
    resizes. `grow` is the direction in which the splitter moves to make that
    region bigger. With `up` (the default) the splitter is horizontal above a
    panel: its value is the height of that panel, and Arrow Up and Arrow Down
    move it 16px. With `left` or `right` the splitter is vertical on the inner
    edge of a `SideColumn`: its value is the column width, and Arrow Left and
    Arrow Right move it 16px. Home gives the region its minimum size, and End
    its maximum size. The splitter of a `SideColumn` has the name
    "Resize <label>" and no visible text.
  - The browser keeps each layout in `localStorage` (`readStoredLayout`,
    `writeStoredLayout`). Blocked storage gives the default layout.
- `foundation/carbon` `IconButton` (`label`, `icon`, `align`, `disabled`, `onclick`) is the Carbon ghost icon-only button, size `sm`, with a Carbon
  tooltip that gives the action name. A disabled `IconButton` has
  `aria-disabled` and stays focusable, so its tooltip and its `label` say why
  it is disabled. A toolbar button can also take `shortcut` (shown in the
  tooltip after the label, and `aria-keyshortcuts`), `tone` (`neutral`,
  `interactive`, `success`, `warning`, `error`: the icon gets
  `--cds-icon-secondary`, `--cds-icon-interactive`, or the support color),
  `marked` (a `--cds-icon-interactive` dot on the icon), and `busy` (the
  icon turns; use it with `disabled`). The icon shape changes with each
  state, so the color is never the only sign. `Select` takes `size` (`sm`)
  and `hideLabel`. `Tabs` (and `Panel` `tabs`) take `itemLabel`, a snippet
  that renders the text of a tab. `SideColumn` takes an `actions` snippet: icon buttons in its
  header line before the Minimize button. `Tabs` takes `size` (`sm` gives the 32px
  tab line), `lineEnd` (content at the end of the tab line), `lineClass`, and
  `panelClass`.
- The instrument page (`/instruments/<exchange>/<symbol>`) is a workbench.
  The left `SideColumn` "Watchlist" lists the watchlist instruments in 32px
  rows: symbol, last price, and change from the previous close (from the
  daily bars). A row opens its instrument page with the same bar period. The
  center `PanelSplit` has the chart panel and the "Paper account" panel. The
  chart panel header line has the instrument name, the last price, the change
  from the previous close, and the bar periods as a Carbon `sm` content
  switcher with short names (1m, 5m, 15m, 30m, 1h, 1D). The arrow keys, Home,
  and End select a bar period at once. The page address keeps the bar period,
  and the switcher keeps the focus. The bar chart fills the rest of the panel.
  The bar count and the live bar are status text for screen readers. The bars
  and the live bar of the page belong to one chart request, so the chart gets
  no data of the previous bar period after a change. The "Paper account"
  panel has the tabs Positions, Open orders, and Filled today, with 32px
  rows. The right `SideColumn` "Paper order" has `InstrumentOrderPanel` of
  `paper_trading` (IBKR Desktop layout). The order is for the instrument of
  the page, so the panel has no instrument fields. From top to bottom: the
  Buy / Sell content switcher; Quantity and Order type, Limit price and Time
  in force in two columns (the limit price starts with the last price); the
  order value, position, average cost, unrealized P&L, cash (USD), and net
  liquidation (USD) as `MetricTile`s in a `MetricRow` with `columns` 2; and
  the full-width button "Review buy order" (primary) or "Review sell order"
  (danger). The button opens the confirmation dialog with the PAPER tag and
  "Send paper order". A paper account check that did not pass, or a running
  forward test on the instrument, disables the button, and the status above it
  says why with a `StatusIndicator` (`findInstrumentOrderBlock`). A sent order
  shows in the Open orders tab from `/ws/paper-trading`. The fields and the
  button stay in view; only the numbers scroll, in their own `ScrollRegion`.
  The side column is the landmark; its content has no landmark with the same
  name (the form is "Paper order of <symbol>"). The page reads the paper account with `PaperAccountFeed`
  of `paper_trading` and the running forward tests with
  `ForwardTestsOnInstrumentsFeed` of `forward_test` (the one
  `/ws/forward-tests` feed: `forwardTests`, `onInstruments`, `isConnected`;
  the forward test page uses it for its list and the strategy page for
  its Stop forward test button; the home page uses the
  same paper account feed). While a socket is not connected, the panel and
  the column show `LiveUpdatesNotification`.
- The home page (`/`, [#108](https://github.com/Mano-Liaoyan/ATrade/issues/108))
  is the account overview workbench. The left `SideColumn` "Watchlist"
  (22rem: the 20rem of the instrument page and 2rem for the Delete column, so
  both tables have the same column widths) has the same watchlist table as the instrument page
  (`src/routes/InstrumentWatchlist.svelte`), with `editable`: the instrument
  search above the table adds an instrument, and each row has a Delete icon
  button. A row opens its instrument page. The main area has the key numbers
  of the paper account in one `MetricRow` of `MetricTile`s
  (`foundation/metric_tile`, values from `listBalanceMetrics` of `paper_trading`,
  and the account check status when the check did not pass), over a
  `PanelSplit` with the "Positions" panel and the "Orders" panel (tabs Open
  orders and Filled today). The tables are the same components as on the
  instrument page (`PositionTable`, `OpenOrderList`, `FilledManualOrderList`),
  and the row menu of an open order cancels it. The home page has no paper
  order form: paper orders are sent on the instrument page.
- `foundation/carbon` `Checkbox` is the Carbon checkbox: `label`, `checked`,
  `onCheckedChange`, and `hideLabel` (the label is for screen readers only).
  The native checkbox is transparent and covers the label, so a pointer
  click goes to the native checkbox.
  A `DataTable` column with `isSelection` is the column of the row
  checkboxes. Its cells have class `cds--table-column-checkbox`. `TextInput`
  also takes `type` `date`. `InlineNotification` has `label` (the accessible
  name of the status or alert).
- The backtest page (`/backtests/<id>`, spec #99, ticket
  [#104](https://github.com/Mano-Liaoyan/ATrade/issues/104)) is a workbench
  like QuantConnect: the "Backtests" `SideColumn` with the backtest list
  (`DataTable` with a selection column and the Carbon batch action bar
  "Compare") and the "New backtest" and "Backtest limits" dialogs; the
  backtest panel (header line, `KeyMetricRow`, `EquityDrawdownChart`) over
  the Trades / Orders / Logs panel. `/backtests` opens the newest backtest
  (docs/architecture/backtest.md section 10.6). A backtest status is a
  `StatusIndicator` (`findBacktestStatusKind` of `backtest`). The equity and
  drawdown chart reads only Carbon tokens: `--cds-layer-01` (background),
  `--cds-text-secondary` (text), `--cds-border-subtle-01` (grid, and the line
  between its 2 panes), `--cds-text-primary` (first equity curve, solid),
  `--cds-interactive` (second equity curve, dashed), `--cds-layer-accent-01`
  (interruptions), and `--cds-support-error` (drawdown line, and its fill
  with alpha).
- The comparison pages (`/backtests/<id>/comparison/<other id>` and
  `/forward-tests/<id>/comparison/<backtest id>`, ticket
  [#109](https://github.com/Mano-Liaoyan/ATrade/issues/109)) are workbenches
  with the structure of the backtest page. The side column is the list of
  the backtest page ("Backtests", both compared rows have the open row color:
  `comparedBacktestIds` of `BacktestList`) or of the forward test page
  ("Forward tests"). The comparison panel has the header line (name, strategy
  link, instrument link and bar period; the backtest comparison shows these 2
  only when both backtests have the same; the forward test comparison also
  has the backtest status), `ComparedKeyMetrics` of `backtest`, and
  `EquityDrawdownChart` with 2 curves. The chart panel has a minimum of
  256px (160px on the other pages), and in a low panel the metric rows scroll
  in their region "Compared metrics" with a visible track. The panel
  under it has the tabs Code difference (backtests, `CodeDiff` with `fill`)
  or Fills / Logs (forward test: `FillComparisonTable` and the backtest
  error). `ComparedKeyMetrics` (`tests: ComparedTest[]`) shows one
  `KeyMetricRow` for each test, under a line with the curve line style and a
  link to the test. This line is the only key of the curves. `readKeyMetrics`
  takes `metrics: null` (all tiles "–") and an optional `period`: only the
  trades in the period count for the win rate.
- `foundation/metric_tile` has the one metric tile of all pages: `MetricTile`
  (`name`, `text`, `change`) is a Carbon tile with the name and the
  right-aligned value (tabular numbers). With `change`, the value is a
  `ChangeText`, so up and down show an arrow icon and a support color.
  `MetricRow` (`label`, `columns`) puts the tiles in one line, each the same
  width, or with `columns` in that many columns (the narrow order panel). The
  key metrics of a backtest or a forward test use `KeyMetricRow` of
  `backtest`: one set, one order, and one sign rule (the max drawdown is a
  negative percent). `formatPercent` of `backtest`, the watchlist, and the
  instrument header line use `formatSignedPercent` of `foundation/value_format`
  ("+0.97 %": the sign rule of `formatSignedNumber` and a space before "%"). Rules for each page that shows a metric:
  `formatMaxDrawdown` of `backtest` gives the max drawdown text (a negative
  percent, "0.00 %" for 0) and the signed number; a tile gives that number as
  `change`, so the max drawdown shows with `ChangeText` (down arrow and
  `--cds-support-error`). Total return and net profit also are `change`
  values. Other metrics have no direction.
- `EquityDrawdownChart` of `backtest` (`curves`, `label`, `interruptions`,
  `fill`) is the one equity and drawdown chart of all pages. Each curve
  (`DrawdownCurve`: `name`, `points`, `startCapitalUsd`) has an equity line
  and a drawdown curve; the second curve is dashed (`readCurveStyle`). The
  chart has no curve legend: `InterruptionList` lists the interruptions (grey
  columns) under it. An interruption without an equity point of a curve (a
  forward test has no records in it) gets one grey column at its end time
  (`findInterruptedTimes`); an interruption after the last equity point (it
  still lasts) gets its column at the right edge. The drawdown axis is a
  percent and ends at 0 at the top of its pane (`findDrawdownScaleRange`, no
  top margin), so the drawdown fill draws nothing above 0. New points of the same curves do not reset the zoom.
- Consistency rules of all workbench pages (ticket
  [#110](https://github.com/Mano-Liaoyan/ATrade/issues/110)):
  - The open row of a list (watchlist, backtests, forward tests, strategies)
    has the Carbon class `cds--data-table--selected`. `DataTable` gives it the
    selected row color and a 3px `--cds-border-interactive` bar at the start.
  - Table rows of size sm are 32px: `ChangeText` and `StatusIndicator` have
    `vertical-align: top`. Lists have fixed column widths and an ellipsis
    for long text; times do not wrap.
  - An empty table, list, or panel shows `EmptyText` of
    `foundation/empty_text` (`text`, optional `role` "status"): a short phrase
    without a full stop, for example "No trades". A read error shows an
    `InlineNotification` "<Thing> not read" where the data would be, also
    when no panel exists (strategy page).
  - A page that reads again while a test is queued or running uses
    `startPolling(read, onResult, intervalMilliseconds, onFailure)` of
    `foundation/polling` in an `$effect` and returns its stop function. A
    failed read shows its message (`onFailure`, or the failed result in
    `onResult`), and the loop reads again after the interval.
  - Table column names stay on one line. The instrument page has a narrow
    order panel, so its `PositionTable` and `OpenOrderList` have `compact`:
    no Currency and Market price columns, and no Type and Filled columns. The
    symbol cell of both tables shows the exchange in the helper color.
  - Percents have 2 decimal places, also the win rate ("66.67 %").
- The code editor and the code diff (`foundation/code_editor`) use Carbon
  tokens: `--cds-layer-01` (background), `--cds-text-primary`,
  `--cds-text-secondary` (gutter and comments), `--cds-border-subtle-01`,
  `--cds-layer-hover-01` (active line), `--cds-highlight` (selection), and
  `--cds-support-error` and `--cds-support-success` (removed and added
  lines). The font is IBM Plex Mono. The syntax colors in `code_colors.ts`
  are Carbon palette colors from `@carbon/colors` (70 grade in g10, 40 grade
  in g100), and plain text and comments are the `textPrimary` and
  `textSecondary` tokens of `@carbon/themes` (section 13.1). A unit test
  checks that each has 4.5:1 contrast on the `layer01` token. A live type error
  has a wavy `--cds-support-error` underline, and its tooltip looks like a
  low-contrast Carbon error notification. A type error does not block the
  save.
- The strategy page (`/strategies/<id>`, spec #99, ticket
  [#106](https://github.com/Mano-Liaoyan/ATrade/issues/106)) is a workbench
  like the QuantConnect editor. `/strategies` shows the first strategy of the
  list. `/strategies/<id>/versions/<n>` opens version n (strategy section
  9.7). The "Strategies" `SideColumn` lists the strategies (32px rows: name
  and latest version) and has the "New strategy" button (a wide `Dialog`:
  the start points on the left, the selected start point on the right, the
  name, and "Create strategy"; strategy section 9.7.1). The editor panel has
  the tabs "Rules" (the rule builder, strategy section 9.8) and
  `strategy.py`. The right `SideColumn` "AI assistant" (default 28rem) holds
  the conversation (section 25). The toolbar line (`PanelHeader`) has the strategy name, the version
  (`Select` size `sm`), and icon buttons with the state in the icon shape
  and color: Delete strategy (danger `Dialog`), the swap button (an arrow to
  the place that the editor moves to), Save version (a blue dot for unsaved
  changes), Start forward test (blue signal; a red stop square "Stop forward
  test" while a forward test of the strategy runs), and Run backtest (green
  triangle; a turning yellow icon "Backtest is running", not clickable, while
  a backtest of the strategy is queued or running). Ctrl S, Ctrl B, and Ctrl
  Shift F (Cmd on macOS) run Save version, Run backtest, and Start or Stop
  forward test, also in the editor: the editor and its language server
  client use none of these keys (a unit test checks it). Run backtest opens
  the "New backtest" dialog of the backtest page with the open strategy
  version; Start forward test opens the "New forward test" dialog of the
  forward test page with the open strategy version. Below the toolbar, a `PanelSplit` has the
  results panel and the editor panel. The results are on top by default; the
  swap button changes the order, and the browser keeps it
  (`atrade.strategy-page.pane-order`). The results panel has one tab for each
  backtest of the strategy (number and total return as `ChangeText`, the
  newest first), then Trades, Orders, and Logs of the last selected backtest.
  A backtest tab shows `KeyMetricRow` and `EquityDrawdownChart`. A backtest
  of the strategy that ends opens in its tab. While the forward test socket is
  not connected, `LiveUpdatesNotification` shows under the toolbar. The editor panel has the file
  tab `strategy.py` and the `CodeEditor`. Below the two panels is the
  "Problems and output" panel (ticket
  [#107](https://github.com/Mano-Liaoyan/ATrade/issues/107)), always the
  last panel of the split. By default it is minimized to its 24px status
  bar: the error count and the warning count (each with its icon; the code
  checks give no severity, so each code problem is an error) open the
  Problems tab, and "Output" opens the Output tab. A click on the selected
  tab or the Minimize button minimizes the panel again; the panel also
  maximizes and restores. A count of 0 has a grey icon; a count above 0 has
  the support color. A save that the checks refuse opens Problems. An error
  (a failed save, read, delete, or forward test stop) opens Output.
  Problems lists the code problems of the last save (line and message); a
  click on a problem puts the cursor on its line (`CodeEditor`
  `revealLine`). Output lists the save results, the backtests that start
  and end, the forward tests that start or get a stop request, and the
  errors of these actions, each line with its UTC time. Each tab scrolls in
  its own `ScrollRegion` ("Code problems", "Output").
- `Button` sizes `sm` and `md` also write `cds--layout--size-<size>`: Carbon
  v11 reads the button height from that class.
- `foundation/value_format` shows API values in tables: `formatBarPeriod`
  ("1-MINUTE" as "1 min", "1-DAY" as "1 day") and `formatAmount` ("98,765.40").
  `formatPrice` (1234.5 as "1,234.50") and `formatSignedNumber` (the one sign
  rule for a change: "+1.26", "-1,234.50", "0.00") show "–" for a missing
  value. `ChangeText` (`value`, `text`, `label`) shows each up or down change
  on all pages: the text with an arrow icon and `--cds-support-success` (up)
  or `--cds-support-error` (down), so the color is never the only sign.
  `foundation/time_format` shows a UTC time as "2026-01-02 03:04:05 UTC".
- The app shell header shows the server time and updates it every second:
  the `time_utc` of `GET /api/health` plus the browser time since the answer
  (`foundation/backend_health`).
- Chart times are UNIX timestamps, not date strings. This keeps the browsers
  consistent.
- New pages and parts of the map #129 (section 20.1):
  - The screen page `/screens/<id>` is a workbench
    (`docs/architecture/screen.md` section 24.10). `#lib/screen` holds its
    HTTP client and parts.
  - The backtest page gets a robustness row under `KeyMetricRow`, a Metrics
    tab, and one vertical line at the split time on the equity chart (phase
    1). A multi-instrument backtest gets an Instruments tab and a Symbol
    column in Trades (phase 3) (`docs/architecture/backtest.md` section 10).
    The key metric order is: Total return, Net profit (USD), Max drawdown,
    Sharpe ratio, Win rate, Trades, Final equity (USD).
  - The parameter sweep page `/sweeps/<id>` (phase 3) is a workbench with
    the structure of the backtest page: the "Parameter sweeps" `SideColumn`,
    a top panel with the status line and the point chart or the heat map,
    and the "Runs" panel. Heat map cells use a Carbon sequential color and
    show their value as text.
  - The forward test start dialog has "Instruments" (one instrument, top N by
    trading value, watchlist), "Capital (USD)", and "Unallocated: <amount>
    USD". The forward test page has an "Instruments" tab, a "Symbol" column
    in "Fills", and the split adjustment rows. The paper trading Positions
    table has an "Owner" column, "Unattributed: <n>" with a warning icon, and
    the "Split check needed" row with "Apply split <ratio>" and "Keep
    ledger" (phase 3, sections 11 and 12).
  - A settings page has the "Source order" list of the bar sources
    (`docs/architecture/market_data.md`). Its route and the place of the HK
    instrument list editor are left to the implementation.
  - A survivorship bias warning (icon, word, and warning color) shows on HK
    screens, on HK backtest results, and on US backtest results that start
    before 2018-05-01.
  - `foundation/carbon` gets the message components of the AI assistant,
    rewritten from the Carbon `ChatLog`, `ChatMessage`, and `ChatDivider`
    (Apache-2.0 header in each file, `THIRD_PARTY_NOTICES.md` in the
    repository root). `ASSISTANT_SOCKET_MESSAGE_MODELS` is the model list of
    `/ws/assistant`.
    The components ([#187](https://github.com/Mano-Liaoyan/ATrade/issues/187)):
    - `ChatLog` (`label`): a `ScrollRegion` with `role="log"` and `fill`
      around an `<ol>` of messages and dividers.
    - `ChatMessage` (`from`: `me` aligns to the end, `them` to the start;
      `author`, which only screen readers announce; `continued`;
      `streaming`, a caret while the text arrives; `typing`, the typing
      indicator in place of the text; `typingText`, its screen reader text).
    - `ChatDivider` (`label`, for example the date).
    - `arrangeChatLog(messages)` (`chat_log.ts`) changes messages with
      `author` and `sentAtUtc` into entries: a divider (`dateUtc`) before
      the first message of each UTC date, and each message with
      `continued` when the message before it on the same date has the same
      author.
    - The bubble colors are the Carbon v11 chat tokens
      (`--cds-chat-bubble-user`, `--cds-chat-bubble-agent`, and their text
      and border tokens). `@carbon/styles` 1.118.0 has no chat log styles,
      so each component has its own CSS with Carbon tokens only.

### 13.1 Browser behavior

- Safari, Firefox, Chrome, and Edge (latest desktop versions) must behave the
  same.
- When page scrolling is off, each region that can overflow must have its own
  visible scroll track and thumb. Safari can hide native scrollbars, so use
  styled tracks where reachability matters.
- No content can be clipped or unreachable.
- Colors come from the Carbon tokens (`--cds-*`) of the current theme
  (section 13). Do not hard-code a color. Extra CSS for parts that Carbon
  does not supply uses only Carbon color tokens, spacing tokens, and type
  tokens.
- The Carbon reset removes all margins. Extra CSS sets the margins with
  Carbon spacing tokens. The app has no other color tokens than `--cds-*`.
- A canvas chart reads a `--cds-*` token with `getComputedStyle`. The browser
  gives the Carbon value of the current theme.
- Exception: Carbon has no syntax color tokens. The CodeMirror highlight
  style needs one color value for each syntax role, so
  `foundation/code_editor/code_colors.ts` imports the colors from the
  official Carbon packages `@carbon/colors` and `@carbon/themes`. It has no
  color literal.

## 14. Deployment and external access

Sources: [Deployment platform and external protection research](https://github.com/Mano-Liaoyan/ATrade/issues/33),
[External access through Cloudflare](https://github.com/Mano-Liaoyan/ATrade/issues/73).

One Docker Compose project on the user's own server runs all services:

| Service | Content |
|---|---|
| `postgres` | PostgreSQL. All ATrade data. |
| `ib-gateway` | `ghcr.io/gnzsnz/ib-gateway:stable`, pinned by digest, `TRADING_MODE=paper`, `EXISTING_SESSION_DETECTED_ACTION: primary`. |
| `web` | `app/web.py`, backtest child processes, basedpyright processes. Memory limit, read-only root file system, writable `/tmp`. |
| `forward-test` | `app/forward_test_worker.py` and the forward test child processes. |
| `assistant` | The Node.js process with the pi SDK (section 25). Image from `deploy/assistant.Dockerfile`. Read-only root file system, writable `/tmp`, `mem_limit: ${ATRADE_ASSISTANT_MEMORY_LIMIT}` (default `1g`), volume `atrade-assistant-pi` on `/data`, networks `atrade-assistant-internal` and `atrade-assistant-egress`. No published port, no `env_file`, no `DATABASE_URL`, and no IBKR settings. |

External access (#73). The user's existing network already has these parts.
ATrade adds no Compose service for them:

```
browser -> Cloudflare (proxy, Access) -> Nginx Proxy Manager (other host) -> Tailscale -> web (server Tailscale IP:ATRADE_WEB_PORT)
```

- The DNS record of the Web host name is proxied by Cloudflare. The SSL/TLS
  mode is Full (strict).
- Cloudflare Access denies all access by default. One Allow policy includes
  only the user's email address. The login method is the GitHub identity
  provider. The user logs in to GitHub with a passkey. The session duration
  is 1 month. Cloudflare Access has no passkey login of its own.
- The Log out link in the header (section 13) opens
  `/cdn-cgi/access/logout`. This ends the Access session, not the GitHub
  session.
- Nginx Proxy Manager (NPM) runs on a different host in the user's tailnet.
  One proxy host sends the Web host name to
  `http://<server Tailscale IP>:<ATRADE_WEB_PORT>`
  with WebSocket support on (market data, the language server).
- Only Cloudflare can connect to NPM: the firewall of the NPM host lets only
  the Cloudflare IP ranges connect to port 443. Without this rule, a request to
  the IP address of the NPM host bypasses Cloudflare Access.
- On the server, `ATRADE_WEB_BIND_ADDRESS` is the Tailscale IP address of
  the server. Only devices in the tailnet can connect to it, and the tailnet
  policy decides which ones. A host firewall does not do this job: Docker
  publishes ports with its own packet filter rules, which firewalld does not
  check. The server sets `net.ipv4.ip_nonlocal_bind = 1`, so Docker can bind
  the address also before Tailscale is up after a restart. The default
  `127.0.0.1` keeps a development machine closed.
- Only the Web host name is published. The Gateway port and the PostgreSQL
  port are not published.
- The Cloudflare cost is 0 USD per month (Zero Trust Free plan).
- `./start run` calls `docker compose up`. It is the only start command.

### 14.1 Compose file and the `web` service

- The Compose file is `deploy/compose.yaml`. `./start run` runs
  `docker compose --file deploy/compose.yaml --env-file .env up --build`, and
  sends its other arguments to `docker compose up`. When `.env` is not there,
  it writes a warning and uses `.env.example`.
- The image of `web` comes from `deploy/web.Dockerfile`. A Vite+ stage
  (`ghcr.io/voidzero-dev/vite-plus`) builds the SPA with `adapter-static`. The Python stage installs the backend with
  `uv sync --frozen --no-dev` and copies the built files to
  `/app/frontend-build`.
- `web` serves the built frontend from FastAPI. There is no separate web
  server. A catch-all route in `app/frontend_files.py` returns the requested
  file when it exists in the build directory. For every other path it returns
  the SPA fallback page `200.html`. Paths under `/api/` and `/ws/` never get
  the fallback page: they return `404`. A path that resolves outside the build
  directory gets the fallback page, never the file. Each frontend file
  response has `Cache-Control: no-transform`, so Cloudflare does not inject
  its Web Analytics script into the pages.
- At start, `web` runs the Alembic migrations, then starts uvicorn with
  1 worker on port 8000. Compose publishes it on
  `${ATRADE_WEB_BIND_ADDRESS}:${ATRADE_WEB_PORT}` (default
  `127.0.0.1:8000`).
- `web` has `read_only: true`, a `tmpfs` on `/tmp`, and
  `mem_limit: ${ATRADE_WEB_MEMORY_LIMIT}` (default `4g`; phase 3 changes it
  to `8g`, because a multi-instrument backtest of 500 instruments on 1-hour
  bars can need 4 to 5 GB,
  [#142](https://github.com/Mano-Liaoyan/ATrade/issues/142)). `0` turns the memory
  limit off. Use `0` only on a host that cannot set memory limits, for example
  rootless Podman without the memory cgroup controller.
- `postgres` uses the image `postgres:18.3` and the new volume
  `atrade-postgres18-data` (section 19). Its port is not published.
  PostgreSQL keeps the password of the first start in the volume. When
  PostgreSQL refuses the password, `web` writes one line that names the
  volume and stops (`check_database_password` in `app/web.py`).
- Before Compose starts, `./start run` checks the env file. It stops with a
  message when `ATRADE_POSTGRES_PASSWORD` is not set in the env file or in the
  process environment. It writes a warning for each variable of the old stack
  (for example `ATRADE_API_HTTP_PORT`, `ATRADE_IBKR_PAPER_ACCOUNT_ID`). The
  test is `backend/tests/app/test_start_script.py`.
- Services added later (`ib-gateway`, `forward-test`) must not
  block the local start when their credentials are missing. They fail with a
  clear message, or they are in a Compose profile. `ib-gateway` is in the
  profile `ibkr` (section 7.4).
- `forward-test` uses the image of `web` with the command
  `python -m atrade.app.forward_test_worker`. It has the same read-only root
  file system and `/tmp`, the database URL, and the IBKR settings, but not
  `ATRADE_IBKR_USERNAME` or `ATRADE_IBKR_PASSWORD`. It waits until the
  health check of `web` passes, because `web` runs the migrations. It starts
  also without IB Gateway: a forward test start then fails with the reason
  in its `error_message` (#76). From phase 3, `forward-test` also gets
  `ATRADE_IBKR_BAR_FETCHER_CLIENT_ID` and `DATABENTO_API_KEY`, and needs
  outbound HTTPS to Databento. IB Gateway then has at most 8 API clients:
  Web 1, forward tests 10 to 13, bar fetcher 20, contract tests 98 and 99.
  The limit is 32.
- The AI assistant (phase 2, section 25) adds 2 networks.
  `atrade-assistant-internal` has `internal: true` and the fixed subnet
  `172.31.250.0/24`, and only `web` and `assistant` are in it.
  `atrade-assistant-egress` has only `assistant`. `assistant` is not on the
  default network, so it cannot connect to `postgres` or `ib-gateway`. `web`
  is on the default network and on `atrade-assistant-internal`. `web` also
  listens on port 8001 in `atrade-assistant-internal`. Compose does not
  publish port 8001.
- `assistant` uses the image of `deploy/assistant.Dockerfile`: a Vite+ stage
  installs the production dependencies of `assistant/`, and a
  `node:24.13.0-slim` stage runs `node src/main.ts` as the user `node`.
  `assistant` listens on port 8002 in `atrade-assistant-internal`. Its
  Compose health check calls `GET /health` on that port. `assistant` has no
  `depends_on`: it starts also when `web` is not ready.
- Disk: plan about 4 GB more in PostgreSQL for the Databento daily bars and
  the universe hourly bars (estimate, #141).

### 14.2 Deployment from GitHub Actions

- `.github/workflows/deploy.yml` runs after a successful CI run of a push to
  `main` of this repository, and when started by hand on `main`. One
  deployment runs at a time.
- The job uses the GitHub environment `production`. Its deployment branch
  rule allows only `main`. Its secrets are `ATRADE_TAILSCALE_CLIENT_ID` and
  `ATRADE_TAILSCALE_AUDIENCE` (a Tailscale federated identity),
  `ATRADE_DEPLOY_HOST` (the Tailscale address of the server),
  `ATRADE_DEPLOY_PORT`, `ATRADE_DEPLOY_USER`, `ATRADE_DEPLOY_SSH_KEY` (a
  private key that is used only for deployment), and
  `ATRADE_DEPLOY_KNOWN_HOSTS` (the host key line of the server).
- The runner joins the user's tailnet with `tailscale/github-action` and
  workload identity federation: GitHub gives the job an OIDC token, and
  Tailscale accepts only the subject
  `repo:Mano-Liaoyan/ATrade:environment:production`. GitHub stores no
  Tailscale secret that works alone. The node is ephemeral and has the tag
  `tag:atrade-deploy`. The tailnet policy lets this tag connect only to
  `tcp:22` of the server. The server has no public SSH port.
- The runner connects to the server with OpenSSH through Tailscale, not with
  Tailscale SSH, because Tailscale SSH does not read `authorized_keys`. It
  sends only the commit SHA.
  In `authorized_keys` on the server, the deploy key has
  `restrict,command="<checkout>/scripts/deploy"`. The key can run nothing
  else.
- `scripts/deploy` accepts only a full SHA of a commit on `origin/main`. It
  stops when `.env` is not there. It checks out the commit (detached HEAD),
  then runs `./start run --detach --wait`. The server builds the images. The
  build is the production build: `vp build` for the SPA, `uv sync --no-dev`,
  and uvicorn with 1 worker. The test is
  `backend/tests/app/test_deploy_script.py`.
- `.env` stays on the server (section 15). GitHub has no ATrade secrets.
- A deployment recreates `web` and `forward-test` when their image changes.
  The worker restarts the running forward tests (section 12.7).

## 15. Secrets and configuration

Sources: [Secret management research (Enpass first)](https://github.com/Mano-Liaoyan/ATrade/issues/35),
[Secret plan after one year](https://github.com/Mano-Liaoyan/ATrade/issues/59).

- The program reads secrets only from environment variables.
- Docker Compose loads the environment variables from `.env`.
- Git contains only `.env.example`, with variable names and placeholder values.
  `.env` is in `.gitignore`.
- The user keeps the secret values in Enpass and saves `.env` by hand on each
  machine. On the server, copy `.env` with `scp` and set `chmod 600`.
- A different secret tool can make `.env`, for example 1Password with
  `op inject`. A change of tool does not change the architecture.
- The repository stays public. A private repository does not replace these
  rules, because secrets still must not go into git.
- Real IBKR checks use the local `.env` values. They skip cleanly when the
  local runtime is not available.

Settings that `foundation/settings` reads:

| Setting | Meaning |
|---|---|
| `trading_mode` (`ATRADE_TRADING_MODE`) | `paper` or `live`. `live` stops the start in this stage. |
| `ibkr_account_id` (`ATRADE_IBKR_ACCOUNT_ID`) | Expected IBKR account number. Empty means not configured. |
| `ibkr_host`, `ibkr_paper_port` (`ATRADE_IBKR_HOST`, `ATRADE_IBKR_PAPER_PORT`) | Where the Web process and forward tests connect. Default `ib-gateway:4004`. |
| `ibkr_web_client_id` (`ATRADE_IBKR_WEB_CLIENT_ID`) | Default `1`. |
| `forward_test_client_id_first`, `forward_test_client_id_last` (`ATRADE_FORWARD_TEST_CLIENT_ID_FIRST`, `_LAST`) | Default `10–13`. |
| `local_paper_capital_usd` (`ATRADE_LOCAL_PAPER_CAPITAL_USD`) | Used when IBKR is not connected. Default `100000`. |
| `database_url` (`DATABASE_URL`) | PostgreSQL connection. |
| `ibkr_bar_fetcher_client_id` (`ATRADE_IBKR_BAR_FETCHER_CLIENT_ID`) | Phase 3. Client ID of the bar fetcher in `forward-test`. Default `20`. |
| `databento_api_key` (`DATABENTO_API_KEY`) | Phase 3. Secret. The Databento API key for the quarterly universe update and the history import. Empty means not configured: the quarterly update then does not run and logs the reason. |

Settings refuse client ID 0, client IDs that are multiples of 1000, a range
that ends before it starts, a Web client ID inside the forward test range,
and a bar fetcher client ID inside the forward test range or equal to the
Web client ID.
`ATRADE_IBKR_USERNAME`, `ATRADE_IBKR_PASSWORD`,
`ATRADE_IBKR_AUTO_RESTART_TIME`, and `ATRADE_IBKR_TIME_ZONE` are not settings:
only the `ib-gateway` service reads them (section 7.4).

Environment variable names: `DATABASE_URL` has no prefix, because the backtest
child process gets it by this name (section 10). `DATABENTO_API_KEY` has no
prefix, because the decision
[#146](https://github.com/Mano-Liaoyan/ATrade/issues/146) names it so and
the user kept that name. All other settings use the prefix `ATRADE_`, for example `ATRADE_TRADING_MODE`. `foundation/settings`
also reads `ATRADE_FRONTEND_BUILD_DIR` (default `/app/frontend-build`, the
path in the `web` image). Compose builds `DATABASE_URL` from
`ATRADE_POSTGRES_PASSWORD`. The ticket that first uses a setting adds it to
`foundation/settings` and to `.env.example`.

The backtest timeout and concurrency are not in `settings`. PostgreSQL stores
them (section 10).

`ATRADE_WEB_MEMORY_LIMIT` and `ATRADE_ASSISTANT_MEMORY_LIMIT` are not
settings: only Compose reads them (section 14.1). `.env.example` lists both.
The `assistant` container gets neither of them, and no other value of
`.env`.

Exception ([ADR 0005](adr/0005-assistant-credentials-outside-postgresql.md)):
AI assistant credentials (subscription logins and API keys) come from the
web UI. The `assistant` service keeps them in a `0600` file in the volume
`atrade-assistant-pi`, not in environment variables, PostgreSQL, or `.env`.
A backup of this volume holds credentials and must be kept like `.env`.

## 16. Readability rules

Sources: [Readability rules](https://github.com/Mano-Liaoyan/ATrade/issues/36),
[Readability rules for Python and TypeScript](https://github.com/Mano-Liaoyan/ATrade/issues/51).
The full examples, the linter configuration, and the code review list
are on branch
[`task/readability-linter-config`](https://github.com/Mano-Liaoyan/ATrade/tree/task/readability-linter-config/docs/readability-linter)
(commit `d8a3374`). The first implementation PR copies that configuration.

Each rule has a check type. `[tool]` means a linter checks it in CI.
`[review]` means a reviewer answers a yes/no question.

### A. Length and complexity

| Rule | Check | Python | TypeScript / Svelte |
|---|---|---|---|
| A1 Cyclomatic complexity at most 10 | tool | ruff `C901` | `complexity` |
| A2 Nesting at most 4 levels. Use guard clauses. | tool | ruff `PLR1702` (the only preview rule turned on) | `max-depth` |
| A3 At most 5 parameters. Above 3, use named arguments or one named object. | tool | ruff `PLR0913`, `PLR0917` | `@typescript-eslint/max-params` |
| A4 At most 50 statements per function | tool | ruff `PLR0915` | `max-statements` |
| A4 At most 1000 lines per file | tool | one `find` + `awk` command in CI | `max-lines` |
| A5 Above about 40 lines per function or 400 per file, check if a split hides real complexity. Do not split only to meet a line count. | review | | |

Cognitive complexity is not checked. A1 and A2 limit it.

### B. Names

- B1 `[review]` Use full English words. Only a fixed list of abbreviations is
  allowed, for example `id`, `url`, `ibkr`.
- B2 `[review]` Domain names must match `GLOSSARY.md`.
- B3 `[review]` Function names are verb + noun.
- B4 `[review]` Boolean names start with `is`, `has`, or `can`.
- B5 `[review]` Names of money, time, and quantity values include the unit or
  currency, for example `timeout_seconds`, `price_usd`, `quantity_shares`.
- B6 Do not use empty names: `data`, `info`, `manager`, `helper`, `utils`,
  `handle`, `process`. TypeScript: `[tool]`
  `@typescript-eslint/naming-convention`. Python: `[review]`.

### C. Abstraction depth

- C1 `[review]` At most 3 levels from an entry point to an external system:
  entry point -> capability function -> external system adapter.
- C2 `[review]` Do not make an interface with only one implementation.
  Exception: external system boundaries (broker, data source, clock, database).
  These need an interface, because tests replace them.
- C3 `[review]` Do not write your own inheritance. When a framework requires
  it (for example NautilusTrader `Strategy`), use only 1 level.
- C4 `[review]` Pass dependencies as arguments. No dependency injection
  container. `app/` creates and connects all dependencies by hand.

### D. Comments

- D1 `[review]` Each file starts with 1 to 3 lines that say what the file does.
- D2 `[review]` Comments say only "why": trade-offs, external limits, business
  rules that are not obvious. An external limit needs a link.
- D3 `[review]` Do not write comments that repeat the code.
- D4 Do not commit commented-out code. Python: `[tool]` ruff `ERA001`.
  TypeScript: `[review]`.
- D5 A `TODO` must have an issue link. Python: `[tool]` ruff `TD003`.
  TypeScript: `[review]`.

### E. Forbidden techniques

- E1 `[review]` No metaprogramming, reflection, `eval`, or code generation at
  run time.
- E2 `[review]` No decorators or annotations that change function behavior.
  Framework decorators are allowed, for example route decorators.
- E3 `[review]` No operator overloading.
- E4 `[review]` No custom DSL and no fluent chained API.
- E5 `[review]` No global mutable state and no singletons.
- E6 `[review]` No nested ternary expressions. At most one chained
  transformation per line. Name the intermediate values.
- E7 `[review]` No currying, no point-free style, no monad-style error
  handling.
- E8 `[review]` Do not use exceptions for normal control flow.
- E9 `[tool]` No implicit type conversion and no magic numbers. Use named
  constants. Python: ruff `PLR2004`, basedpyright strict. TypeScript:
  `no-magic-numbers`, `no-implicit-coercion`, `strict-boolean-expressions`
  with `allowNumber` and `allowString` off. Test files are not checked for
  magic numbers, because tests assert exact values.

### F. Directory structure

- F1 `[review]` Top-level directories are capabilities, plus `app/` and
  `foundation/`. Do not make directories for technical layers, for example
  `controllers/`, `services/`, `repositories/`.
- F2 `[tool]` Each capability has one public entry file. Python: import-linter
  `protected`. TypeScript: `#lib/*` maps only to `index.ts`, and
  `no-restricted-imports`.
- F3 `[tool]` Dependencies go in one direction, with no cycles. Python:
  import-linter `layers`. TypeScript: `no-restricted-imports` (section 13).
- F4 `[review]` Each `foundation/` module has a name that says its purpose. Do
  not make `utils/`, `common/`, or `shared/`.
- F5 `[review]` At most 3 directory levels under `src/` (backend: under
  `atrade/`).
- F6 `[review]` Frontend unit tests are next to the code they test. Backend
  tests are in `backend/tests/<capability>/` (section 17).
- F7 `[tool]` A linter checks the dependencies between capabilities.

### G. Exceptions

- G1 `[review]` When code must break a rule, write
  `readability-exception: <reason>` at that place. The reviewer must accept the
  reason.
- Example: NautilusTrader 2.0 stubs type `submit_order` `params` as a bare
  `dict | None`. Add `# pyright: ignore[reportUnknownMemberType]` with a
  `readability-exception` at the call. When one module needs more than 3 of
  these, turn off `reportUnknownMemberType` for that module only.

The linters check test code too (`backend/tests/`, `*.test.ts`,
`frontend/e2e/`).

## 17. Testing

Source: [Test method](https://github.com/Mano-Liaoyan/ATrade/issues/39).

### 17.1 Tools

| Scope | Tool |
|---|---|
| Backend | pytest with the AnyIO plugin (`@pytest.mark.anyio`) and `httpx.AsyncClient` with `ASGITransport`. Do not use the synchronous `TestClient`. |
| Frontend unit and component | Vitest and `@testing-library/svelte`. |
| End to end | Playwright with 4 projects: chromium, firefox, webkit, msedge. |

### 17.2 What to test

- Tests call each capability through its public entry and its HTTP routes.
  Do not test internal functions. Exception: internal functions with real
  complexity, for example IBKR paging.
- Backtests: the repository holds small generated bar files and one simple
  test strategy. Tests assert exact result values.
- There is no coverage percentage. The review question is: "Does each new
  public behavior have a test?"
- Test names describe behavior, for example
  `test_rejects_backtest_without_paper_capital`.
- Repeated setup code is allowed. Fixtures are only for the database
  connection, fakes, and the clock. No layers of test helpers.

### 17.3 External dependencies

- IBKR: a hand-written fake with the same functions as the `ibkr` public
  entry. It keeps data in memory and comes in as an argument. Do not use
  `unittest.mock.patch`. Do not record and replay.
- Contract tests: one test file runs the same assertions against the fake and
  against the real paper account. CI runs only the fake.
- Real IBKR tests have the pytest mark `ibkr_paper`. The user runs them by
  hand. They skip when `.env` or IB Gateway is not available.
- PostgreSQL: a real PostgreSQL with the production image. Tests run the
  Alembic migrations at start and `TRUNCATE` before each test.
- Time: `foundation/clock` comes in as an argument. Tests pass a clock with a
  fixed time. Do not use `freezegun`.
- Databento: a hand-written fake in `tests/fakes/databento.py`. No real
  Databento call in CI.
- Model providers: the `assistant` service tests use a local fake
  OpenAI-compatible model server. No real provider in CI.

### 17.4 Tests for specific parts

- Backtest child process:
  - A strategy loops forever in `on_bar`, with a 2 second timeout. Assert the
    status "timed out" and that the child ended.
  - A strategy writes `os.environ` to the log. Assert that no IBKR variable is
    in the log.
  - With concurrency 1, assert that the second backtest waits in the queue.
  - The memory limit has no automatic test. Check it by hand in Compose before
    each release.
- Forward test worker loop (state comparison, ID allocation, restart count,
  end time): CI with real PostgreSQL. The function that starts a child process
  comes in as an argument. Tests pass a fake.
- Record `DataActor`: CI runs it with the test strategy in the NautilusTrader
  backtest engine on the small bar files. Assert the exact table content.
- IB execution client (`ibkr_paper` contract test, by hand):
  - Send a limit order far from the market price.
  - Assert that the Web `reqAllOpenOrders` sees it and reads the forward test
    ID from `orderRef`.
  - Stop the forward test. Assert that the order is cancelled.
  - Stop the child with `kill -9`. Assert that it restarts with the same client
    ID and cancels the old order on stop.
- The contract tests must check whether `reqExecutions` and
  `reqCompletedOrders` read filled orders of other client IDs. Run this check
  on the paper account during US market hours.
- Indicators (phase 1): each indicator has a consistency test (the screen
  path and a NautilusTrader engine run with `register_indicator_for_bars`
  give equal values and equal "no value" for the same bars), a no-value test
  (no `0.0` before the warm-up end), and for ATrade-written indicators a test
  with known values (section 23.5).
- Metric functions (phase 1): exact values on fixed equity curves and trades
  for each metric of backtest section 10.9, PSR and DSR against
  hand-calculated values, the trial count, and the out-of-sample use count.
- Rule builder (phase 1): for each rule template and for empty rules, the
  code from the rules passes the checks of strategy section 9.3. The same
  rules give the same code. The append-only trigger refuses an `UPDATE` of
  `rules`. Each rule template runs on the single-instrument backtest.
- Port 8001 app (phase 2): a unit test asserts that its routes are exactly
  the allow-list of section 25. A test asserts `403` on port 8000 for a
  request from the assistant subnet. A test asserts that a save on port 8001
  records the source `assistant` and the conversation ID.
- Market data (phase 3): the source order merge rule, the Databento import
  (price rules, 7 regular-hours hourly bars, split and symbol link
  detection), the quarterly universe (63-day ranking, retry and fallback
  day), the HK instrument list routes, the daily bar update, and the change
  of the stored bars at a stock split.
- Screens (phase 3): HTTP tests of `/api/screens` and `/api/screen-results`
  with saved daily bars. They check the 2 steps, the exclusion reason "no
  value", the `422` problem list, and the `403` of `PUT` on port 8001 for a
  screen that the user saved or kept.
- Parameter sweep (phase 3): the AST reader finds only the `int`, `float`,
  and `bool` fields with a type annotation and a default, and does not
  import the code. A grid of more than 200 runs or more than 3 parameters
  gets `422`. A cancel sets the queued runs to `cancelled`.
- Multi-instrument backtest child (phase 3): a real child process runs a
  universe on one `SMART` venue with one cash account. The test asserts the
  exact trades, the members of each period, and that the strategy gets no
  list before its period.
- Owner ledger (phase 3, CI with real PostgreSQL): a sell larger than the
  position minus open sells, a buy larger than cash minus open buys, no
  short, the `409` of an order by hand, `OrderDenied` of a forward test
  order, the transfer to "By hand" at stop, the stock split formula, and
  "Split check needed" with apply and keep.
- ATrade execution and data clients (phase 3, CI): a LiveNode test with a
  fake IBKR connection sends an order, fills it, restarts the child, asserts
  the strategy position, then applies a stock split and asserts the position
  after the restart.

### 17.5 End to end

- Real backend and real PostgreSQL. IBKR is the fake.
- `backend/tests/e2e_server.py` builds the app with fakes. Production code has
  no fake and no fake mode switch.
- The `forward-test` service uses a fake child process start function.
  Playwright tests start, stop, the list, and the comparison page.
- Scroll regions: Playwright scrolls to the last item of each region and
  asserts that it is visible. It also asserts that the app scrollbar element is
  visible (`getByRole('scrollbar', { name: '<region label> scroll bar' })`
  of `ScrollRegion`, section 13). No screenshot comparison.
- The Playwright projects run at the same time against one database, and the
  e2e database is not cleared. A test uses names or instruments that only its
  project uses. For the watchlist, the e2e server adds the fake instruments
  `<PROJECT NAME>01` to `<PROJECT NAME>25` on `ARCA` for each project.
- WebKit is not Safari. Before each release, check a list by hand in real
  Safari.

### 17.6 File locations

- `backend/tests/<capability>/test_*.py`
- `backend/tests/fakes/`
- `frontend/src/lib/<capability>/*.test.ts`
- `frontend/e2e/*.spec.ts`

### 17.7 CI (GitHub Actions, each PR)

- Backend: ruff, basedpyright, import-linter, the file line count command,
  pytest with a PostgreSQL service container.
- Frontend: ESLint, `svelte-check`, Vitest.
- End to end: Playwright with 4 projects.
- Not in CI: `ibkr_paper`.
- `.github/workflows/ci.yml` runs `./scripts/check backend`,
  `./scripts/check frontend`, `./scripts/check assistant`, and
  `./scripts/check e2e` as 4 jobs. The backend
  and end-to-end jobs use a `postgres:18.3` service container. Local runs use
  the same script. Without `ATRADE_TEST_DATABASE_URL`, the script starts a
  temporary PostgreSQL container.
- Backend formatting: `ruff format --check` with line length 120.
- The test PostgreSQL fixture runs the migrations one time per session and
  truncates all tables except `alembic_version` before each test.

- The `assistant` service checks run in `./scripts/check assistant` (also
  in `./scripts/check` without a scope): ESLint with the readability rules,
  `tsc --noEmit`, and Vitest. The CI job is `assistant`.

### 17.8 Release checklist

Do these checks by hand before each release. Tests cannot do them.

1. Real Safari (section 17.5): open each page. Each scroll region must
   scroll and show its scroll bar.
2. Backtest memory limit (section 10.1). The kernel must stop the backtest
   child before the Web process when memory is low:
   1. In `.env`, set `ATRADE_WEB_MEMORY_LIMIT=1g`. Run `./start run -d`.
   2. Save a strategy that keeps memory in `on_bar`, for example
      `self.blocks.append(bytearray(100_000_000))`. Start a backtest of it on
      saved bars.
   3. While the backtest runs, run
      `docker compose --file deploy/compose.yaml --env-file .env exec web sh -c 'for p in /proc/[0-9]*; do echo "$p $(cat $p/oom_score_adj) $(cut -d" " -f19 $p/stat) $(tr "\0" " " < $p/cmdline)"; done'`.
      The `atrade.app.backtest_process` line must show `oom_score_adj` 1000
      and niceness 10.
   4. Wait until the backtest ends. Its status must be "Failed" with exit
      code -9. The header must still show the backend status, and
      `GET /api/health` must answer: the Web process did not stop.
   5. Set `ATRADE_WEB_MEMORY_LIMIT` back to its earlier value. Run
      `./start run -d` again.

## 18. Documentation rules

Source: [Documentation rules for the new project](https://github.com/Mano-Liaoyan/ATrade/issues/57).

- The repository root keeps 4 documents:
  - `README.md`: how to run ATrade.
  - `AGENTS.md`: rules for agents.
  - `GLOSSARY.md`: terms.
  - `THIRD_PARTY_NOTICES.md`: the source, copyright, and license of adapted
    third-party code (section 25.12.2).
- This document (`docs/architecture.md`) is the architecture specification.
  When it is longer than 1000 lines, split it by capability. A moved section
  goes to `docs/architecture/<capability>.md`, and its number stays. Section 7
  is in `docs/architecture/ibkr.md`. Section 8 is in
  `docs/architecture/market_data.md`. Section 9 is in
  `docs/architecture/strategy.md`. Section 10 is in
  `docs/architecture/backtest.md`. Section 11 is in
  `docs/architecture/paper_trading.md`. Section 12 is in
  `docs/architecture/forward_test.md`. Section 23 is in
  `docs/architecture/indicator.md`. Section 24 is in
  `docs/architecture/screen.md`. Section 25 is in
  `docs/architecture/assistant.md`.
- `docs/adr/` holds decisions that are hard to reverse.
- The plan lives only in GitHub Issues. There is no `PLAN.md`.
- There is no document index and no `active` or `obsolete` status.
- These 5 kinds of change must update the documents in the same PR:
  1. HTTP or WebSocket interfaces.
  2. Settings and `.env.example`.
  3. Module boundaries and dependency direction.
  4. Terms (`GLOSSARY.md`).
  5. Start and run commands.
- Other changes do not need a document update.
- Repository documents are in English and follow the `asd-ste100` skill.
  Issues and the planning map stay in Chinese.

## 19. Old data

Source: [Old data migration](https://github.com/Mano-Liaoyan/ATrade/issues/58).

- ATrade migrates no old data. This includes the watchlist, backtest history,
  bars, and capital snapshots.
- There is no backup and no `pg_dump`.
- The rewrite deletes the old PostgreSQL volume (`postgres-data`) and all old
  tables.
- The user adds the watchlist again in the new UI. The new system has no
  migration code.
- The rewrite uses the volume `atrade-postgres18-data`. It does not use the
  volume `atrade-pgdata` of earlier test starts. ATrade never deletes or
  changes a volume. The user removes old volumes by hand. This rule also
  covers the volume `atrade-assistant-pi` (section 25).

## 20. Implementation phases

1. Market data and backtests. This includes the watchlist and strategies.
2. Paper orders and forward tests.
3. Live orders. This is the next stage, with its own map.

### 20.1 Phases of the indicators, screens, and strategy help map

The map [Wayfinder: indicators, screens, and strategy help](https://github.com/Mano-Liaoyan/ATrade/issues/129) has its own phases. In sections 8 to 12 and 23 to 25,
"phase 1", "phase 2", and "phase 3" mean these phases.

1. The indicator library (section 23), the new metrics and the robustness
   checks (section 10), the rule builder, and the strategy templates
   (section 9). They use only the single-instrument backtest.
2. The AI assistant (section 25).
3. The data sources (section 8), screens (section 24), multi-instrument
   backtests, parameter sweeps and walk-forward (section 10), and
   multi-instrument forward tests with the owner ledger (sections 11 and
   12).

### 20.2 Limits of the first version

- The first version does not handle cash dividends. Backtests do not include
  dividends. On the paper trading page, a dividend shows as an
  "Unattributed" difference (section 11).

### 20.3 Later work

These items are in scope of the map #129, but not of phases 1 to 3:

- Multi-instrument forward tests on 1-hour bars. First measure the time to
  fetch the bars of 500 instruments.
- Scheduled runs of screens, and alerts.

## 21. Facts not yet verified

These facts come from source code, documents, or version constraints. Nobody
ran them. The implementation must check them.

| Fact | How to check |
|---|---|
| `ib_async` 2.1.0 limits `tzdata` to `<2026.0`. A later dependency can conflict with it ([ib_async#209](https://github.com/ib-api-reloaded/ib_async/issues/209)). | Watch `uv lock` on each upgrade. Upgrade to `ib_async` 3.0.0 after its release. |
| The NautilusTrader 2.0 forward test behavior in section 12 (reconciliation, `orderRef`, reconnection, `DataActor` cache reads). | The `ibkr_paper` contract tests in section 17.4. |
| `reqExecutions` and `reqCompletedOrders` read filled orders of other client IDs. | The contract test in section 17.4. |
| Daily `MIDPOINT` bars (`useRTH=False`, `formatDate=2`) of an IDEALPRO pair come as dates, one for each forex trading day (`read_daily_exchange_rates`, `docs/architecture/ibkr.md` section 7.2). Only the fake was used. | Start a backtest of an HKD instrument with IB Gateway connected, and read the `exchange_rate` rows. |
| The Gateway needs IB Key after the daily automatic restart. | Watch the phone after the first `AUTO_RESTART_TIME`. |
| The paper Gateway needs a manual login or approval each week. | Watch the first week of operation. |
| The Web connection gets live status updates for orders of other client IDs. Only the `reqAllOpenOrders` snapshot is checked. | The `ibkr_paper` contract tests. |
| Orders on the real paper account: the order cases of section 7.5 and both forward test cases of section 17.4. On 2026-10-27 they did not run to the end: the Gateway API was read-only, so IBKR refused the test order (warning 321, no open order left) and refused `reqOpenOrders` (section 7.4). The forward test cases need a `NetLiquidation` value in USD: the EUR paper account now gets it through the IBKR `EUR.USD` rate (section 21.1). | Recreate `ib-gateway` with `READ_ONLY_API: "no"`, then `uv run pytest -m ibkr_paper`. |
| The forward test LiveNode of section 12.15: the IB data client and the IB execution client use the same client ID; the venue of `SYMBOL.EXCHANGE` matches the primary exchange of IBKR; the `ClientOrderId` with `order_id_tag = FT<ID>` reaches `orderRef`; `reqOpenOrders` returns the orders of the LiveNode on a new connection with the same client ID (#76). | `uv run pytest -m ibkr_paper tests/forward_test` (`test_the_forward_test_order_shows_its_forward_test_id_and_the_stop_cancels_it`). |
| The forward test recovery of section 12.7 (#77): after `kill -9` of the child, the worker restarts it with the same client ID, the restart cancels the old order, and the stop cancels the new one. The child detects a lost IB execution client with a TCP probe of the Gateway port, because the rc7 `LiveNode` does not show the client connection state to Python. A daily Gateway restart was not watched. | `uv run pytest -m ibkr_paper tests/forward_test` (`test_after_kill_9_the_worker_restarts_with_the_same_client_id_and_cancels_the_old_order`). |
| The forward test records of section 12.8 (#78) in a real `LiveNode`: the IB bar `ts_event` is the bar end, the `DataActor` gets the bars of the strategy bar type, and `self.cache.orders(instrument_id=...)` holds the `OrderFilled` events of the IB execution client with stable `trade_id` values after a restart. Only the backtest engine run is checked (`test_forward_test_recorder.py`). | Run a forward test on the paper account, then compare `forward_test_equity_point` times with the bar ends and `forward_test_fill` with the IBKR executions. |
| `reqExecutions` returns the executions of the current day only. The filled orders by hand (section 11.4) show only those fills. | The `ibkr_paper` contract tests, during US market hours. |
| Live bars with periods other than 5 seconds use `reqHistoricalData` with keepUpToDate. Checked on a weekday outside the trading hours (section 21.1). Not checked on a weekend. | `uv run pytest -m ibkr_paper -k live_bar` on a Saturday or Sunday. |
| The account `ExchangeRate` for USD (section 11.9 of `paper_trading.md`, step 3): IBKR sends it only when the ledger holds USD, as base currency units for 1 USD. Checked only with the fake; the paper account of the owner holds only EUR. | `uv run pytest -m ibkr_paper -k balance_and_the_positions` after the account holds USD cash, and compare the panel rate with the IBKR `EUR.USD` rate. |

Facts of the map #129 (section 20.1) that the implementation must check:

| Fact | How to check |
|---|---|
| The 12-1 momentum class accepts skip 0 (#139, template S3). | Check the parameter in the indicator implementation. |
| The default parameters of the template sources (#139). | Read the method section of each paper. |
| The time to read the daily bars of all US instruments from PostgreSQL (about 10000 × 260 rows) (#136). | Run the bulk daily bar query on the real bar tables and time it. |
| The time of the IBKR daily bar update for about 500 instruments (#145). | Download the daily bars of 50 instruments and time it. |
| The run time of a backtest with a `screen` universe against the 15 minute wait of the AI assistant (#150). | Run one with real data and time it. |
| The token count of a 500-row screen result (#150). | Count the tokens of 1 real result. |
| Memory and time of a backtest of 500 instruments on 1-hour bars: about 4 to 5 GB and 15 s (estimate, #142). | Run one with real data and measure the peak memory and the time. |
| Look-back bars of many bar types in one catalog, and chunked loading memory (#131, source only). | A multi-instrument child test with look-back bars for each member. |
| Databento `ohlcv-1h` is on whole hours. The first IBKR regular-hours hourly bar starts at 9:30 ET and is 30 minutes long (#141). | Compare IBKR and Databento hourly bars of one instrument on one day. |
| NYSE American and NYSE Arca instruments have no official open and close in XNAS or XNYS `statistics` (#141). | After the daily import, count the instruments without `stat_type` 11. |
| The cost of the universe hourly bars is about 24 USD (#141). | `metadata.get_cost` before the purchase. |
| The Databento usage-based plan can download 2018 data, and the data stays usable after the account closes (#141, #144). | Download 1 instrument for 1 day. Ask Databento support about the license. |
| The time of day at which the EQUS.SUMMARY bar of the previous trading day is available (#146). | `metadata.get_dataset_range` at 06:00, 07:00, and 08:00 ET on one trading day. |
| How Databento links symbol changes, for example FB to META (#141). | Free `symbology.resolve` for FB and META. |
| IBKR scales `TRADES` volume by the split ratio (#149). | At the first stock split, read 1 year of daily bars again and compare. |
| The paper account handles stock splits (#149). | Watch the first stock split of a held instrument. |
| The ATrade execution and data clients in a real LiveNode: reconciliation from owner reports, no repeated buy after a restart (#146). | The LiveNode test of section 17.4, then the `ibkr_paper` forward test contract test. |
| IBKR does or does not refuse opposite orders of 2 owners on one instrument (self-trade prevention) (#146). | 2 client IDs on the paper account place an AAPL buy and a sell, first with prices that do not cross, then with prices that cross. |
| Real subscription logins and model calls through the pi SDK `ModelRuntime.login()` (#133, #140). Only a fake model server was run. | Log in with each provider and send one message. |
| `ModelRuntime.create({ credentials })` with the ATrade `CredentialStore` writes an OAuth refresh back (#140). | Test with 2 credentials of one provider, and read the file after a refresh. |
| OpenAI can count a self-hosted single-user server as "remotely hosted" (#133). | Read the OpenAI "Preview limitations" page. |

Each section file of the map lists more facts in its "Left to the
implementation" list.

### 21.1 Facts checked

| Fact | Result |
|---|---|
| `ib_async` 2.1.0 and NautilusTrader 2.0 resolve together in one environment. | Yes. On 2026-10-27, `uv lock` (uv 0.13.5) resolved `ib-async==2.1.0`, `nautilus-trader==2.0.0rc7`, and `tzdata==2025.3` for Python 3.14 (#62). |
| `ghcr.io/gnzsnz/ib-gateway:stable` digest. | On 2026-10-27, the `stable` index was `sha256:1e2236804ac949b789197c225a048c0c891c9958f948c87166226e5b647ff581` (IB Gateway 10.50.1f) (#63). |
| `ib_async` 2.1.0 and NautilusTrader 2.0.0rc7 import on Python 3.14. | Yes. Both packages import on CPython 3.14.9 (#62). The real connection is the next row. |
| `ib_async` 2.1.0 (client protocol 178 at most) connects to IB Gateway 10.50.1f. | Yes. On 2026-10-27 the Gateway reported server version 178. The `ibkr_paper` contract cases for the connection, `managedAccounts` (exactly 1 `DU` account), the instrument search (`AAPL`, `700` on SEHK), historical bars (1 minute and 1 day), and the refusals without a connection pass. ib_async reports the API as ready before its startup synchronization ends, so `is_connected()` now waits for the end of `connectAsync` (section 7.2). |
| Live bars with keepUpToDate (`stream_live_bars`, 1 minute and 1 day) on a real Gateway. | Yes. On Tuesday 2026-10-27 at about 10:00 UTC, outside the US trading hours, the first `AAPL` bar came within 60 seconds for both periods (contract test `test_streams_the_current_live_bar`). |
| `NetLiquidation` in USD on the paper account of the owner. | No. On 2026-10-27 the paper account had the base currency EUR, and the owner cannot change it. IBKR sent `NetLiquidation` and `TotalCashValue` only in EUR, and `$LEDGER-ExchangeRate` only for `BASE` and `EUR` (`1.00`): no USD ledger, so no USD rate from the account. Decided: ATrade converts the balance to USD (section 11.9 of `paper_trading.md`) with the account `ExchangeRate` for USD when IBKR sends it, else with the IBKR forex rate (`read_exchange_rate`, last 1 hour `MIDPOINT` bar of IDEALPRO `EUR.USD`). Checked on 2026-10-27 against the real Gateway with read-only queries: `PaperAccountMonitor.read_balance()` returned base currency EUR, rate source `ibkr_forex`, and a USD net liquidation; the `ibkr_paper` cases `test_reads_the_balance_and_the_positions_of_the_paper_account` and `test_reads_the_forex_rate_for_the_paper_account_balance` pass. The account `ExchangeRate` path is checked only with the fake. |
| Editor input latency and completion latency in the browser. | On 2026-10-27, Playwright 1.64.1 (headless Chromium and Firefox) against `tests.e2e_server` on the same machine, basedpyright 1.40.2 (#69). Input latency (key press to the next painted frame, 50 keys): Chromium median 9.8 ms, p95 16.6 ms; Firefox median 3.0 ms, p95 6.0 ms. Completion latency (Ctrl+Space to the visible list for `self.subscribe_ba` in a `Strategy` subclass): first request after the page opens 782 ms (Chromium) and 808 ms (Firefox); next 10 requests 74 to 76 ms (Chromium) and 81 to 86 ms (Firefox). Not measured through Cloudflare. |
| A Python indicator class written by ATrade registers with `register_indicator_for_bars` (#131 read the source only). | Yes. On 2026-10-30 with NautilusTrader 2.0.0rc7 (#160), the minimal class `atrade.indicator.BarClose` ran in the backtest engine. The class does not subclass a NautilusTrader class: rc7 exports no `Indicator` base class, and `register_indicator_for_bars` accepts any object with `handle_bar(bar)` and `initialized`. NautilusTrader called `handle_bar` before `on_bar`, so `on_bar` read the close of the current bar on each of 3 bars (`tests/indicator/test_indicator_registration.py`). |
| Strategy code can import `atrade.indicator` (#136, #138). | Yes. On 2026-10-30 (#160), a strategy version that imports `atrade.indicator` passed the checks before save (section 9.3, `ruff --select F` included) and ran in a real backtest child with the status `finished`. The indicator value in `on_bar` was the close of each of the 20 bars (`tests/indicator/test_indicator_registration.py`). |
| The default smoothing (`ma_type`) of `RelativeStrengthIndex` and `AverageTrueRange` in NautilusTrader 2.0.0rc7. | On 2026-10-30 (#160), in the backend environment: both defaults are Wilder. `AverageTrueRange(14).ma_type` is `MovingAverageType.Wilder`. `RelativeStrengthIndex` has no `ma_type` property, so the check compared values: on 200 test closes, RSI(14) with the default gave 34.832627, the same as `ma_type=MovingAverageType.Wilder` and as a Wilder RSI written by hand; `Exponential` gave 14.769989 and `Simple` gave 5.270742. The value scale is 0 to 100. `MovingAverageConvergenceDivergence` defaults to `Exponential`. The indicator library does not need to pass `MovingAverageType.Wilder` for RSI and ATR. |
| The difference of a recursive indicator value when it starts from fewer bars (`docs/architecture/indicator.md` section 23.4). | On 2026-10-30 (#160), NautilusTrader 2.0.0rc7 with default parameters, on 1000 fixed synthetic daily bars (no saved real daily bars were available): start close 100, each close is the previous close times `exp(N(0, 0.015))` (Python `random.Random(160)`), high and low are 0 to 1 % outside the open and the close, and the open is the previous close. The table value is the value at the last bar when the class starts N bars before the end, minus the value when it starts 1000 bars before the end. Last close 108.59. RSI(14) (1000 bars: 22.772027): N=50 +0.40, N=100 -0.0010, N=150 -0.00025, N=200 +0.0000024. EMA(20) (116.353654): N=50 +0.023, N=100 +0.00012, N=150 +0.0000027. EMA(50) (120.956079): N=50 +3.5, N=100 +0.39, N=150 -0.038, N=200 +0.00038, N=300 -0.000092. ATR(14) (2.556675): N=50 -0.0038, N=100 +0.00011, N=150 -0.0000032. MACD(12, 26) line (-3.635635): N=50 -0.21, N=100 -0.0058, N=150 -0.000051, N=200 +0.00000089. Suggested look-back (#163 decides it): 8 × the longest period of the recursive average (RSI(14): 112, EMA(20): 160, EMA(50): 400, ATR(14): 112, MACD(12, 26): 208 by the slow period). With it, every measured difference is less than 0.005, half of the last place of a value with 2 decimals. The MACD signal line was not measured. |
| Start time of a backtest child process (estimated 1 to 3 seconds). | On 2026-10-27, a new CPython 3.14.9 process that imports `atrade.app.backtest_process` (NautilusTrader 2.0.0rc7, pyarrow 26.0.0, FastAPI) took 0.38 seconds (median of 10 runs, 0.379 to 0.392 seconds) on an AMD Ryzen 9 9950X3D, outside Docker (#70). The full test backtest of 20 daily bars, from the child start to the saved result, ends in about 1 second. Not measured in the `web` container. |

## 22. Points left to the implementation

The decisions do not name these details. The implementation picks the simplest
option and records it in this document.

- Decided (#76): `forward_test` cancels the open orders of its client ID
  itself (section 12.6), with the `ibkr` functions `read_own_open_orders()`
  (`reqOpenOrders`) and `cancel_order_and_wait()`. Section 6.2 has the new
  edge `forward_test -> ibkr`. `paper_trading` exports no cancel function.
- Decided (#76): the child process gets its connections through
  `IbkrAccess.open_gateway_connection(client_id)`. `app/forward_test_process.py`
  passes a function that makes a new `IbAsyncGatewayConnection` with the
  client ID of the forward test. The child connects it with `connect()` for
  the paper account check and again for the stop steps, and disconnects it
  before the LiveNode starts.
- Decided (#160): the minimal indicator class is `BarClose` (the close of
  the last bar) in `indicator/bar_close.py`. The indicator tests are in
  `backend/tests/indicator/`. Their test strategy
  `tests/indicator/strategies/record_bar_close.py` registers the class and
  writes the value of each `on_bar` to a file.
- Decided (#160): an ATrade indicator class does not subclass a
  NautilusTrader class. It has `handle_bar(bar)` and an `initialized`
  property (section 21.1).
- Decided (#74): a forward test child passes its own connection as the
  `gateway_connection` argument of `require_paper_account()` (section 11.5).
- Decided (#187): `ChatLog` follows new content while the end of the log is
  at most 48px below the visible area (`LOG_END_THRESHOLD_PIXELS` of
  `foundation/carbon/chat_log.ts`, the value of the Carbon `ChatLog`). A new
  message with `from="me"` always scrolls the log to the end, also while the
  user reads older messages (as in the Carbon `ChatLog`). The
  divider dates are UTC dates, like the other times of the app.
- Decided (#177): a `SideColumn` stores `{isMinimized, widthPixels}` under
  its `storageKey`. `widthPixels` null gives the default width, and a
  double-click on the splitter sets it to null. A value stored before the
  splitter (`{isCollapsed}` only) reads as `isMinimized` with the default
  width. The shown width is the stored width in the range of section 25.13,
  so a smaller window makes the column narrower without a change of the
  stored width.
- The open points of the map #129 are in the "Left to the implementation"
  lists of sections 8 to 12 and 23 to 25. Two of them:
  - How the platform gives the strategy the new universe list at each
    period start: NautilusTrader custom data or a platform timer (#142).
    Make a small test first.
  - The backtest look-back is 60 days for daily bars. SMA(200) and 12-1
    momentum need about 252 bars. The look-back must follow the longest
    indicator of the strategy, or this effect is accepted.
- Decided (#178): the `assistant` service code is in `assistant/`, an own
  pnpm project that Vite+ runs like `frontend/`. Node.js runs the
  TypeScript files directly (type stripping), so there is no build step. The
  image is `deploy/assistant.Dockerfile`. The checks are
  `./scripts/check assistant` and the CI job `assistant` (section 17.7).
- Decided (#178): the subnet of `atrade-assistant-internal` is fixed in
  `deploy/compose.yaml` as `172.31.250.0/24`. It is not a setting.
  `assistant` listens on port 8002 in this network. In #178 it has only
  `GET /health`.
- Decided (#178): the `tool_call` handler is `createToolGuard` in
  `assistant/src/tool_guard.ts`. It is an inline pi extension factory of
  the `assistant` process (section 25.14).
- Decided (#214): the owner ledger of "By hand" (the ledger start at the
  first passed check, the cash of rule 2, the price of a market buy, the
  USD conversion, and when the Web process records fills) is in
  [`paper_trading.md`](architecture/paper_trading.md) sections 11.10 and
  11.13.
- These names are choices of this document, not decisions of a ticket. The
  implementation can change them:
  - the Compose service names `postgres`, `ib-gateway`, `web`, `forward-test`
  - the path `backend/migrations/`
  - the default Web client ID `1`

## 23. Indicator library

Section 23 is in [`docs/architecture/indicator.md`](architecture/indicator.md).
It holds the indicator decisions (one definition for screens and strategies,
the time rule, no value), the first 11 indicators, the `indicator` module and
its catalog, the look-back bars of a screen, and the consistency tests.

## 24. Screens

Section 24 is in [`docs/architecture/screen.md`](architecture/screen.md). It
holds the screen decisions (two-step run, rank rule, one market), the
`screen` tables, the run flow, the checks, the routes under `/api/screens`
and `/api/screen-results`, the AI assistant access, screens as a backtest
universe, and the `/screens/<id>` page.

## 25. AI assistant

Section 25 is in [`docs/architecture/assistant.md`](architecture/assistant.md).
It holds the AI assistant decisions, the `assistant` service with the pi SDK,
port 8001 and its allow-list, credentials and provider login, conversations
and prompt versions, the tools for strategies, backtests, and screens, Keep
and Discard, and the AI assistant column of the strategy page.
