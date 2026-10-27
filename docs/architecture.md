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
| `foundation/` | `money`, `clock`, `instrument`, `settings`, `order_ref`. |
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
forward_test  -> strategy, paper_trading, backtest
all modules   -> foundation
app           -> all modules
```

- `ibkr` depends on no capability.
- `forward_test -> paper_trading` is only for the paper account check.
- `forward_test -> backtest` is only for the comparison and the metric
  functions.
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

Sources: [Strategy editing and run isolation](https://github.com/Mano-Liaoyan/ATrade/issues/48),
[Module division](https://github.com/Mano-Liaoyan/ATrade/issues/38).

- A backtest request contains the strategy version, the instrument, the bar
  type, the time range, and `paper_capital_usd`. `paper_capital_usd` is
  required.
- `paper_trading` exports `fetch_paper_capital_usd()`. It returns the paper
  account balance (`NetLiquidation` in USD) after a passed paper account check.
  Otherwise it returns the local value from `settings` (section 11.5). The frontend uses it to fill in the backtest form.
- Each backtest runs in its own child process (`app/backtest_process.py`),
  because the NautilusTrader backtest engine blocks the event loop.
- In NautilusTrader 2.0, `BarDataWrangler` takes Arrow bytes, not a
  DataFrame. The child converts the bars from PostgreSQL to Arrow.
- The isolation goal is to prevent accidents, not to stop hostile code. Only
  one user writes strategies.

| Control | Rule |
|---|---|
| Timeout | Default 120 minutes. After the timeout, the parent stops the child. The status is "timed out". |
| Concurrency | Default 1 backtest at a time. Other backtests wait in a queue. |
| Defaults | The user can change the timeout and the concurrency in the UI. PostgreSQL stores them. |
| Memory | Do not use `RLIMIT_AS`. The `web` container has a memory limit. The child sets `oom_score_adj` to 1000, so the kernel stops the backtest first when memory is low. |
| CPU | The child runs with `nice 10`. |
| Environment | Allow list: `PATH`, `HOME`, `TZ`, `DATABASE_URL`. IBKR and Cloudflare secrets are not passed. |
| Network | No network isolation. The child must connect to PostgreSQL. |
| File system | The container root file system is read-only. Only `/tmp` is writable. |

## 11. Paper trading

Section 11 is in [`docs/architecture/paper_trading.md`](architecture/paper_trading.md).
It holds the live order switch, the paper account check, paper orders sent by
hand, the order list, the `paper_trading` module, `/ws/paper-trading`, and the
account panel.

## 12. Forward test

Source: [Forward test design](https://github.com/Mano-Liaoyan/ATrade/issues/41).
The NautilusTrader facts in this section come from the `v2.0.0rc7` source and
documents. Nobody ran them.

### 12.1 Input and process

- Each forward test has 1 child process. The process has 1 `LiveNode`,
  1 user `Strategy`, and 1 client ID.
- Input: a strategy version, 1 instrument, 1 bar type, and an optional end
  time. The start time is always "now".
- Without an end time, the forward test runs until the user stops it.
- The end time is a date and a time. The browser shows it in the local time
  zone. The database stores UTC. The end time cannot change while the forward
  test runs.
- At the end time, the worker stops the forward test with the steps of
  section 12.6.
- The bar type must use a period that IB live bars support. Backtests do not
  have this limit. The supported periods are:
  - 1, 5, 15, or 30 seconds
  - 1, 2, 3, 5, 10, 15, 20, or 30 minutes
  - 1, 2, 3, 4, or 8 hours
  - 1 day, 1 week, or 1 month
- A forward test does not use paper capital. It uses the real paper account
  balance and records the balance at start.
- A forward test does not need a backtest first. The start form shows the
  metrics of the latest backtest of the strategy version, or "no backtest
  result".
- The strategy version is fixed at start. To use a new version, stop the
  forward test and start a new one.

### 12.2 One forward test per instrument

- NautilusTrader reconciles by account, not by client ID. With two position
  sources on one instrument, NautilusTrader generates synthetic fills to align
  the positions. When it cannot align them, the start fails.
- So only 1 forward test can run on one instrument at a time.
- Paper orders by hand on that instrument are refused (section 11.3).

### 12.3 Web and worker

- The forward test table has a `desired_state` column (`running` or
  `stopped`). The Web process writes only this column.
- Every 2 seconds, the worker compares `desired_state` with the actual state.
  It starts or stops child processes and writes the actual state back.
- Every 2 seconds, the Web process reads the actual state and pushes it on
  `/ws/forward-tests`.

### 12.4 Client IDs

- The forward test client ID range is in `settings`. The default is `10–13`.
- The range size is the limit of forward tests that run at the same time
  (default 4). There is no other limit.
- At start, one transaction takes the lowest free ID in the range. A unique
  constraint prevents two forward tests from getting the same ID.
- A forward test keeps its ID while it runs, restarts, or has the status "stop
  failed". The ID becomes free after the orders are cancelled and the process
  ends.
- When no ID is free, the start is refused. The UI shows "limit of running
  forward tests reached".

### 12.5 Paper account check

- Before each `LiveNode` start, including automatic restarts, the child
  process:
  1. Connects with `ib_async` and its own client ID.
  2. Calls `require_paper_account()`.
  3. Disconnects.
  4. Starts the `LiveNode` with the same client ID.
- The Web process does not repeat the check.
- The child passes `settings.ibkr_account_id` to the IB execution client
  `account_id`.
- When the check fails, the status is "failed". There is no retry.
- When the Gateway is not reachable, the child retries every 30 seconds. The
  UI shows "waiting for IB Gateway". This does not count toward the 3-crash
  limit (section 12.7).

### 12.6 Stop

1. The child stops the `LiveNode`.
2. The child connects with `ib_async` and the same client ID.
3. The child reads the open orders of this client ID with `reqOpenOrders`.
4. The child cancels each order and waits for the confirmation.
5. The child exits.

- Positions stay open. The user handles them by hand.
- Do not use `manage_stop`. It closes positions. `LiveNode.stop()` does not
  cancel orders.
- When a cancellation fails, the status is "stop failed". The client ID stays
  taken. The worker retries the cancellation.

### 12.7 Recovery after restart

- Daily IB Gateway restart: NautilusTrader reconnects and subscribes to bars
  again. When the IB execution client is disconnected for more than 5 minutes,
  the child exits. The worker waits for the Gateway (section 12.5) and starts
  it again. This does not count toward the 3-crash limit.
- Other stops are a restart of the `forward-test` service, a server restart,
  or a child crash. After each of them, the worker restarts the forward test.
  It uses the same client ID and the same strategy version.
- After 3 crashes in a row, the status is "failed". The worker stops the
  restarts.
- Restart steps:
  1. Cancel all open orders of this client ID (section 12.6). This prevents
     duplicate orders.
  2. Start the `LiveNode`. Set `external_order_instrument_ids` and
     `reconciliation_instrument_ids` to the instrument. The account position
     on this instrument belongs to this strategy (section 12.2).
  3. The strategy indicators start from zero. NautilusTrader does not save
     strategy state without Redis.
- An event table records the start and the end of each interruption.

### 12.8 Records

- A platform `DataActor` subscribes to the same bar type.
- At the end of each bar, the actor reads `self.cache`. It appends new fills
  (unique by `trade_id`) and one equity snapshot row to the forward test
  tables.
- Reasons:
  - A Python `DataActor` cannot subscribe to order and fill events. Only a
    `Strategy` gets them.
  - Do not use `PostgresCacheConfig`. Its tables belong to NautilusTrader and
    can change in each release candidate.
  - Do not write a `Strategy` base class. The readability rules forbid our own
    inheritance.
- The current state of open orders still comes from IBKR.

### 12.9 Order source

- The forward test sets `order_id_tag` to `FT<forward test ID>`.
- The IB execution client writes the `ClientOrderId` into `orderRef`. User code
  cannot change it.
- `foundation/order_ref.py` holds the format rule. `forward_test` writes it.
  `paper_trading` reads it.
- The frontend changes the ID into the forward test name in `routes/`.

### 12.10 Comparison with a backtest

- The forward test page has a "backtest the same period" button. It creates a
  normal backtest with:
  - the same strategy version, instrument, and bar type
  - the period from the forward test start to its end, or to now while it runs
  - `paper_capital_usd` equal to the balance at forward test start
- The comparison page uses the comparison view of section 9.5: the metric
  table and both equity curves on one chart.
- A fill table shows, for each bar, the fill price on each side and the
  difference.
- The chart marks interruptions in grey.
- Forward test metrics use the same metric functions that `backtest` exports.

## 13. Frontend

Sources: [Technology stack decision](https://github.com/Mano-Liaoyan/ATrade/issues/37),
[Readability rules for Python and TypeScript](https://github.com/Mano-Liaoyan/ATrade/issues/51).

- SvelteKit 3 in SPA mode. Do not use the SvelteKit server features:
  `+page.server.*`, `+layout.server.*`, `+server.*`, `hooks.server.*`,
  `*.remote.*`, and form actions. ESLint fails on these file names.
- SvelteKit 3 reads configuration from `vite.config.ts` in `sveltekit({...})`.
  It does not read `svelte.config.js`.
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
- Generated API types go in `lib/api/`. `python -m atrade.app.openapi_document`
  writes the OpenAPI document to `lib/api/openapi.json`, and
  `openapi-typescript` writes `lib/api/index.ts`. `pnpm generate:api` runs
  both. Both files are committed. The backend test
  `tests/app/test_openapi_document.py` fails when `openapi.json` does not
  match the routes, and `pnpm check:api` fails when `index.ts` does not match
  `openapi.json`. Use `components['schemas'][...]`; do not write API types by
  hand.
- `foundation/scroll_region/` has `ScrollRegion`: a region that scrolls inside
  itself. It hides the native scrollbar and draws its own track and thumb
  (`role="scrollbar"`, named "<region label> scroll bar"). The thumb can be
  dragged, a click on the track scrolls one page, and the track takes Arrow,
  Page Up, Page Down, Home, and End keys. Use it for each region that can
  overflow (section 13.1).
- WebSocket reconnection and heartbeat are our own code. Reconnection is
  required, because browsers suspend background tabs in different ways.
  `foundation/live_socket` does it: a server heartbeat every 10 seconds, a
  reconnection after 25 seconds without a message or after a close, and a
  delay from 1 to 10 seconds between attempts.
- `lightweight-charts` uses the Apache 2.0 license. The UI must show the
  TradingView attribution.
- Chart times are UNIX timestamps, not date strings. This keeps the browsers
  consistent.

### 13.1 Browser behavior

- Safari, Firefox, Chrome, and Edge (latest desktop versions) must behave the
  same.
- When page scrolling is off, each region that can overflow must have its own
  visible scroll track and thumb. Safari can hide native scrollbars, so use
  styled tracks where reachability matters.
- No content can be clipped or unreachable.

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
- The image of `web` comes from `deploy/web.Dockerfile`. A Node stage builds
  the SPA with `adapter-static`. The Python stage installs the backend with
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
- `postgres` uses the image `postgres:18.3` and the new volume `atrade-pgdata`
  (section 19). Its port is not published.
- Services added later (`ib-gateway`, `forward-test`, `cloudflared`) must not
  block the local start when their credentials are missing. They fail with a
  clear message, or they are in a Compose profile. `ib-gateway` is in the
  profile `ibkr` (section 7.4).

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
`ATRADE_IBKR_USERNAME` and `ATRADE_IBKR_PASSWORD` are not settings: only the
`ib-gateway` service reads them (section 7.4).

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
  `docs/architecture/strategy.md`. Section 11 is in
  `docs/architecture/paper_trading.md`.
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
| `ib_async` 2.1.0 connects with client protocol 178 at most. Features after 178 are not available. Its real connection to Gateway 10.50.1f is not checked. | The `ibkr_paper` contract tests. |
| The Web connection gets live status updates for orders of other client IDs. Only the `reqAllOpenOrders` snapshot is checked. | The `ibkr_paper` contract tests. |
| Live bars with periods other than 5 seconds use `reqHistoricalData` with keepUpToDate. | Read the `ibapi` crate source, or run a forward test. |
| Start time of a backtest child process (estimated 1 to 3 seconds). | Measure it in phase 1. |

### 21.1 Facts checked

| Fact | Result |
|---|---|
| `ib_async` 2.1.0 and NautilusTrader 2.0 resolve together in one environment. | Yes. On 2026-10-27, `uv lock` (uv 0.13.5) resolved `ib-async==2.1.0`, `nautilus-trader==2.0.0rc7`, and `tzdata==2025.3` for Python 3.14 (#62). |
| `ghcr.io/gnzsnz/ib-gateway:stable` digest. | On 2026-10-27, the `stable` index was `sha256:1e2236804ac949b789197c225a048c0c891c9958f948c87166226e5b647ff581` (IB Gateway 10.50.1f) (#63). |
| `ib_async` 2.1.0 and NautilusTrader 2.0.0rc7 import on Python 3.14. | Yes. Both packages import on CPython 3.14.9 (#62). A real IB Gateway connection is not checked. |
| Editor input latency and completion latency in the browser. | On 2026-10-27, Playwright 1.64.1 (headless Chromium and Firefox) against `tests.e2e_server` on the same machine, basedpyright 1.40.2 (#69). Input latency (key press to the next painted frame, 50 keys): Chromium median 9.8 ms, p95 16.6 ms; Firefox median 3.0 ms, p95 6.0 ms. Completion latency (Ctrl+Space to the visible list for `self.subscribe_ba` in a `Strategy` subclass): first request after the page opens 782 ms (Chromium) and 808 ms (Firefox); next 10 requests 74 to 76 ms (Chromium) and 81 to 86 ms (Firefox). Not measured through the Cloudflare tunnel. |

## 22. Points left to the implementation

The decisions do not name these details. The implementation picks the simplest
option and records it in this document.

- The module that cancels the open orders of a forward test client ID
  (section 12.6). The dependency list in section 6.2 has no `forward_test ->
  ibkr` edge. Either `paper_trading` exports the cancel function, or the edge
  is added. The change must update section 6.2.
- Decided (#74): a forward test child passes its own connection as the
  `gateway_connection` argument of `require_paper_account()` (section 11.5).
- These names are choices of this document, not decisions of a ticket. The
  implementation can change them:
  - the Compose service names `postgres`, `ib-gateway`, `web`, `cloudflared`
  - the path `backend/migrations/`
  - the default Web client ID `1`
