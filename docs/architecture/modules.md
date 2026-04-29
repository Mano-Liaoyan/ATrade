---
status: active
owner: architect
updated: 2026-04-29
summary: Target module map for the ATrade modular monolith covering `src/`, `workers/`, and `frontend/` with first-phase IBKR and Polygon focus.
see_also:
  - ../INDEX.md
  - overview.md
  - ../../README.md
  - ../../PLAN.md
  - ../../scripts/README.md
---

# ATrade Module Map

> **Status note:** This document describes the **target** module layout of
> the ATrade codebase, not a finished implementation. `src/ATrade.AppHost`,
> `src/ATrade.ServiceDefaults`, `src/ATrade.Api`, `src/ATrade.Accounts`,
> `src/ATrade.Brokers.Ibkr`, `src/ATrade.Orders`, `src/ATrade.MarketData`, and
> `workers/ATrade.Ibkr.Worker` now exist. `ATrade.Accounts` provides the
> deterministic bootstrap overview endpoint, `ATrade.Brokers.Ibkr` now owns the
> paper-only broker seam, `ATrade.Orders` now owns deterministic paper-order
> simulation, and `ATrade.Ibkr.Worker` now reports safe disabled/paper/rejected
> status while remaining intentionally light on broker-side state.
> `ATrade.MarketData` now provides deterministic mocked symbol, candle,
> indicator, trending-factor, and SignalR snapshot contracts for the first
> workspace slice. The remaining modules and workers listed below stay
> aspirational and will land in later milestones tracked by `PLAN.md`. The
> `frontend/` directory now hosts the first paper-trading workspace UI slice:
> a Next.js home route with backend-driven trending symbols, local browser
> watchlists, symbol navigation, and `lightweight-charts` chart routes while
> preserving the original bootstrap smoke markers.
>
> **Current runnable slice:** today the AppHost launches `ATrade.Api`,
> `ATrade.Ibkr.Worker`, and the Next.js frontend home page; declares
> `Postgres`, `TimescaleDB`, `Redis`, and `NATS` as managed infrastructure
> resources; forwards the safe IBKR paper-trading environment contract into
> `api` / `ibkr-worker`; and keeps the browser-facing backend slice focused on
> `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/{symbol}/candles`,
> `GET /api/market-data/{symbol}/indicators`, and `/hubs/market-data` while
> the worker limits itself to paper-safe session/status monitoring.

## 1. How To Read This Document

Each module entry below records four fields:

- **Purpose** — the single reason the module exists.
- **Responsibilities** — the concrete capabilities the module owns.
- **Expected dependencies** — other ATrade modules and infrastructure
  resources the module relies on, named using the components defined in
  `overview.md` (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) and in
  `README.md` → *Stack Contract*.
- **First-phase focus** — where `IBKR` (broker) and `Polygon` (market data)
  enter the picture, if at all.

Module boundaries are **logical**, not deployment boundaries. Every backend
module ships inside the same .NET 10 solution and is composed at runtime by
the Aspire AppHost; there are no per-module services in the first phase.

## 2. Backend — `src/`

The backend is a single .NET 10 solution. The AppHost (`ATrade.AppHost`)
composes the runtime graph; `ATrade.ServiceDefaults` supplies cross-cutting
hosting defaults (telemetry, health checks, resilience, configuration).

### 2.1 `ATrade.AppHost` *(exists today)*

- **Purpose:** Aspire 13.2 orchestrator entrypoint. The single place that
  knows how to compose services, workers, the Next.js frontend, and
  infrastructure resources.
- **Responsibilities:** Declare Aspire resources; wire connection strings;
  expose HTTP endpoints for the frontend and API; emit unified telemetry.
- **Expected dependencies:** Every other runtime module as declared
  resources; `Postgres`, `TimescaleDB`, `Redis`, `NATS` as Aspire-managed
  infrastructure resources. In the current runnable slice, the AppHost wires
  `ATrade.Api`, `ATrade.Ibkr.Worker`, and the bootstrap Next.js frontend home
  page; declares the four shared infrastructure resources; sends `api` the
  full backend infrastructure set; sends `ibkr-worker` its current
  `Postgres` / `Redis` / `NATS` references; forwards the safe paper-mode IBKR
  environment contract to the API and worker; and only declares an
  `ibkr-gateway` container when a non-placeholder official image is supplied
  locally — see `src/ATrade.AppHost/Program.cs`.
- **First-phase focus:** Hosts the IBKR and Polygon integrations via the
  modules below.

### 2.2 `ATrade.ServiceDefaults` *(exists today)*

- **Purpose:** Shared hosting defaults for every .NET process in the
  solution.
- **Responsibilities:** OpenTelemetry wiring, default health checks,
  HTTP/gRPC resilience handlers, service discovery integration.
- **Expected dependencies:** None within ATrade; referenced by every other
  .NET module.
- **First-phase focus:** None directly — infrastructure module.

### 2.3 `ATrade.Api` *(exists today, paper-safe backend slice)*

- **Purpose:** The single public HTTP surface for the Next.js frontend and
  any future external clients.
- **Responsibilities:** In the current slice, provide an ASP.NET Core host
  that uses `ATrade.ServiceDefaults`, composes the Accounts, Orders, IBKR
  broker, and MarketData modules, and exposes stable `GET /health`,
  `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`,
  `POST /api/orders/simulate`, `GET /api/market-data/trending`,
  `GET /api/market-data/{symbol}/candles?timeframe=...`,
  `GET /api/market-data/{symbol}/indicators?timeframe=...`, and
  `/hubs/market-data`. The overview endpoint still returns deterministic
  bootstrap JSON from `ATrade.Accounts` (`module`, `status`,
  `brokerConnection`, `accounts`); the broker status endpoint projects the
  safe `ATrade.Brokers.Ibkr` status shape without leaking secrets; the
  simulation endpoint returns deterministic paper-only fills while making
  live broker order placement impossible by construction; and the market-data
  endpoints/hub return deterministic mocked stocks, ETFs, candles,
  indicators, trending factors, and SignalR snapshots without external
  providers. The AppHost now also injects the runtime connection information
  for `Postgres`, `TimescaleDB`, `Redis`, and `NATS` so the local graph
  matches the API's planned infrastructure shape, even though the API does
  not consume those stores functionally yet. Later slices add authenticated
  REST/streaming endpoints for deeper accounts, backend-owned watchlists,
  charts, strategies, and market-data queries plus translation of HTTP
  requests into module calls and NATS publications.
- **Expected dependencies:** `ATrade.ServiceDefaults`, `ATrade.Accounts`,
  `ATrade.Brokers.Ibkr`, `ATrade.Orders`, and `ATrade.MarketData` today for
  functional behavior; the current AppHost graph also provides `Postgres`,
  `TimescaleDB`, `Redis`, and `NATS` connection info so later slices can
  begin consuming them without reshaping the runtime topology.
- **First-phase focus:** The backend now proves the paper-safe composition
  pattern: official IBKR session status, deterministic order simulation, and
  deterministic mocked market-data HTTP/SignalR surfaces for the frontend
  workspace.

### 2.4 `ATrade.Accounts` *(exists today, first read-only slice)*

- **Purpose:** Account, portfolio, and position bookkeeping.
- **Responsibilities:** In the current slice, provide deterministic,
  bootstrap-safe `AccountOverview` response types, a minimal overview
  provider, and DI registration used by `ATrade.Api` to serve
  `GET /api/accounts/overview`. The response intentionally stops at module
  markers (`module = "accounts"`, `status = "bootstrap"`,
  `brokerConnection = "not-configured"`, `accounts = []`). Future slices
  own the canonical account/portfolio/position schema, reconcile
  broker-reported state with internal state, and expose richer query and
  projection APIs.
- **Expected dependencies:** `Postgres` (system of record), `NATS`
  (execution events from the broker integration), and
  `ATrade.ServiceDefaults` in later slices. The current slice
  intentionally avoids persistence, broker/data clients, and fake account
  state while contributing only bootstrap-safe read-only behavior.
- **First-phase focus:** Reconcile against IBKR account and execution
  events after the bootstrap overview slice proves module wiring.

### 2.5 `ATrade.Orders` *(exists today, first paper-simulation slice)*

- **Purpose:** Order lifecycle and routing.
- **Responsibilities:** In the current slice, own deterministic paper-order
  request/response contracts, validate paper-order inputs, enforce
  paper-only eligibility through `ATrade.Brokers.Ibkr`, and return
  deterministic simulated fills for `POST /api/orders/simulate`. Persistence,
  lifecycle fan-out, and broker handoff remain future work, and no
  live-trading path belongs in this module family.
- **Expected dependencies:** `ATrade.Brokers.Ibkr` and
  `ATrade.ServiceDefaults` today for functional behavior; `Postgres`
  (order state), `NATS` (publish intents, consume executions), and
  `ATrade.Accounts` join later when paper-order persistence and projections
  land.
- **First-phase focus:** Own the paper-only order workflow for the workspace
  while keeping the order contract provider-neutral so other brokers can be
  added later.

### 2.6 `ATrade.MarketData` *(exists today, deterministic mocked-data slice)*

- **Purpose:** Market data ingestion, storage, and query.
- **Responsibilities:** In the current slice, provide provider-neutral mocked
  market-data contracts, a deterministic stock/ETF catalog, OHLCV candle
  generation for `1m`, `5m`, `1h`, and `1D`, moving-average / RSI / MACD
  indicator calculations, transparent trending factors, DI registration, and
  a SignalR hub/snapshot service consumed by `ATrade.Api`. Future slices
  expose historical chart queries against TimescaleDB, publish real-time
  updates onto NATS for API / SignalR projection, cache hot reads in Redis,
  and keep deterministic mocked quote/bar feeds available until real provider
  ingestion lands.
- **Expected dependencies:** No external runtime services today beyond
  composition into `ATrade.Api`; future slices add `TimescaleDB` (hypertables),
  `Redis` (hot cache), `NATS` (real-time fan-out), and `ATrade.ServiceDefaults`.
- **First-phase focus:** Polygon remains the primary long-term market-data
  provider, but the current workspace starts with mocked quotes, bars,
  indicators, and trending factors behind the same provider-neutral boundary.

### 2.7 `ATrade.Strategies` *(planned)*

- **Purpose:** Strategy definition, evaluation, and signal generation.
- **Responsibilities:** Persist strategy definitions and parameters;
  evaluate strategies against live and historical market data; emit
  signals that `ATrade.Orders` may act on.
- **Expected dependencies:** `Postgres` (definitions), `TimescaleDB`
  (evaluation traces), `NATS` (signal publication), `ATrade.MarketData`,
  `ATrade.ServiceDefaults`.
- **First-phase focus:** Swing/position strategies evaluated against
  Polygon bars. Any future LEAN adoption plugs into this area as a
  signal-source seam, not as a first-slice dependency.

### 2.8 `ATrade.Brokers.Ibkr` *(exists today, first broker slice)*

- **Purpose:** IBKR broker adapter.
- **Responsibilities:** In the current slice, bind typed paper-mode broker
  options, enforce a paper-only guard, expose the official Gateway
  auth-status client boundary, normalize safe broker status/capability
  shapes, and keep order placement, credential storage, unofficial SDKs, and
  persistence out of scope. Later explicitly reviewed slices may translate
  approved paper-only order intents into IBKR API calls and surface the
  results back onto NATS.
- **Expected dependencies:** Shared hosting/configuration abstractions today;
  consumed directly by `ATrade.Api` and `ATrade.Ibkr.Worker`. Future slices
  may additionally use `NATS` and `Redis` for broker event publication and
  rate-limit counters. Paired with `ATrade.Ibkr.Worker` under `workers/`.
- **First-phase focus:** Provide the paper-only broker seam: session status
  first, paper-safe data next, and no live-trading behavior.

### 2.9 `ATrade.MarketData.Polygon` *(planned)*

- **Purpose:** Polygon market-data adapter.
- **Responsibilities:** Pull historical bars into TimescaleDB; maintain
  real-time streams; translate Polygon-specific shapes into ATrade's
  internal market-data contracts.
- **Expected dependencies:** `TimescaleDB`, `Redis` (API rate-limit
  counters), `NATS` (real-time publish), `ATrade.ServiceDefaults`.
  Paired with the `polygon-worker` under `workers/`.
- **First-phase focus:** The entire module is the first-phase data
  integration.

## 3. Workers — `workers/`

Workers are long-running .NET 10 processes orchestrated by the Aspire
AppHost. Anything that must not block an HTTP request handler — streaming
connections, scheduled jobs, broker sessions — belongs in a worker. They
share `ATrade.ServiceDefaults` and communicate with the API host
exclusively through `NATS` and the shared databases. The first worker
project now exists as compileable scaffolding, and `ATrade.Ibkr.Worker` is
now added to the AppHost runtime graph with its initial infrastructure
references.

### 3.1 `ATrade.Ibkr.Worker` *(exists today, first paper-status slice)*

- **Purpose:** Host the IBKR session and execute the broker-side half of
  `ATrade.Brokers.Ibkr`.
- **Responsibilities:** In the current slice, start a hosted background
  service that composes `ATrade.Brokers.Ibkr`, reports safe disabled /
  not-configured / connecting / authenticated / degraded / error states,
  and fails fast on rejected live-mode requests before any broker call. When
  paper mode is enabled, it polls the official auth-status endpoint through
  the broker adapter; when disabled, it remains idle. The AppHost now wires
  `Postgres`, `Redis`, and `NATS` connection info into the process so the
  runtime graph matches the worker's planned dependencies before any broker
  messaging or database behavior lands.
- **Expected dependencies:** `ATrade.Brokers.Ibkr`, `NATS`, `Redis`,
  `Postgres` (for durable intent/execution correlation),
  `ATrade.ServiceDefaults`. The current worker uses the broker adapter and
  shared defaults functionally today, while the AppHost runtime graph already
  provides the `Postgres` / `Redis` / `NATS` references it will consume more
  deeply later.
- **First-phase focus:** Core worker for paper-only IBKR session and broker
  status handling.

### 3.2 `polygon-worker` *(planned)*

- **Purpose:** Host the Polygon ingestion pipeline for
  `ATrade.MarketData.Polygon`.
- **Responsibilities:** Drive historical backfill into TimescaleDB; run
  real-time streams; publish bars and ticks to NATS.
- **Expected dependencies:** `ATrade.MarketData.Polygon`, `TimescaleDB`,
  `Redis`, `NATS`, `ATrade.ServiceDefaults`.
- **First-phase focus:** Core first-phase worker.

### 3.3 `strategy-worker` *(planned)*

- **Purpose:** Execute `ATrade.Strategies` evaluations out-of-band from
  HTTP request handling.
- **Responsibilities:** Subscribe to market-data events; evaluate active
  strategies; publish signals to NATS for the API/orders path to act on.
- **Expected dependencies:** `ATrade.Strategies`, `ATrade.MarketData`,
  `NATS`, `TimescaleDB`, `ATrade.ServiceDefaults`.
- **First-phase focus:** Consumes Polygon-sourced data and can emit
  signals that `ATrade.Orders` routes to IBKR.

## 4. Frontend — `frontend/`

### 4.1 Next.js app *(exists today, first trading workspace slice)*

- **Purpose:** The sole user-facing surface for ATrade.
- **Responsibilities:** Render dashboards for accounts, positions,
  orders, strategies, and market data; host watchlists, paper-order
  tickets, trending panels, and `lightweight-charts`-based chart surfaces;
  stream live updates over SignalR; delegate all server-side concerns to
  `ATrade.Api`; participate in the Aspire graph as a JavaScript resource so
  it starts, stops, and is observed with the rest of the stack.
- **Expected dependencies:** `ATrade.Api` for all data; the Aspire
  AppHost for process lifecycle and environment wiring.
- **First-phase focus:** UI surfaces for paper-only IBKR connection /
  account views, simulated orders, mocked-or-provider-backed market data,
  and transparent trending-factor explanations. The current slice preserves
  the stable home-page markers (`ATrade Frontend Home` /
  `Next.js Bootstrap Slice` / `Aspire AppHost Frontend Contract`) while adding
  the first workspace route: backend-driven trending stocks/ETFs, symbol
  navigation to `/symbols/[symbol]`, localStorage watchlist persistence,
  `lightweight-charts` candlesticks with `1m` / `5m` / `1h` / `1D` timeframe
  switching, moving-average / RSI / MACD panels, SignalR updates with HTTP
  fallback, and explicit no-real-orders messaging.

## 5. Dependency Summary

The expected intra-repo dependency direction is:

```text
frontend (Next.js)
    │  HTTP / streaming
    ▼
ATrade.Api ──► ATrade.Accounts
          ├──► ATrade.Brokers.Ibkr ◄── ATrade.Ibkr.Worker
          ├──► ATrade.Orders ──────┘
          ├──► ATrade.Strategies ◄── strategy-worker
          └──► ATrade.MarketData ──► ATrade.MarketData.Polygon ◄── polygon-worker

All modules ──► ATrade.ServiceDefaults
All modules ──► Postgres / TimescaleDB / Redis / NATS (as noted above)
```

No backend module may reach "up" into `ATrade.Api` or "sideways" between
brokers and data providers directly — broker modules publish and consume
on `NATS` using provider-neutral contracts defined by `ATrade.Orders` and
`ATrade.MarketData`.

## 6. Relationship To Other Documents

- `overview.md` — high-level architecture and the authoritative role of
  each infrastructure component referenced here.
- `README.md` — authoritative stack contract and repository map.
- `PLAN.md` — order in which the modules above are scaffolded.
- `scripts/README.md` — how `start run` lights all of these processes up
  through the Aspire AppHost.
- `../INDEX.md` — documentation discovery layer.

## 7. Change Control

This document is `status: active` and therefore authoritative. Adding a
new module, splitting an existing module, or changing first-phase broker
or data focus requires an architect-approved edit to this document and a
matching update to `overview.md` and, where structure changes, `README.md`
— per the Documentation Contract in `AGENTS.md`.
