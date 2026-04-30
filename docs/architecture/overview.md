---
status: active
owner: maintainer
updated: 2026-04-29
summary: Target high-level architecture for the ATrade modular monolith, Aspire 13.2 orchestration, and the `start run` contract.
see_also:
  - ../INDEX.md
  - modules.md
  - provider-abstractions.md
  - ../../README.md
  - ../../PLAN.md
  - ../../scripts/README.md
---

# ATrade Architecture Overview

> **Status note:** This document describes the target architecture and the
> current runnable slice. The repository now has an Aspire AppHost graph that
> launches `ATrade.Api`, `ATrade.Ibkr.Worker`, the Next.js frontend, and
> Aspire-managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources.
> Active implementation work is tracked in `PLAN.md` and Taskplane packets
> under `tasks/`.
>
> **Current backend slice:** `ATrade.Api` provides stable `GET /health`,
> `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, market-data HTTP endpoints, backend-owned
> watchlist endpoints under `/api/workspace/watchlist`, and a market-data
> SignalR hub. `ATrade.Accounts` returns bootstrap-safe overview JSON,
> `ATrade.Brokers` defines the provider-neutral broker contract,
> `ATrade.Brokers.Ibkr` supplies the paper-only IBKR implementation,
> `ATrade.Orders` owns deterministic paper-order simulation,
> `ATrade.MarketData` supplies provider-neutral market-data contracts,
> `ATrade.MarketData.Ibkr` supplies provider-backed IBKR/iBeam market data,
> `ATrade.MarketData.Timescale` supplies the TimescaleDB persistence foundation
> for candles and scanner/trending snapshots, and `ATrade.Workspaces` persists
> exact provider/market watchlist pins in Postgres. The AppHost graph forwards the safe
> IBKR/iBeam paper-mode environment contract into `ATrade.Api` and
> `ATrade.Ibkr.Worker`, provides the `postgres` connection string consumed by
> the API/workspaces slice plus the `timescaledb` connection string prepared for
> market-data persistence, and can start an optional `ibkr-gateway`
> `voyz/ibeam:latest` container only when ignored local `.env` credentials enable
> integration. Production market-data mocks remain removed, and API cache-aside
> use of Timescale rows is deferred to TP-030.

## 1. Shape Of The System

ATrade is designed as a **modular monolith** rather than a constellation of
independently deployed microservices. The target system has three first-class
runtime surfaces:

1. A **.NET 10 backend** composed of modules that live in a single solution
   under `src/` and share hosting, configuration, telemetry, and database
   access through `ATrade.ServiceDefaults`.
2. A **Next.js frontend** under `frontend/` that is the only user-facing
   surface. The earlier Blazor UI is explicitly out of scope — Aspire must
   orchestrate Next.js directly (see `scripts/README.md` → *Next.js
   Orchestration Requirement*).
3. **Long-running workers** under `workers/` that perform scheduled,
   streaming, or broker-integration work that must not block API request
   handling.

All three surfaces are wired together by **Aspire 13.2** acting as the local
orchestrator. There is no separate `docker compose`, no independent
`npm run dev`, and no hand-run worker command in the normal local startup
path. `start run` delegates to the Aspire AppHost and the AppHost brings up
every process and every infrastructure resource.

```text
┌──────────────────────────────────────────────────────────────────┐
│                         start run (shim)                         │
│           ./start | ./start.ps1 | ./start.cmd → AppHost          │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
                   ┌────────────────────────────┐
                   │   Aspire 13.2 AppHost      │
                   │   (src/ATrade.AppHost)     │
                   └──────────────┬─────────────┘
           ┌──────────────┬───────┴───────┬──────────────┐
           ▼              ▼               ▼              ▼
   ┌──────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  .NET API    │ │  Workers   │ │  Next.js   │ │  Infra     │
   │  (src/)      │ │ (workers/) │ │ (frontend/)│ │  (below)   │
   └──────┬───────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
          │               │              │              │
          └───────────────┴──────┬───────┴──────────────┘
                                 ▼
               ┌────────────────────────────────┐
               │  Postgres │ TimescaleDB │ Redis │ NATS  │
               └────────────────────────────────┘
```

## 2. The `start run` Contract

The repository-wide startup contract is the repo-local `start` shim defined
in `scripts/README.md`. It exposes one semantic entrypoint on every
supported platform:

| Platform        | Invocation         |
|-----------------|--------------------|
| Unix-like       | `./start run`      |
| PowerShell      | `./start.ps1 run`  |
| Command Prompt  | `./start.cmd run`  |

All three wrappers must resolve to the same behavior: launch the Aspire
AppHost located under `src/ATrade.AppHost`. The AppHost is the only place
that knows how to wire processes to infrastructure. The human-facing Aspire
dashboard UI keeps the safe ephemeral loopback default (`0`) unless ignored
`.env` sets `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT` to a non-zero fixed local port;
the dashboard OTLP endpoint remains ephemeral.

Reserved-but-not-yet-implemented subcommands (`test`, `build`, `lint`,
`fmt`, `agents:dispatch`, `plans:check`, `docs:check`) are enumerated in
`scripts/README.md` → *Reserved Commands*. They must be added through the
same shim, never as ad-hoc top-level scripts.

Within this repository the phrase `start run` always refers to the
repo-local shim contract, not the Windows shell built-in `start` command.
Windows documentation must use the explicit relative path form.

## 3. Aspire 13.2 As The Orchestrator

Aspire 13.2 is the **single local orchestrator** for ATrade. In the target
architecture the AppHost is responsible for:

- Starting the main .NET API host built on `ATrade.ServiceDefaults`
- Starting every worker process defined under `workers/`
- Starting the Next.js app as an Aspire-managed JavaScript resource (the
  pattern already exercised by the bootstrap home page in
  `src/ATrade.AppHost/Program.cs`)
- Declaring `Postgres`, `TimescaleDB`, `Redis`, and `NATS` as Aspire-managed
  infrastructure resources and wiring their connection strings into the
  services that need them. The current runnable slice already declares those
  resources in `src/ATrade.AppHost/Program.cs`, wires `ATrade.Api` to all
  four, wires `ATrade.Ibkr.Worker` to `Postgres`, `Redis`, and `NATS`,
  forwards the safe paper-trading IBKR/iBeam environment contract into both .NET
  processes using redacted Aspire parameters for credential-bearing values, and
  only declares an optional `ibkr-gateway` `voyz/ibeam:latest` container when
  broker integration is enabled and fake credential placeholders have been
  replaced in ignored `.env`. The optional iBeam container also receives a
  read-only repo-local inputs config so Client Portal accepts the loopback/private
  Docker bridge caller addresses used by Aspire published-port requests.
- Emitting OpenTelemetry traces, metrics, and logs via the shared defaults
  so every process reports into the same Aspire dashboard

What Aspire explicitly is **not** asked to do: act as the production
deployment substrate, replace CI, or manage long-term data. Aspire is the
local developer orchestration layer; production topology is out of scope
for this document and for the current milestones in `PLAN.md`.

## 4. Infrastructure Components

The `README.md` *Stack Contract* lists four infrastructure components. Each
plays a distinct, non-overlapping role and no additional stores may be
introduced without an architect review and a doc update here.

### 4.1 Postgres — canonical relational store

Postgres is the system of record for everything that is *not* time-series
bar or tick data: accounts, strategy definitions, order intents,
executions, positions snapshots, configuration, user/session state, and
audit trails. Any durable entity with a lifecycle owned by ATrade lives
here unless it is explicitly a time-series observation. Schema migrations
are owned by the backend module that owns the entity.

Current implementation note: `ATrade.Workspaces` now initializes and owns the
Postgres schema for pinned workspace watchlists through the AppHost-provided
`ConnectionStrings:postgres` reference. Watchlist rows use a durable
`instrument_key` derived from provider, provider id / IBKR `conid`, symbol,
exchange, currency, and asset class, plus a temporary `local-user` /
`paper-trading` identity seam until authentication and named workspaces exist.

### 4.2 TimescaleDB — time-series workloads

TimescaleDB hosts market-data hypertables and any other strictly
time-stamped series ATrade generates (e.g. strategy evaluation ticks,
backtest outputs, broker event streams at observation granularity). The current
market-data foundation owns an `atrade_market_data` schema for provider-backed
OHLCV candles and scanner/trending snapshots through
`ATrade.MarketData.Timescale`; future TP-030 API cache-aside reads decide whether
rows are fresh enough using `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`.
TimescaleDB is logically distinct from Postgres even though it runs the Postgres
protocol: schemas, retention policies, and continuous aggregates live here and
do not mix with transactional OLTP data.

### 4.3 Redis — low-latency cache and ephemeral state

Redis is reserved for ephemeral, regenerable state: hot caches in front of
Postgres/TimescaleDB reads, short-lived session/lock primitives, rate-limit
counters for broker and data-provider calls, and coordination keys between
workers. Anything stored in Redis must be safe to lose on restart.

### 4.4 NATS — internal messaging backbone

NATS is the asynchronous messaging substrate used to decouple the API host
from workers and to fan out broker and market events to interested
subscribers. Typical usage: order intent published by the API → executed
by a broker worker → execution event published back → consumed by the
position/accounting module and by the Next.js UI's streaming layer. NATS
is deliberately chosen over request/response HTTP for intra-system events
so that workers can be restarted and scaled without surprising the API.

## 5. First-Phase Broker And Data Focus

The first delivery phase of the new ATrade codebase targets two external
integrations, and only those two:

- **IBKR through local iBeam (`voyz/ibeam:latest`)** — brokerage/session status first, then paper-safe accounts, orders, executions, positions, and data in later tasks
- **Polygon** — market data (historical bars and real-time streams)

Both integrations live behind provider-agnostic module boundaries on the
backend side (see `provider-abstractions.md` and `modules.md` → *Broker* /
*Market Data*), so additional providers can be added later without reshaping
the rest of the monolith.

The next staged feature direction is a **paper-trading workspace** inside the
Next.js frontend: watchlists, TradingView-like charts, paper-only order entry,
and trending symbols. The backend and UI halves of that direction are now
started: safe IBKR/iBeam session status, credentials-missing/configured-iBeam
states, deterministic paper-order simulation, provider-backed market-data
surfaces, SignalR chart updates, exact Postgres-backed watchlist preferences,
and the optional LEAN analysis provider already route through `ATrade.Api`. The slice
keeps the current modular-monolith and Aspire contracts intact by routing
browser traffic through `ATrade.Api`, using SignalR for browser-facing real-time
updates, using NATS for internal fan-out, keeping orders simulated rather than
live, and treating official IBKR Gateway / iBeam connectivity plus LEAN analysis
as plug-ins behind provider-neutral contracts rather than as reasons to add new
runtime surfaces or API/UI assumptions.

Until those modules, workers, and infrastructure integrations become
functional rather than scaffolded, the rest of this document is aspirational
in the way called out at the top.

## 6. Relationship To Other Documents

- `README.md` — human-facing overview and authoritative stack contract.
- `PLAN.md` — live milestone list; the order in which the architecture in
  this document becomes real.
- `scripts/README.md` — detailed `start run` shim contract and current
  bootstrap status of the AppHost.
- `modules.md` — module-by-module map of the backend, workers, and
  frontend surfaces referenced throughout this document.
- `provider-abstractions.md` — broker and market-data provider switching
  contract.
- `paper-trading-workspace.md` — paper-only workspace architecture,
  streaming boundaries, charting-library decision, and LEAN analysis seam.
- `../INDEX.md` — documentation discovery layer; the architecture docs
  are indexed there with `status: active`.

## 7. Change Control

This document is `status: active` and therefore authoritative. Any change
to the infrastructure list, the number of runtime surfaces, the broker or
data provider for the first phase, or the role of Aspire requires an
explicit maintainer-approved edit to this document **and** to `README.md`
in the same change, per the repository-wide Documentation Contract in
`AGENTS.md`.
