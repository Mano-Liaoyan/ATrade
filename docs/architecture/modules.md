---
status: active
owner: maintainer
updated: 2026-05-04
summary: Target module map for the ATrade modular monolith covering `src/`, `workers/`, and `frontend/` with provider-neutral broker and market-data seams.
see_also:
  - ../INDEX.md
  - ../design/atrade-terminal-ui.md
  - overview.md
  - provider-abstractions.md
  - analysis-engines.md
  - ../../README.md
  - ../../PLAN.md
  - ../../scripts/README.md
---

# ATrade Module Map

> **Status note:** This document describes the **target** module layout of
> the ATrade codebase, not a finished implementation. `src/ATrade.AppHost`,
> `src/ATrade.ServiceDefaults`, `src/ATrade.Api`, `src/ATrade.Accounts`,
> `src/ATrade.Brokers`, `src/ATrade.Brokers.Ibkr`, `src/ATrade.Orders`,
> `src/ATrade.MarketData`, `src/ATrade.MarketData.Ibkr`,
> `src/ATrade.MarketData.Timescale`, `src/ATrade.Analysis`, `src/ATrade.Analysis.Lean`,
> `src/ATrade.Workspaces`, and `workers/ATrade.Ibkr.Worker` now exist.
> `ATrade.Accounts` provides the deterministic bootstrap overview endpoint,
> `ATrade.Brokers` defines the provider-neutral broker contract,
> `ATrade.Brokers.Ibkr` implements that contract with the paper-only IBKR/iBeam
> status adapter, `ATrade.Orders` now owns deterministic paper-order
> simulation, and `ATrade.Ibkr.Worker` now reports safe disabled,
> credentials-missing, configured-iBeam, connecting/authenticated/degraded,
> and rejected-live statuses while remaining intentionally light on broker-side state.
> `ATrade.MarketData` now provides provider-neutral async market-data read
> contracts, compatibility services, provider status/error shapes, the
> backend-owned `ExactInstrumentIdentity` normalization/key helper, chart range
> preset normalization/lookback semantics, stock search contracts, and SignalR
> snapshot contracts, while `ATrade.MarketData.Ibkr` provides the
> first real IBKR/iBeam market-data provider including secdef search/detail
> mapping. `ATrade.MarketData.Timescale` now provides the TimescaleDB persistence
> foundation plus the API cache-aside decorator for provider-backed candles and
> scanner/trending snapshots while preserving provider/market identity metadata.
> `ATrade.Analysis` now defines the
> provider-neutral analysis engine seam, API-facing registry, normalized request/result shapes, engine/source
> metadata, and no-configured-engine fallback. `ATrade.Analysis.Lean` now
> implements LEAN as the first analysis engine provider behind that seam using
> a generated analysis-only LEAN workspace, AppHost-managed Docker metadata when
> Docker mode is selected, and safe runtime-unavailable states.
> `ATrade.Workspaces` owns the first backend-persisted
> workspace preference: Postgres-backed exact instrument watchlists with stable
> `instrumentKey`/`pinKey` payloads derived from provider, provider id / IBKR
> `conid`, symbol, exchange, currency, and asset class, plus a temporary local
> user / workspace identity seam. The remaining modules and workers listed below stay
> aspirational and will land in later milestones tracked by `PLAN.md`. The
> `frontend/` directory now hosts the first paper-trading workspace UI slice,
> and the target frontend reconstruction is governed by
> [`docs/design/atrade-terminal-ui.md`](../design/atrade-terminal-ui.md): a
> clean-room ATrade Terminal with enabled API-backed modules, visible-disabled
> future modules, deterministic commands, resizable panels, and shadcn/Tailwind/
> Radix-compatible original primitives. The current slice routes home and symbol
> pages through `ATradeTerminalApp`: a deterministic command input,
> enabled/disabled module registry and rail, resizable primary/context/monitor
> layout with versioned browser-local persistence, and status/help surfaces over
> the existing backend-driven trending symbols, bounded/ranked/filterable IBKR
> stock search, Postgres-backed watchlists, `lightweight-charts` chart routes,
> SignalR-to-HTTP fallback, and provider-neutral analysis panel. The
> `frontend/lib/*Workflow.ts` hooks continue to centralize watchlist, bounded
> search result view models, chart range loading, source labeling, and streaming
> fallback orchestration behind the terminal frame.
>
> **Current runnable slice:** today the AppHost launches `ATrade.Api`,
> `ATrade.Ibkr.Worker`, and the Next.js frontend home page; declares
> `Postgres`, `TimescaleDB`, `Redis`, and `NATS` as managed infrastructure
> resources; forwards the safe IBKR/iBeam paper-trading environment contract into
> `api` / `ibkr-worker`; can add the optional `ibkr-gateway` `voyz/ibeam:latest`
> container only when ignored `.env` credentials enable integration; and keeps the browser-facing backend slice focused on
> `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/search`, `GET /api/market-data/{symbol}/candles`,
> `GET /api/market-data/{symbol}/indicators`, `GET /api/analysis/engines`,
> `POST /api/analysis/run`, `GET` / `PUT` / `POST`
> `/api/workspace/watchlist`, exact `DELETE`
> `/api/workspace/watchlist/pins/{instrumentKey}`, legacy `DELETE`
> `/api/workspace/watchlist/{symbol}`, and `/hubs/market-data` while the worker limits itself to paper-safe
> session/status monitoring. `/api/market-data/trending`, candle, and indicator
> HTTP reads now use TimescaleDB first when rows are fresh under
> `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`; because the AppHost `timescaledb`
> resource is volume-backed, fresh cache rows can survive full local AppHost
> reboots and serve `timescale-cache:*` responses without another provider call.
> Misses or stale rows refresh from IBKR/iBeam and persist the provider response
> before returning it.

## 1. How To Read This Document

Each module entry below records four fields:

- **Purpose** — the single reason the module exists.
- **Responsibilities** — the concrete capabilities the module owns.
- **Expected dependencies** — other ATrade modules and infrastructure
  resources the module relies on, named using the components defined in
  `overview.md` (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) and in
  `README.md` → *Stack Contract*.
- **First-phase focus** — where `IBKR` (broker and current market data),
  Polygon, and later analysis providers enter the picture, if at all.

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
  `Postgres` / `Redis` / `NATS` references; backs the primary `postgres` data
  directory with the named `ATRADE_POSTGRES_DATA_VOLUME` volume and a stable
  `ATRADE_POSTGRES_PASSWORD` secret parameter so workspace preferences survive
  full local AppHost reboots; backs the `timescaledb` data directory with the
  named `ATRADE_TIMESCALEDB_DATA_VOLUME` volume and stable
  `ATRADE_TIMESCALEDB_PASSWORD` secret parameter so fresh market-data cache rows
  survive full local AppHost reboots; forwards the safe paper-mode IBKR/iBeam environment
  contract to the API and worker through redacted Aspire parameters; and only
  declares the optional `ibkr-gateway` `voyz/ibeam:latest` container when broker
  integration is enabled and fake credential placeholders have been replaced in
  ignored `.env`; the iBeam endpoint is modeled as HTTPS on the configured host
  gateway port while targeting the container's fixed Client Portal port `5000`,
  with a read-only repo-local iBeam inputs mount for loopback/private Docker
  bridge callers — see `src/ATrade.AppHost/Program.cs` and
  `src/ATrade.AppHost/ibeam-inputs/conf.yaml`. It also reads the safe LEAN
  runtime contract from the same local `.env`/`.env.template` source, forwards
  LEAN settings into `api`, and declares the optional Aspire-visible
  `lean-engine` container only when `ATRADE_ANALYSIS_ENGINE=Lean` and
  `ATRADE_LEAN_RUNTIME_MODE=docker` are selected.
- **First-phase focus:** Hosts the IBKR and Polygon integrations via the
  modules below.

### 2.2 `ATrade.ServiceDefaults` *(exists today)*

- **Purpose:** Shared hosting defaults and local runtime contract resolution for
  every .NET process in the solution.
- **Responsibilities:** OpenTelemetry wiring, default health checks,
  HTTP/gRPC resilience handlers, service discovery integration, and the shared
  local runtime contract loader that parses `.env.template`/ignored `.env`,
  applies process-environment overrides, validates local ports and Docker volume
  names, exposes resolved runtime settings, and classifies database passwords plus
  IBKR credential/account-id values as secret.
- **Expected dependencies:** None within ATrade; referenced by every other
  .NET module.
- **First-phase focus:** Own the shared local-development runtime contract seam
  consumed by direct API startup and the AppHost.

### 2.3 `ATrade.Api` *(exists today, paper-safe backend slice)*

- **Purpose:** The single public HTTP surface for the Next.js frontend and
  any future external clients.
- **Responsibilities:** In the current slice, provide an ASP.NET Core host
  that uses `ATrade.ServiceDefaults`, composes the Accounts, Orders, IBKR
  broker, MarketData, Analysis, and Workspaces modules, and exposes stable `GET /health`,
  `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`,
  `POST /api/orders/simulate`, `GET /api/market-data/trending`,
  `GET /api/market-data/search?query=...&assetClass=stock&limit=...`,
  `GET /api/market-data/{symbol}/candles?range=...`,
  `GET /api/market-data/{symbol}/indicators?range=...`,
  `GET /api/analysis/engines`, `POST /api/analysis/run`, `GET /api/workspace/watchlist`,
  `PUT /api/workspace/watchlist`, `POST /api/workspace/watchlist`, exact
  `DELETE /api/workspace/watchlist/pins/{instrumentKey}`, legacy
  `DELETE /api/workspace/watchlist/{symbol}`, and `/hubs/market-data`. The overview endpoint still returns deterministic
  bootstrap JSON from `ATrade.Accounts` (`module`, `status`,
  `brokerConnection`, `accounts`); the broker status endpoint resolves the
  provider-neutral `IBrokerProvider` contract and projects the safe IBKR/iBeam status
  shape without leaking usernames, passwords, tokens, session cookies, or account ids; the simulation endpoint returns deterministic
  paper-only fills while making live broker order placement impossible by
  construction; and the market-data endpoints/hub depend on compatibility
  services over `IMarketDataProvider` / `IMarketDataStreamingProvider` while
  returning IBKR/iBeam scanner, stock search, snapshot, historical candle,
  indicator, source metadata, and provider-unavailable/authentication-required
  payloads without a production fallback provider. For trending, candle, and
  indicator HTTP paths, API composition wraps the provider-backed service with
  `ATrade.MarketData.Timescale`, reads fresh Timescale rows before provider
  access, persists provider responses on cache misses, and labels cache hits with
  `timescale-cache:{originalSource}` source metadata. Candle/indicator endpoints
  prefer `range` / `chartRange` and retain legacy `timeframe` as a query-name
  alias for normalized chart range values. The analysis endpoints resolve
  `IAnalysisEngineRegistry` for discovery and `IAnalysisRequestIntake` for runs,
  so `ATrade.Analysis` owns symbol/range (`timeframe` payload field) defaults,
  candle acquisition through the cache-aware `IMarketDataService` seam, symbol
  identity resolution, invalid-request/provider-error mapping, and engine handoff before
  the API projects the HTTP result. The watchlist endpoints resolve
  `IWorkspaceWatchlistIntake`, so `ATrade.Workspaces` owns the temporary local
  workspace identity, idempotent schema initialization ordering, exact
  provider/market pin normalization, exact unpin validation, Postgres
  persistence, stable `instrumentKey`/`pinKey` metadata payloads, and stable
  validation/storage error shapes while the API only binds HTTP requests and
  projects HTTP responses. The AppHost now injects runtime connection
  information for `Postgres`, `TimescaleDB`, `Redis`, and `NATS`; the API
  consumes `Postgres` for workspace watchlists and `TimescaleDB` for fresh
  market-data cache-aside reads today. Later slices add authenticated
  REST/streaming endpoints for deeper accounts, charts, strategies, and broader
  market-data queries plus translation of HTTP requests into module calls and
  NATS publications.
- **Expected dependencies:** `ATrade.ServiceDefaults`, `ATrade.Accounts`,
  `ATrade.Brokers`, `ATrade.Brokers.Ibkr`, `ATrade.Orders`,
  `ATrade.MarketData`, `ATrade.MarketData.Ibkr`, `ATrade.Analysis`,
  `ATrade.Analysis.Lean`, and `ATrade.Workspaces` today for functional behavior;
  the current AppHost graph also provides `Postgres`, `TimescaleDB`, `Redis`,
  `NATS`, and optional LEAN Docker-mode environment handoff / workspace mapping
  information. `Postgres` is consumed by `ATrade.Workspaces`
  now; the other infrastructure references remain ready for later slices.
- **First-phase focus:** The backend now proves the paper-safe composition
  pattern: official IBKR session status, deterministic order simulation,
  IBKR/iBeam-backed market-data HTTP/SignalR surfaces with safe unavailable
  states, provider-neutral analysis discovery/run contracts with an explicit
  no-engine fallback plus optional LEAN execution, and Postgres-backed workspace watchlists for the frontend workspace.

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

### 2.6 `ATrade.Brokers` *(exists today, provider-neutral broker contracts)*

- **Purpose:** Broker provider abstraction shared by API, workers, and concrete
  broker adapters.
- **Responsibilities:** Define `IBrokerProvider`, provider identity,
  capabilities, account-mode strings, provider states (including
  `credentials-missing` and `ibeam-container-configured`), and safe status payloads
  without embedding IBKR-specific gateway types. The contract exposes session
  status and read-only capability flags while making unsupported order
  placement explicit.
- **Expected dependencies:** None within ATrade; concrete broker modules depend
  on it.
- **First-phase focus:** Keep `ATrade.Api` and worker status handling stable as
  IBKR/iBeam runtime details evolve behind the adapter.

### 2.7 `ATrade.MarketData` *(exists today, provider-neutral market-data slice)*

- **Purpose:** Market data ingestion, storage, and query.
- **Responsibilities:** In the current slice, provide provider-neutral async
  market-data provider/read contracts, provider identity/capability/status
  models, `MarketDataReadResult<T>` / `MarketDataError` result shapes, the
  `ExactInstrumentIdentity` helper that owns normalization/defaulting/key
  encoding/equality for provider/market identity, symbol identity and stock-search
  contracts, OHLCV candle and indicator payload shapes with source metadata,
  `ChartRangePresets` for `1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`,
  `5y`, and `all` lookbacks from now, compatibility services for the existing
  HTTP/SignalR API, moving-average / RSI / MACD indicator calculations,
  transparent trending factors, and a SignalR hub/snapshot service consumed by
  `ATrade.Api`. Search results, provider-backed
  trending symbols, candles, indicators, and latest updates include provider,
  provider symbol id, asset class, exchange, currency, and name/identity metadata
  where available so UI/watchlist/chart payloads remain provider-neutral.
  Concrete providers are registered by composition; production no
  longer ships a deterministic market-data provider or catalog fallback. The
  Timescale persistence and cache-aside integration now live in
  `ATrade.MarketData.Timescale`; API trending, search, symbol, candle,
  indicator, latest-update, SignalR snapshot, and analysis candle callers await
  the async seam, and cache-aware reads can use fresh stored rows keyed by
  normalized chart range before refreshing from providers. Future slices may
  publish real-time updates onto NATS for API / SignalR projection and cache hot
  reads in Redis.
- **Expected dependencies:** No external runtime services in the contract module
  beyond composition into `ATrade.Api`; concrete providers such as
  `ATrade.MarketData.Ibkr` depend on broker/iBeam configuration and gateway
  clients.
- **First-phase focus:** Keep HTTP/SignalR payloads provider-neutral while the
  current workspace uses the IBKR/iBeam provider behind this boundary.

#### 2.7.1 `ATrade.MarketData.Timescale` *(exists today, Timescale persistence and cache-aside)*

- **Purpose:** Provider-neutral TimescaleDB storage and API cache-aside for
  market-data time series.
- **Responsibilities:** Own the `atrade_market_data` schema, idempotent
  Timescale initialization for candle and scanner/trending snapshot hypertables,
  repository contracts for upserting/reading fresh candle series and trending
  snapshots, typed cache freshness options from
  `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`, and the async
  `IMarketDataService` decorator used by `ATrade.Api`. Storage records provider metadata as generic
  `provider` / `provider_symbol_id` fields plus symbol, exchange, currency,
  asset class, source, generated/observed timestamps, and write timestamps.
  Fresh reads keep bare-symbol compatibility and can additionally filter by exact
  provider symbol id / exchange / currency / asset class when callers supply
  identity metadata. The decorator awaits fresh rows before provider calls for
  trending, candles, and indicator candle inputs; writes provider responses after
  cache misses or stale rows without sync-over-async; returns cache hits with
  `timescale-cache:{originalSource}` source
  metadata after verifying the cached candles match the requested normalized
  chart range and lookback semantics; and falls back to provider behavior when
  Timescale storage is unavailable. AppHost persists the `timescaledb` data directory in
  `ATRADE_TIMESCALEDB_DATA_VOLUME` (default `atrade-timescaledb-data`) with a
  stable `ATRADE_TIMESCALEDB_PASSWORD`, so fresh cache rows survive full local
  AppHost restarts while stale rows still require provider refresh.
- **Expected dependencies:** `ATrade.MarketData`, `TimescaleDB` via
  AppHost-provided `ConnectionStrings:timescaledb`, .NET configuration/DI
  abstractions, and `Npgsql`. The storage/repository layer intentionally does not
  depend on `ATrade.Api`, frontend types, or concrete provider modules such as
  `ATrade.MarketData.Ibkr`; only API composition wires the cache-aside decorator
  around the provider-backed service.
- **First-phase focus:** Serve browser-facing market-data HTTP reads from fresh
  persisted provider rows when available, including after AppHost reboot when
  the rows remain inside the freshness window, refresh and persist IBKR/iBeam
  data on miss/stale reads, and preserve safe provider-unavailable behavior when
  neither fresh cache nor provider data is available.

### 2.8 `ATrade.Analysis` *(exists today, provider-neutral analysis engine seam)*

- **Purpose:** Analysis engine abstraction for strategy analysis, signals,
  metrics, and backtest summaries without coupling API/frontend contracts to a
  concrete runtime.
- **Responsibilities:** Define `IAnalysisEngine`, `IAnalysisEngineRegistry`,
  `IAnalysisRequestIntake`, engine metadata/capability/status shapes,
  HTTP-facing provider-neutral `AnalysisRunRequest` / `AnalysisRunIntakeResult`
  intake records, normalized `AnalysisRequest` and `AnalysisResult` records,
  signal/metric/backtest output contracts, and the `NoConfiguredAnalysisEngine`
  fallback. The intake owns symbol/range (`timeframe` payload field) defaults,
  direct-bar validation, cache-aware candle acquisition through `IMarketDataService`,
  symbol identity resolution/fallback, invalid-request and provider-error propagation, and
  engine handoff. The current API surface exposes `GET /api/analysis/engines`
  and `POST /api/analysis/run`; with no selected provider, run requests return
  `analysis-engine-not-configured` with empty signals, metrics, and backtest
  output.
- **Expected dependencies:** `ATrade.MarketData` for normalized
  `MarketDataSymbolIdentity` and `OhlcvCandle` inputs; composed by
  `ATrade.Api`. Concrete providers such as `ATrade.Analysis.Lean` may depend on
  external runtimes, but this contract module must remain provider-neutral.
- **First-phase focus:** Provide the seam that LEAN now implements without
  making LEAN an API, frontend, or core contract assumption.

### 2.8.1 `ATrade.Analysis.Lean` *(exists today, first analysis provider)*

- **Purpose:** LEAN adapter behind the provider-neutral analysis engine seam.
- **Responsibilities:** Bind safe LEAN runtime options, generate temporary LEAN
  project workspaces from ATrade-normalized OHLCV bars, execute the configured
  official LEAN CLI or the AppHost-managed Docker runtime (`lean-engine` via
  `docker exec` with a shared workspace mount), parse the emitted analysis result
  marker, and return provider-neutral signals, metrics, and backtest summaries.
  Docker mode without managed-container metadata, a missing container, runtime
  timeouts, non-zero exits, and parse failures become explicit
  `analysis-engine-unavailable` results rather than hidden fallback success. The
  generated algorithm is analysis-only and guardrails reject brokerage,
  live-mode, order-placement, and ATrade order-endpoint calls.
- **Expected dependencies:** `ATrade.Analysis`, `ATrade.MarketData`, .NET
  hosting/configuration abstractions, and either an optional local official LEAN
  CLI or the AppHost-managed `lean-engine` container selected through ignored
  `.env` values.
- **First-phase focus:** Provide moving-average crossover analysis/backtest
  output over the same market-data-provider bars the API and frontend already
  use, while cleanly reporting runtime-unavailable/timeout states.

### 2.9 `ATrade.Workspaces` *(exists today, first backend-owned preference slice)*

- **Purpose:** Workspace preference and personalization persistence.
- **Responsibilities:** Own the local user/workspace identity abstraction,
  `IWorkspaceWatchlistIntake` request orchestration, symbol
  normalization/validation delegated to
  `ATrade.MarketData.ExactInstrumentIdentity`, exact instrument-key validation,
  idempotent Postgres schema initialization ordering, stable watchlist error
  shapes, and repository operations for pinned watchlist instruments. The current schema
  stores `user_id`, `workspace_id`, durable `instrument_key`, normalized symbol,
  provider, optional provider symbol id / IBKR `conid`, display name, exchange,
  currency, asset class, sort order, and timestamps. It deduplicates only exact
  provider/market instrument keys, allowing the same symbol or company name to
  be pinned for multiple exchanges/currencies, and rejects legacy symbol deletes
  when they would be ambiguous. The local identity provider is explicitly
  temporary until authentication and named workspaces are introduced.
- **Expected dependencies:** `ATrade.MarketData` for backend-owned exact
  identity normalization/key construction, `Postgres` via the AppHost-provided
  `ConnectionStrings:postgres`, `Microsoft.Extensions.Configuration`,
  `Microsoft.Extensions.DependencyInjection`, and `Npgsql`. The AppHost-managed
  Postgres data directory is volume-backed so these preferences survive full
  local `start run` / AppHost restarts when the same volume and stable password
  are reused. `ATrade.Workspaces` is composed by `ATrade.Api`; it does not call
  brokers or market-data providers directly.
- **First-phase focus:** Persist backend-owned exact stock/instrument watchlists
  across API/server restarts and full local AppHost reboots while keeping symbol
  metadata provider-neutral.

### 2.10 `ATrade.Strategies` *(planned)*

- **Purpose:** Strategy definition, evaluation, and signal generation.
- **Responsibilities:** Persist strategy definitions and parameters;
  evaluate strategies against live and historical market data; emit
  signals that `ATrade.Orders` may act on.
- **Expected dependencies:** `Postgres` (definitions), `TimescaleDB`
  (evaluation traces), `NATS` (signal publication), `ATrade.MarketData`,
  `ATrade.ServiceDefaults`.
- **First-phase focus:** Swing/position strategies evaluated against
  Polygon bars or provider-neutral analysis requests. LEAN plugs in through
  `ATrade.Analysis` as a signal/backtest provider seam, not as an API or
  frontend dependency.

### 2.11 `ATrade.Brokers.Ibkr` *(exists today, first broker slice)*

- **Purpose:** IBKR broker adapter behind the provider-neutral broker contract.
- **Responsibilities:** In the current slice, bind typed paper-mode broker/iBeam
  options, enforce a paper-only guard, expose the official Gateway/iBeam
  auth-status client boundary over the shared HTTPS/local-certificate transport,
  own the normalized IBKR/iBeam readiness result, implement
  `ATrade.Brokers.IBrokerProvider` by projecting that readiness into safe broker
  status/capability shapes, redact credential-bearing env values, and keep order
  placement, credential storage, unofficial SDKs, and persistence out of scope. Later
  explicitly reviewed slices may translate
  approved paper-only order intents into IBKR API calls and surface the
  results back onto NATS.
- **Expected dependencies:** Shared hosting/configuration abstractions today;
  consumed directly by `ATrade.Api` and `ATrade.Ibkr.Worker`. Future slices
  may additionally use `NATS` and `Redis` for broker event publication and
  rate-limit counters. Paired with `ATrade.Ibkr.Worker` under `workers/`.
- **First-phase focus:** Provide the paper-only broker seam: session status
  first, paper-safe data next, and no live-trading behavior.

### 2.12 `ATrade.MarketData.Ibkr` *(exists today, first real market-data provider)*

- **Purpose:** IBKR/iBeam market-data adapter behind the provider-neutral
  market-data contract.
- **Responsibilities:** Translate official Client Portal/iBeam auth status,
  contract search/detail, snapshot, historical bar, and scanner responses into
  ATrade market-data payloads; expose `ibkr-ibeam-*` source metadata; implement
  `IMarketDataProvider` and `IMarketDataStreamingProvider`; reuse broker/iBeam
  gateway configuration, the shared readiness module, and the shared
  HTTPS/local-certificate transport without reading credentials directly; and
  return safe provider-not-configured/provider-unavailable/authentication-required
  errors when iBeam is disabled, missing credentials, unauthenticated, degraded,
  timed out, or unreachable.
- **Expected dependencies:** `ATrade.MarketData`, `ATrade.Brokers.Ibkr`, and
  the local `voyz/ibeam:latest` Client Portal runtime when integration is
  enabled through ignored `.env` values.
- **First-phase focus:** Real paper-safe market data for the paper-trading
  workspace without production mock fallback.

### 2.13 `ATrade.MarketData.Polygon` *(planned)*

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
  credentials-missing / not-configured / iBeam-container-configured / connecting /
  authenticated / degraded / error states from the shared IBKR/iBeam readiness
  module, and fails fast on rejected live-mode requests before any broker call.
  When paper mode is enabled and credentials are present, it polls the official
  auth-status endpoint through that readiness module; when disabled, it remains
  idle. The AppHost now wires
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
  account views, API-served IBKR/iBeam market data with fresh Timescale cache
  hits when available, clear provider-not-configured/provider-unavailable/
  authentication-required states, and transparent trending-factor/source
  explanations. The current frontend shell is the clean-room ATrade Terminal
  described in [`atrade-terminal-ui.md`](../design/atrade-terminal-ui.md):
  `frontend/types/terminal.ts` and `frontend/lib/terminalModuleRegistry.ts` own
  enabled modules (`HOME`, `SEARCH`, `WATCHLIST`, `CHART`, `ANALYSIS`, `STATUS`,
  `HELP`) plus visible-disabled future modules (`NEWS`, `PORTFOLIO`, `RESEARCH`,
  `SCREENER`, `ECON`, `AI`, `NODE`, `ORDERS`); `frontend/lib/terminalCommandRegistry.ts`
  owns deterministic local parsing for `HOME`, `SEARCH <query>`, `CHART <symbol>`,
  `WATCH` / `WATCHLIST`, `ANALYSIS <symbol>`, `STATUS`, and `HELP`; and
  `frontend/lib/terminalLayoutPersistence.ts` owns versioned local-only layout
  preferences under `atrade.terminal.layout.v1`. Home and symbol routes now render
  through `ATradeTerminalApp`, `TerminalCommandInput`, `TerminalModuleRail`,
  `TerminalWorkspaceLayout`, `TerminalStatusStrip`, `TerminalHelpModule`, and
  `TerminalStatusModule` instead of the retired `TerminalWorkspaceShell` /
  `WorkspaceCommandBar` / `WorkspaceNavigation` / `WorkspaceContextPanel`
  primitives. The app keeps the existing workflow hooks for watchlist migration /
  exact pin commands, search debounce/provider errors/bounded result view models,
  chart range loading/source labels/SignalR-to-HTTP fallback, and provider-neutral
  analysis while presenting disabled modules with honest unavailable states and
  no order-entry controls.
- **UI stack foundation:** `frontend/tailwind.config.ts`,
  `frontend/postcss.config.mjs`, `frontend/components.json`, and
  `frontend/lib/utils.ts` establish the Tailwind/PostCSS/shadcn-compatible
  styling substrate, local `@/*` aliases, and `cn()` class merging helper for
  downstream terminal modules. Minimal shadcn-style wrappers live under
  `frontend/components/ui/` and are limited to reusable Radix/accessibility
  primitives (button, input, badge, tabs, dialog, popover, scroll area,
  separator, and tooltip) with ATrade Terminal tokens applied. Original
  ATrade-only foundation components live under `frontend/components/terminal/`
  (`TerminalSurface`, `TerminalPanel`, `TerminalSectionHeader`,
  `TerminalStatusBadge`, `ATradeTerminalApp`, `TerminalCommandInput`,
  `TerminalModuleRail`, `TerminalWorkspaceLayout`, `TerminalStatusStrip`,
  `TerminalHelpModule`, `TerminalStatusModule`, and `TerminalDisabledModule`) and
  intentionally avoid legacy page-shell layout assumptions, backend access,
  provider runtime calls, order-entry behavior, or third-party terminal branding.

## 5. Dependency Summary

The expected intra-repo dependency direction is:

```text
frontend (Next.js)
    │  HTTP / streaming
    ▼
ATrade.Api ──► ATrade.Accounts
          ├──► ATrade.Brokers ◄──── ATrade.Brokers.Ibkr ◄── ATrade.Ibkr.Worker
          ├──► ATrade.Orders ─────────────────────────────┘
          ├──► ATrade.Workspaces ──► Postgres
          ├──► ATrade.Analysis ──► ATrade.MarketData
          ├──► ATrade.Strategies ◄── strategy-worker
          └──► ATrade.MarketData ◄──── ATrade.MarketData.Ibkr
                              ├──► ATrade.MarketData.Timescale ──► TimescaleDB
                              └──► ATrade.MarketData.Polygon ◄── polygon-worker

All modules ──► ATrade.ServiceDefaults
All modules ──► Postgres / TimescaleDB / Redis / NATS (as noted above)
```

No backend module may reach "up" into `ATrade.Api` or "sideways" between
brokers and data providers directly — broker modules normalize through
`ATrade.Brokers`, market-data modules normalize through `ATrade.MarketData`,
analysis engines normalize through `ATrade.Analysis`, and cross-module events
publish and consume provider-neutral shapes on `NATS`.

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
or data focus requires a maintainer-approved edit to this document and a
matching update to `overview.md` and, where structure changes, `README.md`
— per the Documentation Contract in `AGENTS.md`.
