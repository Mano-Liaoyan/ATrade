# ATrade Target Architecture

This document is the target architecture for the full rewrite of ATrade. It
sets the technology stack, the modules, the readability rules, and the test
method. It covers the three capabilities of this stage:

1. Get market data.
2. Run backtests.
3. Paper trading: paper orders sent by hand, and forward tests.

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
- The 8 disabled modules of the old system: news, portfolio, research,
  screener, econ, ai, node, orders. The rewrite has no page and no entry for
  them.
- The implementation of live orders. That is the next stage, with its own map.
- Parameter optimization and tick data.
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
| Backend language | Python only. CPython 3.14, standard GIL build. | NautilusTrader has a Python interface. One language is easiest to read. |
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
| Deployment | User's own server, one Docker Compose project, Cloudflare Tunnel and Cloudflare Access. | See section 14. |
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
deploy/                # compose.yaml, web.Dockerfile
scripts/check          # the quality gate: the same checks as CI (section 17.7)
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
| `market_data/` | Search instruments. Read bars from IBKR and save them in PostgreSQL. Push live market data. |
| `watchlist/` | Add, delete, and list watchlist instruments. |
| `strategy/` | Save, check, and compare strategies and strategy versions. |
| `backtest/` | Run backtests. Save and read backtest results. Provide the metric functions. |
| `paper_trading/` | Paper orders sent by hand, order status, positions, account balance, paper capital, and the paper account check. |
| `forward_test/` | Start and stop forward tests. Record forward test results. |
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
backtest      -> strategy, market_data
paper_trading -> ibkr
forward_test  -> strategy, paper_trading, backtest, market_data, ibkr
all modules   -> foundation
app           -> all modules
```

- `ibkr` depends on no capability.
- `forward_test -> paper_trading` is only for the paper account check
  (`require_paper_account()`, and `PaperAccountMonitor` for the balance at
  start).
- `forward_test -> ibkr` is only for the `GatewayConnection` protocol of the
  child process: the connection for the paper account check, the warm-up
  bars (`read_historical_bars()`), and the stop steps
  (`read_own_open_orders()`, `cancel_order_and_wait()`) (#76, section 22).
- `forward_test -> market_data` is only to save the bars that a forward test
  receives (`save_received_bars()` for the warm-up bars,
  `save_received_bars_blocking()` for each live bar), so a same-period
  backtest finds them (`docs/architecture/forward_test.md` sections 12.8 and
  12.15).
- `paper_trading` does not import `forward_test`. The refusal of paper orders
  by hand on the instrument of a running forward test (section 12.2) gets a
  function from `app/web.py`, which calls
  `forward_test.find_forward_test_on_instrument()`.
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
| `app/web.py` | Compose service `web` | HTTP API, WebSocket, language server processes. 1 uvicorn worker. |
| `app/backtest_process.py` | Child process of `web` | Runs one backtest. Gets only a backtest ID. Reads the request and the strategy version from PostgreSQL. Writes the result to PostgreSQL. |
| `app/forward_test_worker.py` | Compose service `forward-test` | Reads forward test state from PostgreSQL. Starts and stops one child process per forward test. |
| `app/forward_test_process.py` | Child process of `forward-test` | Runs one forward test (`run`) or only cancels its open orders (`cancel_orders`). Gets the forward test ID and the mode. Stops at `SIGTERM`. |

A restart of `web` does not stop forward tests.

### 6.5 Web app routes outside the capabilities

`app/` owns two routers that belong to no capability:

| Route | Behavior |
|---|---|
| `GET /api/health` | `200` with `{"status": "ok", "database": "ok", "time_utc": ...}` when the Web process can connect to PostgreSQL. `503` with `"status": "degraded"` and `"database": "unreachable"` when it cannot. The time comes from `foundation/clock`. |
| `GET /{path}` | The built frontend (section 14.1). It is mounted after all other routers. |

## 7. IBKR access

Section 7 is in [`docs/architecture/ibkr.md`](architecture/ibkr.md). It holds
the IBKR decisions, the `ibkr` module, `GET /api/ibkr/gateway`, the
`ib-gateway` Compose service, and the contract tests.

## 8. Market data and watchlist

Section 8 is in [`docs/architecture/market_data.md`](architecture/market_data.md).
It holds the bar storage decisions, the watchlist decisions, the
instrument search (`GET /api/market-data/instrument-search`), and the
watchlist routes (`/api/watchlist`).

## 9. Strategies and strategy versions

Section 9 is in [`docs/architecture/strategy.md`](architecture/strategy.md).
It holds the storage rules, the `strategy` and `strategy_version` tables, the
strategy file format and template, the checks before save, the strategy HTTP
routes, and the editor pages.

## 10. Backtest

Section 10 is in [`docs/architecture/backtest.md`](architecture/backtest.md).
It holds the backtest decisions and isolation controls, the backtest tables,
the run flow in the child process, the metric functions, the backtest HTTP
routes (`/api/backtests`), and the backtest pages.

## 11. Paper trading

Section 11 is in [`docs/architecture/paper_trading.md`](architecture/paper_trading.md).
It holds the live order switch, the paper account check, paper orders sent by
hand, the order list, the `paper_trading` module, `/ws/paper-trading`, the
account overview and the paper order form (11.7), the order routes (11.8), and the balance in USD for any base
currency (11.9).

## 12. Forward test

Section 12 is in [`docs/architecture/forward_test.md`](architecture/forward_test.md).
It holds the forward test decisions (input, one forward test per instrument,
Web and worker, client IDs, paper account check, stop, recovery, records,
order source, comparison) and the implementation: the `forward_test` table,
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
  page links (Home, Strategies, Backtests, Forward tests) with
  `aria-current="page"` on the current page, the backend status, the IB
  Gateway status, the server time, and the Paper tag. The Paper tag is a
  Carbon operational tag with a tooltip. The tooltip shows the checked paper
  account number with its middle hidden, for example `DU****567`. The header
  reads the account check from `/ws/paper-trading`. Carbon hides the header
  navigation below 1056 px. ATrade is a desktop app, so it keeps the
  navigation at all widths. Header buttons go in `cds--header__global`.
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
  side column collapses. Without `fill`, `height` and `minHeight` set the
  canvas height. `readChartThemeOptions(container)` and
  `readChartColor(container, token)` of `foundation/chart_frame` read the
  Carbon tokens for each chart.
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
    default 17.5rem): a 32px header line with the name and the Collapse
    button ("Collapse <label>"). A collapsed column is a 32px wide rail with
    the Open button ("Open <label>"). The body stays in the page while the
    column is collapsed, so a form keeps its values.
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
    click on the same button restores the panel. Escape restores a maximized
    panel of the split that has the focus (the innermost split first), or of
    each split when the focus is outside all splits. `panel_split.ts` has the
    state as functions with unit tests.
  - `Panel` (`label`, `PanelState`, and `tabs` or a `header` snippet): a
    region with a 32px header line and a body that fills the rest. The header
    line has Carbon tabs (size `sm`) or other content, and at its right end
    the Minimize and Maximize icon buttons ("Minimize panel", "Maximize
    panel", "Restore panel"). A double-click on an empty part of the header
    line toggles Maximize. A tab of a panel that shows only its header line
    opens the panel again. With a `statusBar` snippet, a minimized panel is a
    24px status bar (like the VS Code panel), and a control in it calls
    `onRestore`.
  - `PanelHeader` (`end` snippet): the 32px header line with the class
    `atrade-panel-header`. `Splitter` (`label`, `controls`, `value`, `min`,
    `max`, `onValueChange`): a `role="separator"` (WAI-ARIA window splitter)
    with `aria-controls` on the panel below it; its value is the height of
    that panel, Arrow Up and Arrow Down move it 16px, Home gives the panel its
    minimum height, and End its maximum height.
  - The browser keeps each layout in `localStorage` (`readStoredLayout`,
    `writeStoredLayout`). Blocked storage gives the default layout.
- `foundation/carbon` `IconButton` (`label`, `icon`, `align`, `disabled`, `onclick`) is the Carbon ghost icon-only button, size `sm`, with a Carbon
  tooltip that gives the action name. A disabled `IconButton` has
  `aria-disabled` and stays focusable, so its tooltip and its `label` say why
  it is disabled. `SideColumn` takes an `actions` snippet: icon buttons in its
  header line before the Collapse button. `Tabs` takes `size` (`sm` gives the 32px
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
  liquidation (USD) in two columns with right-aligned tabular numbers; and
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
  the forward test page uses it for its list; the home page uses the
  same paper account feed). While a socket is not connected, the panel and
  the column show `LiveUpdatesNotification`.
- The home page (`/`, [#108](https://github.com/Mano-Liaoyan/ATrade/issues/108))
  is the account overview workbench. The left `SideColumn` "Watchlist"
  (22rem) has the same watchlist table as the instrument page
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
  `StatusIndicator` (`findBacktestStatusKind` of `backtest`). The comparison
  page shows the compared metrics as a data table. The equity chart
  reads only Carbon tokens: `--cds-layer-01` (background),
  `--cds-text-secondary` (text), `--cds-border-subtle-01` (grid),
  `--cds-text-primary` (first curve, solid), `--cds-interactive` (second
  curve, dashed), and `--cds-layer-accent-01` (interruptions). The equity and
  drawdown chart reads `--cds-text-primary` (equity) and
  `--cds-support-error` (drawdown line, and its fill with alpha), and
  `--cds-border-subtle-01` for the line between its 2 panes.
- `foundation/metric_tile` has the one metric tile of all pages: `MetricTile`
  (`name`, `text`, `change`) is a Carbon tile with the name and the
  right-aligned value (tabular numbers). With `change`, the value is a
  `ChangeText`, so up and down show an arrow icon and a support color.
  `MetricRow` (`label`) puts the tiles in one line, each the same width. The
  key metrics of a backtest or a forward test use `KeyMetricRow` of
  `backtest`: one set, one order, and one sign rule (the max drawdown is a
  negative percent). `formatPercent` of `backtest` uses the sign rule of
  `formatSignedNumber`. Rules for each page that shows a metric:
  `formatMaxDrawdown` of `backtest` gives the max drawdown text (a negative
  percent, "0.00 %" for 0) and the signed number; a tile gives that number as
  `change`, so the max drawdown shows with `ChangeText` (down arrow and
  `--cds-support-error`). Total return and net profit also are `change`
  values. Other metrics have no direction.
- `EquityDrawdownChart` of `backtest` (`curves`, `label`, `interruptions`,
  `fill`) is the one equity and drawdown chart. Each curve (`DrawdownCurve`:
  `name`, `points`, `startCapitalUsd`) has an equity line and a drawdown
  curve; the second curve is dashed (`readCurveStyle`), and `ChartLegend`
  names the curves and lists the interruptions (grey columns). The drawdown
  axis is a percent. New points of the same curves do not reset the zoom.
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
- The strategy pages use the components of `foundation/carbon`: the list
  page has a `TextInput` and a `Button` for the new strategy, and the editor
  has a `Select` for the version, the Save version button, an "Unsaved
  changes" tag, and a danger `Dialog` that confirms Delete strategy. The save
  result and the refused checks show as an `InlineNotification`.
  `InlineNotification` also takes child content, for example a list of
  problems.
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

Source: [Deployment platform and external protection research](https://github.com/Mano-Liaoyan/ATrade/issues/33).

One Docker Compose project on the user's own server runs all services:

| Service | Content |
|---|---|
| `postgres` | PostgreSQL. All ATrade data. |
| `ib-gateway` | `ghcr.io/gnzsnz/ib-gateway:stable`, pinned by digest, `TRADING_MODE=paper`, `EXISTING_SESSION_DETECTED_ACTION: primary`. |
| `web` | `app/web.py`, backtest child processes, basedpyright processes. Memory limit, read-only root file system, writable `/tmp`. |
| `forward-test` | `app/forward_test_worker.py` and the forward test child processes. |
| `cloudflared` | Cloudflare Tunnel. |

- `cloudflared` makes only outbound connections. The server can close all
  inbound ports. The tunnel supports WebSocket.
- Only the Web host name is published. The Gateway port is not published.
- Cloudflare Access denies all access by default. One Allow policy includes
  only the user's email address. Login uses One-time PIN.
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
  directory gets the fallback page, never the file.
- At start, `web` runs the Alembic migrations, then starts uvicorn with
  1 worker on port 8000. Compose publishes it on
  `127.0.0.1:${ATRADE_WEB_PORT}` only.
- `web` has `read_only: true`, a `tmpfs` on `/tmp`, and
  `mem_limit: ${ATRADE_WEB_MEMORY_LIMIT}` (default `4g`). `0` turns the memory
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
- Services added later (`ib-gateway`, `forward-test`, `cloudflared`) must not
  block the local start when their credentials are missing. They fail with a
  clear message, or they are in a Compose profile. `ib-gateway` is in the
  profile `ibkr` (section 7.4).
- `forward-test` uses the image of `web` with the command
  `python -m atrade.app.forward_test_worker`. It has the same read-only root
  file system and `/tmp`, the database URL, and the IBKR settings, but not
  `ATRADE_IBKR_USERNAME` or `ATRADE_IBKR_PASSWORD`. It waits until the
  health check of `web` passes, because `web` runs the migrations. It starts
  also without IB Gateway: a forward test start then fails with the reason
  in its `error_message` (#76).

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

Settings refuse client ID 0, client IDs that are multiples of 1000, a range
that ends before it starts, and a Web client ID inside the forward test range.
`ATRADE_IBKR_USERNAME`, `ATRADE_IBKR_PASSWORD`,
`ATRADE_IBKR_AUTO_RESTART_TIME`, and `ATRADE_IBKR_TIME_ZONE` are not settings:
only the `ib-gateway` service reads them (section 7.4).

Environment variable names: `DATABASE_URL` has no prefix, because the backtest
child process gets it by this name (section 10). All other settings use the
prefix `ATRADE_`, for example `ATRADE_TRADING_MODE`. `foundation/settings`
also reads `ATRADE_FRONTEND_BUILD_DIR` (default `/app/frontend-build`, the
path in the `web` image). Compose builds `DATABASE_URL` from
`ATRADE_POSTGRES_PASSWORD`. The ticket that first uses a setting adds it to
`foundation/settings` and to `.env.example`.

The backtest timeout and concurrency are not in `settings`. PostgreSQL stores
them (section 10).

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
  `./scripts/check frontend`, and `./scripts/check e2e` as 3 jobs. The backend
  and end-to-end jobs use a `postgres:18.3` service container. Local runs use
  the same script. Without `ATRADE_TEST_DATABASE_URL`, the script starts a
  temporary PostgreSQL container.
- Backend formatting: `ruff format --check` with line length 120.
- The test PostgreSQL fixture runs the migrations one time per session and
  truncates all tables except `alembic_version` before each test.

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

- The repository root keeps 3 documents:
  - `README.md`: how to run ATrade.
  - `AGENTS.md`: rules for agents.
  - `GLOSSARY.md`: terms.
- This document (`docs/architecture.md`) is the architecture specification.
  When it is longer than 1000 lines, split it by capability. A moved section
  goes to `docs/architecture/<capability>.md`, and its number stays. Section 7
  is in `docs/architecture/ibkr.md`. Section 8 is in
  `docs/architecture/market_data.md`. Section 9 is in
  `docs/architecture/strategy.md`. Section 10 is in
  `docs/architecture/backtest.md`. Section 11 is in
  `docs/architecture/paper_trading.md`. Section 12 is in
  `docs/architecture/forward_test.md`.
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
  changes a volume. The user removes old volumes by hand.

## 20. Implementation phases

1. Market data and backtests. This includes the watchlist and strategies.
2. Paper orders and forward tests.
3. Live orders. This is the next stage, with its own map.

## 21. Facts not yet verified

These facts come from source code, documents, or version constraints. Nobody
ran them. The implementation must check them.

| Fact | How to check |
|---|---|
| `ib_async` 2.1.0 limits `tzdata` to `<2026.0`. A later dependency can conflict with it ([ib_async#209](https://github.com/ib-api-reloaded/ib_async/issues/209)). | Watch `uv lock` on each upgrade. Upgrade to `ib_async` 3.0.0 after its release. |
| The NautilusTrader 2.0 forward test behavior in section 12 (reconciliation, `orderRef`, reconnection, `DataActor` cache reads). | The `ibkr_paper` contract tests in section 17.4. |
| `reqExecutions` and `reqCompletedOrders` read filled orders of other client IDs. | The contract test in section 17.4. |
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

### 21.1 Facts checked

| Fact | Result |
|---|---|
| `ib_async` 2.1.0 and NautilusTrader 2.0 resolve together in one environment. | Yes. On 2026-10-27, `uv lock` (uv 0.13.5) resolved `ib-async==2.1.0`, `nautilus-trader==2.0.0rc7`, and `tzdata==2025.3` for Python 3.14 (#62). |
| `ghcr.io/gnzsnz/ib-gateway:stable` digest. | On 2026-10-27, the `stable` index was `sha256:1e2236804ac949b789197c225a048c0c891c9958f948c87166226e5b647ff581` (IB Gateway 10.50.1f) (#63). |
| `ib_async` 2.1.0 and NautilusTrader 2.0.0rc7 import on Python 3.14. | Yes. Both packages import on CPython 3.14.9 (#62). The real connection is the next row. |
| `ib_async` 2.1.0 (client protocol 178 at most) connects to IB Gateway 10.50.1f. | Yes. On 2026-10-27 the Gateway reported server version 178. The `ibkr_paper` contract cases for the connection, `managedAccounts` (exactly 1 `DU` account), the instrument search (`AAPL`, `700` on SEHK), historical bars (1 minute and 1 day), and the refusals without a connection pass. ib_async reports the API as ready before its startup synchronization ends, so `is_connected()` now waits for the end of `connectAsync` (section 7.2). |
| Live bars with keepUpToDate (`stream_live_bars`, 1 minute and 1 day) on a real Gateway. | Yes. On Tuesday 2026-10-27 at about 10:00 UTC, outside the US trading hours, the first `AAPL` bar came within 60 seconds for both periods (contract test `test_streams_the_current_live_bar`). |
| `NetLiquidation` in USD on the paper account of the owner. | No. On 2026-10-27 the paper account had the base currency EUR, and the owner cannot change it. IBKR sent `NetLiquidation` and `TotalCashValue` only in EUR, and `$LEDGER-ExchangeRate` only for `BASE` and `EUR` (`1.00`): no USD ledger, so no USD rate from the account. Decided: ATrade converts the balance to USD (section 11.9 of `paper_trading.md`) with the account `ExchangeRate` for USD when IBKR sends it, else with the IBKR forex rate (`read_exchange_rate`, last 1 hour `MIDPOINT` bar of IDEALPRO `EUR.USD`). Checked on 2026-10-27 against the real Gateway with read-only queries: `PaperAccountMonitor.read_balance()` returned base currency EUR, rate source `ibkr_forex`, and a USD net liquidation; the `ibkr_paper` cases `test_reads_the_balance_and_the_positions_of_the_paper_account` and `test_reads_the_forex_rate_for_the_paper_account_balance` pass. The account `ExchangeRate` path is checked only with the fake. |
| Editor input latency and completion latency in the browser. | On 2026-10-27, Playwright 1.64.1 (headless Chromium and Firefox) against `tests.e2e_server` on the same machine, basedpyright 1.40.2 (#69). Input latency (key press to the next painted frame, 50 keys): Chromium median 9.8 ms, p95 16.6 ms; Firefox median 3.0 ms, p95 6.0 ms. Completion latency (Ctrl+Space to the visible list for `self.subscribe_ba` in a `Strategy` subclass): first request after the page opens 782 ms (Chromium) and 808 ms (Firefox); next 10 requests 74 to 76 ms (Chromium) and 81 to 86 ms (Firefox). Not measured through the Cloudflare tunnel. |
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
- Decided (#74): a forward test child passes its own connection as the
  `gateway_connection` argument of `require_paper_account()` (section 11.5).
- These names are choices of this document, not decisions of a ticket. The
  implementation can change them:
  - the Compose service names `postgres`, `ib-gateway`, `web`, `cloudflared`
  - the path `backend/migrations/`
  - the default Web client ID `1`
