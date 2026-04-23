---
status: active
owner: architect
updated: 2026-04-23
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
> `src/ATrade.ServiceDefaults`, and the first scaffolded backend service,
> `src/ATrade.Api`, currently exist. The `workers/` directory and the other
> backend feature modules listed below remain aspirational and will land in
> later milestones tracked by `PLAN.md`. The `frontend/` directory now hosts
> the first real Next.js slice: a minimal home page that proves Aspire can
> orchestrate a real frontend runtime, while broader UI routes remain later
> work.
>
> **Current runnable slice:** today the AppHost launches `ATrade.Api` plus the
> Next.js frontend home page, declares `Postgres`, `TimescaleDB`, `Redis`, and
> `NATS` as managed infrastructure resources, and still keeps `ATrade.Api`
> limited to a stable `GET /health` smoke endpoint while broader domain modules
> remain future work.

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
  `ATrade.Api` plus the bootstrap Next.js frontend home page and declares the
  four shared infrastructure resources without adding application consumers yet
  — see `src/ATrade.AppHost/Program.cs`.
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

### 2.3 `ATrade.Api` *(exists today, first slice only)*

- **Purpose:** The single public HTTP surface for the Next.js frontend and
  any future external clients.
- **Responsibilities:** In the current slice, provide a minimal ASP.NET
  Core host that uses `ATrade.ServiceDefaults` and exposes a stable
  `GET /health` smoke endpoint. Later slices add authenticated
  REST/streaming endpoints for accounts, portfolios, strategies, orders,
  and market-data queries plus translation of HTTP requests into module
  calls and NATS publications.
- **Expected dependencies:** `ATrade.ServiceDefaults` today; later,
  every backend feature module, `Postgres`, `Redis` (session/rate-limit),
  and `NATS` (publishing intents, subscribing to UI-bound events).
- **First-phase focus:** The scaffold proves the backend/AppHost bootstrap
  path. Functional IBKR account/order and Polygon market-data surfaces land
  in later slices.

### 2.4 `ATrade.Accounts` *(planned)*

- **Purpose:** Account, portfolio, and position bookkeeping.
- **Responsibilities:** Own the canonical account/portfolio/position
  schema; reconcile broker-reported state with internal state; expose
  query and projection APIs.
- **Expected dependencies:** `Postgres` (system of record), `NATS`
  (execution events from the broker integration), `ATrade.ServiceDefaults`.
- **First-phase focus:** Reconcile against IBKR account and execution
  events.

### 2.5 `ATrade.Orders` *(planned)*

- **Purpose:** Order lifecycle and routing.
- **Responsibilities:** Validate order intents, persist order state
  transitions, route to the correct broker integration via NATS, publish
  execution updates.
- **Expected dependencies:** `Postgres` (order state), `NATS` (publish
  intents, consume executions), `ATrade.Accounts`,
  `ATrade.ServiceDefaults`.
- **First-phase focus:** Routes exclusively to IBKR; provider-agnostic
  order contract is required so other brokers can be added later.

### 2.6 `ATrade.MarketData` *(planned)*

- **Purpose:** Market data ingestion, storage, and query.
- **Responsibilities:** Define bar/tick schemas; expose historical queries
  against TimescaleDB; publish real-time updates onto NATS for
  subscribers; cache hot reads in Redis.
- **Expected dependencies:** `TimescaleDB` (hypertables), `Redis` (hot
  cache), `NATS` (real-time fan-out), `ATrade.ServiceDefaults`.
- **First-phase focus:** Polygon is the only data provider; provider
  adapter lives behind an internal `IMarketDataProvider`-style boundary.

### 2.7 `ATrade.Strategies` *(planned)*

- **Purpose:** Strategy definition, evaluation, and signal generation.
- **Responsibilities:** Persist strategy definitions and parameters;
  evaluate strategies against live and historical market data; emit
  signals that `ATrade.Orders` may act on.
- **Expected dependencies:** `Postgres` (definitions), `TimescaleDB`
  (evaluation traces), `NATS` (signal publication), `ATrade.MarketData`,
  `ATrade.ServiceDefaults`.
- **First-phase focus:** Swing/position strategies evaluated against
  Polygon bars.

### 2.8 `ATrade.Brokers.Ibkr` *(planned)*

- **Purpose:** IBKR broker adapter.
- **Responsibilities:** Translate internal order intents into IBKR API
  calls; ingest IBKR execution, position, and account updates; surface
  them back onto NATS using provider-neutral event shapes.
- **Expected dependencies:** `NATS`, `Redis` (rate-limit counters for the
  IBKR API), `ATrade.ServiceDefaults`. Paired with the `ibkr-worker`
  under `workers/`.
- **First-phase focus:** The entire module is the first-phase broker
  integration.

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
exclusively through `NATS` and the shared databases.

### 3.1 `ibkr-worker` *(planned)*

- **Purpose:** Host the IBKR session and execute the broker-side half of
  `ATrade.Brokers.Ibkr`.
- **Responsibilities:** Maintain the IBKR connection; consume order
  intents from NATS; publish executions, positions, and account updates.
- **Expected dependencies:** `ATrade.Brokers.Ibkr`, `NATS`, `Redis`,
  `Postgres` (for durable intent/execution correlation),
  `ATrade.ServiceDefaults`.
- **First-phase focus:** Core first-phase worker.

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

### 4.1 Next.js app *(exists today, bootstrap slice only)*

- **Purpose:** The sole user-facing surface for ATrade.
- **Responsibilities:** Render dashboards for accounts, positions,
  orders, strategies, and market data; stream live updates; delegate all
  server-side concerns to `ATrade.Api`; participate in the Aspire graph
  as a JavaScript resource so it starts, stops, and is observed with the
  rest of the stack.
- **Expected dependencies:** `ATrade.Api` for all data; the Aspire
  AppHost for process lifecycle and environment wiring.
- **First-phase focus:** UI surfaces for IBKR accounts/orders and
  Polygon-sourced market data; the current slice is intentionally small and
  serves a stable home page (`ATrade Frontend Home` / `Next.js Bootstrap
  Slice`) so shell smoke tests can verify the real Next.js runtime before
  broader feature work lands.

## 5. Dependency Summary

The expected intra-repo dependency direction is:

```text
frontend (Next.js)
    │  HTTP / streaming
    ▼
ATrade.Api ──► ATrade.Accounts
          ├──► ATrade.Orders ──────► ATrade.Brokers.Ibkr ◄── ibkr-worker
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
