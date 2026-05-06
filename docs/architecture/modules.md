---
status: active
owner: maintainer
updated: 2026-05-06
summary: Target module map for the ATrade modular monolith covering `src/`, `workers/`, and `frontend/` with provider-neutral broker, account-capital, and market-data seams.
see_also:
  - ../INDEX.md
  - ../design/atrade-terminal-ui.md
  - overview.md
  - provider-abstractions.md
  - analysis-engines.md
  - backtesting.md
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
> `src/ATrade.Backtesting`, `src/ATrade.Workspaces`, and
> `workers/ATrade.Ibkr.Worker` now exist.
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
> metadata, rich backtest detail contracts, and no-configured-engine fallback.
> `ATrade.Analysis.Lean` now implements LEAN as the first analysis engine
> provider behind that seam using a generated analysis-only LEAN workspace,
> AppHost-managed Docker metadata when Docker mode is selected, parameterized
> built-in strategy simulation, and safe runtime-unavailable states.
> `ATrade.Accounts` now also owns the provider-neutral paper-capital contract,
> Postgres-backed local paper-capital fallback ledger, and `IPaperCapitalService`
> selection flow that prefers an authenticated IBKR paper balance before local
> fallback and explicit unavailable states. `ATrade.Backtesting` owns saved
> asynchronous single-symbol backtest run contracts, built-in strategy/parameter
> validation, cost/slippage/benchmark snapshots, rich completed result envelopes,
> Postgres-backed run history, capital-source snapshots, an API-hosted runner
> with restart recovery, server-side market-data/analysis execution, best-effort
> cancellation, `/hubs/backtests` SignalR updates, and secret/direct-bar/runtime
> detail redaction. `ATrade.Workspaces` owns the first
> backend-persisted workspace preference: Postgres-backed exact instrument
> watchlists with stable `instrumentKey`/`pinKey` payloads derived from provider,
> provider id / IBKR `conid`, symbol, exchange, currency, and asset class, plus a
> temporary local
> user / workspace identity seam. The remaining modules and workers listed below stay
> aspirational and will land in later milestones tracked by `PLAN.md`. The
> `frontend/` directory now hosts the first paper-trading workspace UI slice,
> and the target frontend reconstruction is governed by
> [`docs/design/atrade-terminal-ui.md`](../design/atrade-terminal-ui.md): a
> clean-room ATrade paper workspace with enabled API-backed modules,
> visible-disabled future modules, purpose-matched rail icons, local icon-first
> rail collapse behavior, direct workflow navigation, a simplified full-viewport
> layout, and shadcn/Tailwind/Radix-compatible original primitives.
> The current slice routes home and symbol pages through `ATradeTerminalApp`: an
> enabled/disabled module registry and rail with icon metadata, a rail-first
> full-bleed single-primary `TerminalWorkspaceLayout` with no top app brand header, visible
> global safety strip, context/monitor shell chrome, footer/status strip,
> splitters, layout reset, or page-level vertical scrolling, status/help
> surfaces, and a dense terminal market monitor over backend-driven trending
> symbols, bounded/ranked/compact-filterable IBKR stock search, and
> Postgres-backed exact watchlists plus terminal chart/analysis/backtest
> workspaces.
> `TerminalMarketMonitor`,
> `MarketMonitorTable`, `MarketMonitorSearch`, `MarketMonitorFilters`, and
> `MarketMonitorDetailPanel` replace the old long/list search, trending, and
> watchlist renderers while preserving exact identity for chart/analysis/backtest
> actions. `TerminalChartWorkspace`, `TerminalInstrumentHeader`, and
> `TerminalIndicatorGrid` own the chart module around the reusable
> `CandlestickChart`; `TerminalAnalysisWorkspace` owns provider-neutral analysis
> states; `TerminalBacktestWorkspace` owns saved backtest run/capital/history
> states; and `TerminalProviderDiagnostics` replaces the old broker status card.
> The `frontend/lib/*Workflow.ts` hooks continue to centralize watchlist,
> bounded search result view models, terminal monitor rows/actions, chart range
> loading, source labeling, streaming fallback orchestration, analysis engine
> discovery/run view models, and backtest capital/history/status workflows behind
> the terminal frame.
>
> **Current runnable slice:** today the AppHost launches `ATrade.Api`,
> `ATrade.Ibkr.Worker`, and the Next.js frontend home page; declares
> `Postgres`, `TimescaleDB`, `Redis`, and `NATS` as managed infrastructure
> resources; forwards the safe IBKR/iBeam paper-trading environment contract into
> `api` / `ibkr-worker`; can add the optional `ibkr-gateway` `voyz/ibeam:latest`
> container only when ignored `.env` credentials enable integration; and keeps the browser-facing backend slice focused on
> `GET /health`, `GET /api/accounts/overview`, `GET /api/accounts/paper-capital`,
> `PUT /api/accounts/local-paper-capital`, `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/search`, `GET /api/market-data/{symbol}/candles`,
> `GET /api/market-data/{symbol}/indicators`, `GET /api/analysis/engines`,
> `POST /api/analysis/run`, `POST /api/backtests`, `GET /api/backtests`,
> `GET /api/backtests/{id}`, `POST /api/backtests/{id}/cancel`,
> `POST /api/backtests/{id}/retry`, `GET` / `PUT` / `POST`
> `/api/workspace/watchlist`, exact `DELETE`
> `/api/workspace/watchlist/pins/{instrumentKey}`, legacy `DELETE`
> `/api/workspace/watchlist/{symbol}`, `/hubs/market-data`, and
> `/hubs/backtests` while the worker limits itself to paper-safe session/status
> monitoring. `/api/market-data/trending`, candle, and indicator
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
  broker, MarketData, Analysis, Backtesting, and Workspaces modules, and exposes stable `GET /health`,
  `GET /api/accounts/overview`, `GET /api/accounts/paper-capital`,
  `PUT /api/accounts/local-paper-capital`, `GET /api/broker/ibkr/status`,
  `POST /api/orders/simulate`, `GET /api/market-data/trending`,
  `GET /api/market-data/search?query=...&assetClass=stock&limit=...`,
  `GET /api/market-data/{symbol}/candles?range=...`,
  `GET /api/market-data/{symbol}/indicators?range=...`,
  `GET /api/analysis/engines`, `POST /api/analysis/run`, `POST /api/backtests`,
  `GET /api/backtests`, `GET /api/backtests/{id}`,
  `POST /api/backtests/{id}/cancel`, `POST /api/backtests/{id}/retry`,
  `GET /api/workspace/watchlist`, `PUT /api/workspace/watchlist`,
  `POST /api/workspace/watchlist`, exact `DELETE /api/workspace/watchlist/pins/{instrumentKey}`, legacy
  `DELETE /api/workspace/watchlist/{symbol}`, `/hubs/market-data`, and
  `/hubs/backtests`. The overview endpoint still returns deterministic
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
  projects HTTP responses. The backtest REST handlers resolve
  `IBacktestRunFactory`, `IBacktestRunRepository`, the backtesting schema
  initializer, and `IBacktestRunCancellationRegistry`, while the mapped
  `/hubs/backtests` surface publishes payloads through
  `IBacktestRunUpdatePublisher`; `ATrade.Backtesting` owns single-symbol request
  validation, built-in strategy ids, optional analysis engine ids, capital
  snapshotting through Accounts, saved-run Postgres persistence, async runner
  claim/recovery/finalization state, server-side market-data/analysis execution,
  cancel/retry status rules, SignalR update payload shape, and redaction of
  account identifiers, credentials, gateway URLs, LEAN workspace paths, raw
  process command lines, tokens, cookies, session details, direct bars, custom
  code, and order-routing fields. The paper-capital endpoints resolve
  `IPaperCapitalService`, so `ATrade.Accounts` owns local capital validation,
  Postgres schema initialization, stable storage-unavailable errors, IBKR-first
  effective-capital selection, and redaction; the API returns only the safe
  payload (`effectiveCapital`, `currency`, `source`, `ibkrAvailable`,
  `localConfigured`, `localCapital`, and `messages`) and never account ids,
  credentials, gateway URLs, tokens, cookies, or session details. The AppHost
  now injects runtime connection information for `Postgres`, `TimescaleDB`,
  `Redis`, and `NATS`; the API consumes `Postgres` for Accounts local
  paper-capital fallback storage and workspace watchlists, and `TimescaleDB` for
  fresh market-data cache-aside reads today. Later slices add authenticated
  REST/streaming endpoints for deeper accounts, charts, strategies, and broader
  market-data queries plus translation of HTTP requests into module calls and
  NATS publications.
- **Expected dependencies:** `ATrade.ServiceDefaults`, `ATrade.Accounts`,
  `ATrade.Brokers`, `ATrade.Brokers.Ibkr`, `ATrade.Orders`,
  `ATrade.MarketData`, `ATrade.MarketData.Ibkr`, `ATrade.Analysis`,
  `ATrade.Analysis.Lean`, `ATrade.Backtesting`, and `ATrade.Workspaces` today
  for functional behavior; the current AppHost graph also provides `Postgres`,
  `TimescaleDB`, `Redis`, `NATS`, and optional LEAN Docker-mode environment
  handoff / workspace mapping information. `Postgres` is consumed by
  `ATrade.Accounts` for local paper-capital fallback storage,
  `ATrade.Backtesting` for saved run history and async runner state, and
  `ATrade.Workspaces` for exact watchlists; the other infrastructure references
  remain ready for later slices.
- **First-phase focus:** The backend now proves the paper-safe composition
  pattern: official IBKR session status, deterministic order simulation,
  IBKR/iBeam-backed market-data HTTP/SignalR surfaces with safe unavailable
  states, provider-neutral analysis discovery/run contracts with an explicit
  no-engine fallback plus optional LEAN execution, first-class saved backtest
  APIs backed by Postgres run history, paper-capital snapshots, API-hosted async
  execution, restart recovery, cancellation, and SignalR job updates,
  Postgres-backed workspace watchlists for the frontend workspace, and
  paper-capital source selection without browser-visible broker account data.

### 2.4 `ATrade.Accounts` *(exists today, bootstrap overview plus paper-capital source)*

- **Purpose:** Account, portfolio, position, and paper-capital bookkeeping.
- **Responsibilities:** In the current slice, provide deterministic,
  bootstrap-safe `AccountOverview` response types and DI registration used by
  `ATrade.Api` to serve `GET /api/accounts/overview`; own the provider-neutral
  paper-capital response contract (`ibkr-paper-balance`, `local-paper-ledger`,
  and `unavailable` sources); validate `PUT /api/accounts/local-paper-capital`
  payloads as positive USD local fallback capital with sensitive provider fields
  rejected; initialize and persist the `atrade_accounts.local_paper_capital`
  Postgres table idempotently under the temporary `local-user` /
  `paper-trading` identity; compose `IIbkrPaperCapitalProvider` availability
  with the local ledger so `GET /api/accounts/paper-capital` prefers a safe
  authenticated IBKR paper balance, falls back to local capital, or returns an
  explicit unavailable state; and redact account identifiers, credentials,
  gateway URLs, tokens, cookies, and session details from messages and errors.
  The overview response intentionally remains bootstrap-safe (`module =
  "accounts"`, `status = "bootstrap"`, `brokerConnection = "not-configured"`,
  `accounts = []`). Future slices own the canonical account/portfolio/position
  schema, reconcile broker-reported state with internal state, and expose richer
  query and projection APIs.
- **Expected dependencies:** `Postgres` today for local paper-capital fallback
  storage, `ATrade.Brokers.Ibkr` through the provider-neutral
  `IIbkrPaperCapitalProvider` seam for authenticated paper-balance reads, and
  `ATrade.ServiceDefaults`. `NATS` joins later for execution/account events.
- **First-phase focus:** Provide a truthful initial-capital source for
  backtesting and future account workflows without fake account state or leaked
  broker identifiers.

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
  signal/metric/backtest output contracts including rich backtest details, and
  the `NoConfiguredAnalysisEngine` fallback. The intake owns symbol/range
  (`timeframe` payload field) defaults,
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
  marker, and return provider-neutral signals, metrics, backtest summaries,
  equity curves, simulated trades, benchmarks, and accounting details.
  Docker mode without managed-container metadata, a missing container, runtime
  timeouts, non-zero exits, and parse failures become explicit
  `analysis-engine-unavailable` results rather than hidden fallback success. The
  generated algorithm is analysis-only and guardrails reject brokerage,
  live-mode, order-placement, and ATrade order-endpoint calls.
- **Expected dependencies:** `ATrade.Analysis`, `ATrade.MarketData`, .NET
  hosting/configuration abstractions, and either an optional local official LEAN
  CLI or the AppHost-managed `lean-engine` container selected through ignored
  `.env` values.
- **First-phase focus:** Provide SMA crossover, RSI mean-reversion, and breakout
  analysis/backtest output over the same market-data-provider bars the API and
  frontend already use, while cleanly reporting runtime-unavailable/timeout
  states.

### 2.9 `ATrade.Backtesting` *(exists today, async runner and saved run persistence)*

- **Purpose:** Provider-neutral saved asynchronous backtest run contracts,
  validation, API-hosted execution, persistence, SignalR updates, and
  local-workspace API orchestration.
- **Responsibilities:** Own `BacktestCreateRequest`, normalized request
  snapshots, run ids, run statuses (`queued`, `running`, `completed`, `failed`,
  `cancelled`), built-in strategy ids, optional analysis engine ids,
  cost/slippage/benchmark options, capital snapshots, safe errors, retry source
  ids, SignalR update payloads, and saved run envelopes. Creation is
  single-symbol and stock-only, rejects direct browser-submitted bars, custom
  strategy code, multi-symbol/portfolio payloads, broker/order-routing fields,
  credentials, gateway URLs, tokens, cookies, session details, and account
  identifiers. The run factory snapshots effective paper capital from
  `ATrade.Accounts.IPaperCapitalService` and blocks creation when no positive
  source is available. The Postgres repository owns idempotent schema
  initialization, create/list/get/status/cancel/retry operations, queued-run
  claiming with duplicate-execution guards, startup interruption recovery,
  canonical request JSON persistence, rich result JSON envelopes, and safe
  storage errors. The hosted runner fetches candles server-side through
  `IMarketDataService`, invokes `IAnalysisEngineRegistry`, persists completed or
  failed terminal envelopes, and publishes best-effort `/hubs/backtests` updates.
- **Expected dependencies:** `ATrade.Accounts` for effective paper-capital source
  selection and temporary local user/workspace identity, `ATrade.MarketData` for
  symbol identity/chart range presets and server-side candle reads,
  `ATrade.Analysis` for provider-neutral analysis/LEAN engine invocation,
  `Postgres` via AppHost-provided `ConnectionStrings:postgres`,
  `Microsoft.AspNetCore.SignalR`, `Microsoft.Extensions.Configuration`,
  `Microsoft.Extensions.DependencyInjection`, and `Npgsql`. The module is
  composed by `ATrade.Api`; it does not call brokers, concrete LEAN process
  code, frontend code, or market-data providers directly.
- **First-phase focus:** Execute queued saved runs inside the API process,
  recover interrupted running jobs safely on restart, cancel queued/running jobs
  best-effort, persist and stream safe rich strategy result/error updates to
  browsers, and keep provider/runtime details out of browser contracts and
  persisted unsafe fields.

### 2.10 `ATrade.Workspaces` *(exists today, first backend-owned preference slice)*

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

### 2.11 `ATrade.Strategies` *(planned)*

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

### 2.12 `ATrade.Brokers.Ibkr` *(exists today, first broker slice)*

- **Purpose:** IBKR broker adapter behind the provider-neutral broker contract.
- **Responsibilities:** In the current slice, bind typed paper-mode broker/iBeam
  options, enforce a paper-only guard, expose the official Gateway/iBeam
  auth-status client boundary over the shared HTTPS/local-certificate transport,
  own the normalized IBKR/iBeam readiness result, implement
  `ATrade.Brokers.IBrokerProvider` by projecting that readiness into safe broker
  status/capability shapes, expose an Accounts-facing `IIbkrPaperCapitalProvider`
  that reads the configured paper account summary only after authenticated paper
  readiness, parse `/v1/api/portfolio/{configured paper account id}/summary`
  for `totalcashvalue` first and `netliquidation` second, redact
  credential-bearing env values and account identifiers, and keep order
  placement, credential storage, unofficial SDKs, and persistence out of scope.
  Later explicitly reviewed slices may translate approved paper-only order
  intents into IBKR API calls and surface the results back onto NATS.
- **Expected dependencies:** Shared hosting/configuration abstractions today;
  consumed directly by `ATrade.Api` and `ATrade.Ibkr.Worker`. Future slices
  may additionally use `NATS` and `Redis` for broker event publication and
  rate-limit counters. Paired with `ATrade.Ibkr.Worker` under `workers/`.
- **First-phase focus:** Provide the paper-only broker seam: session status
  first, paper-safe data and paper-balance reads next, and no live-trading
  behavior.

### 2.13 `ATrade.MarketData.Ibkr` *(exists today, first real market-data provider)*

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

### 2.14 `ATrade.MarketData.Polygon` *(planned)*

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
  explanations. The current frontend shell is the clean-room ATrade paper
  workspace described in [`atrade-terminal-ui.md`](../design/atrade-terminal-ui.md):
  `frontend/types/terminal.ts` and `frontend/lib/terminalModuleRegistry.ts` own
  enabled modules (`HOME`, `SEARCH`, `WATCHLIST`, `CHART`, `ANALYSIS`, `BACKTEST`,
  `STATUS`, `HELP`) plus visible-disabled future modules (`NEWS`, `PORTFOLIO`, `RESEARCH`,
  `SCREENER`, `ECON`, `AI`, `NODE`, `ORDERS`) and their purpose-matched rail
  icon metadata. Home and symbol routes now render directly through
  `ATradeTerminalApp`, `TerminalModuleRail`, `TerminalWorkspaceLayout`,
  `TerminalHelpModule`, and `TerminalStatusModule`; `TerminalModuleRail` keeps
  local non-persisted icon-first collapse state while preserving accessible
  labels, active/focus states, and disabled-module explanations.
  the simplified rail-first shell removed the former app-level brand header,
  visible global safety strip, context/monitor split-size persistence, shell
  monitor strip, context aside, footer/status strip, and layout reset. The old `TradingWorkspace`
  and `SymbolChartView` compatibility wrappers have been deleted, and the
  retired `TerminalWorkspaceShell` / `WorkspaceCommandBar` /
  `WorkspaceNavigation` / `WorkspaceContextPanel` primitives remain absent.
  `frontend/lib/terminalMarketMonitorWorkflow.ts` wraps the existing
  watchlist and symbol-search workflow hooks with provider-backed trending state,
  source/provider/market filters, sorting, selected-row state, bounded
  show-more/show-less exploration, exact pin state projection, and exact
  chart/analysis/backtest navigation intents; `frontend/components/terminal/TerminalMarketMonitor.tsx`
  and its table/search/compact-filter/detail components render that monitor for `HOME`,
  `SEARCH`, and `WATCHLIST`. `frontend/lib/terminalChartWorkspaceWorkflow.ts`
  adapts `symbolChartWorkflow` into terminal source/range/identity/stream view
  models consumed by `TerminalChartWorkspace`, `TerminalInstrumentHeader`, and
  `TerminalIndicatorGrid`; the chart module keeps `CandlestickChart` as a
  reusable low-level `lightweight-charts` renderer that receives measured
  non-zero dimensions, observes resize/layout changes, preserves the OHLC legend,
  volume, SMA overlays, fit-content, crosshair behavior, and cleanup, and is only
  mounted by `TerminalChartWorkspace` when actual candle rows exist. Empty candle
  arrays stay explicit no-data states instead of synthetic bars while
  `TimeframeSelector` and `IndicatorPanel` remain retired.
  `frontend/lib/terminalAnalysisWorkflow.ts` adapts `analysisClient`
  discovery/run behavior for `TerminalAnalysisWorkspace`, which
  replaces `AnalysisPanel`; `frontend/types/backtesting.ts`,
  `frontend/lib/backtestClient.ts`, and `frontend/lib/terminalBacktestWorkflow.ts`
  own the `BACKTEST` rail module's safe saved-run/capital contracts, ATrade.Api
  HTTP/SignalR calls, form validation, create/cancel/retry actions, history/detail
  selection, reconnect recovery, and no-fake-result status state for
  `TerminalBacktestWorkspace`; `TerminalProviderDiagnostics` replaces
  `BrokerPaperStatus` as diagnostics-only broker/IBKR/iBeam/source state. The
  old `SymbolSearch`, `TrendingList`, `Watchlist`, `MarketLogo`,
  `TimeframeSelector`, `IndicatorPanel`, `AnalysisPanel`, and
  `BrokerPaperStatus` renderers are retired and no longer exist as active
  frontend source files. Visible-disabled modules such as `NEWS`, `PORTFOLIO`,
  `RESEARCH`, `SCREENER`, `ECON`, `AI`, `NODE`, and `ORDERS` stay honest
  unavailable states rather than fake news, portfolio rows, research output,
  screeners, macro calendars, assistant text, node graphs, or order-entry
  controls. The cutover guardrail lives in
  `tests/apphost/frontend-terminal-cutover-tests.sh` alongside the no-command,
  top-chrome/filter-density, shell/market/chart/analysis/theme, backtest
  workspace, and module rail icon/collapse validation scripts.
- **UI stack foundation:** `frontend/tailwind.config.ts`,
  `frontend/postcss.config.mjs`, `frontend/components.json`, and
  `frontend/lib/utils.ts` establish the Tailwind/PostCSS/shadcn-compatible
  styling substrate, local `@/*` aliases, and `cn()` class merging helper for
  downstream terminal modules. Minimal shadcn-style wrappers live under
  `frontend/components/ui/` and are limited to reusable Radix/accessibility
  primitives (button, input, badge, tabs, dialog, popover, scroll area,
  separator, and tooltip) with the original black/graphite/amber ATrade
  workspace tokens applied. Original
  ATrade-only foundation components live under `frontend/components/terminal/`
  (`TerminalSurface`, `TerminalPanel`, `TerminalSectionHeader`,
  `TerminalStatusBadge`, `ATradeTerminalApp`, `TerminalModuleRail`,
  `TerminalWorkspaceLayout`, `TerminalHelpModule`, `TerminalStatusModule`,
  `TerminalChartWorkspace`, `TerminalInstrumentHeader`, `TerminalIndicatorGrid`,
  `TerminalAnalysisWorkspace`, `TerminalBacktestWorkspace`,
  `TerminalProviderDiagnostics`, and `TerminalDisabledModule`) and intentionally
  avoid legacy page-shell layout
  assumptions, backend access, provider runtime calls, order-entry behavior, or
  third-party terminal branding.

## 5. Dependency Summary

The expected intra-repo dependency direction is:

```text
frontend (Next.js)
    │  HTTP / streaming
    ▼
ATrade.Api ──► ATrade.Accounts ──► Postgres
          │              └────► ATrade.Brokers.Ibkr
          ├──► ATrade.Brokers ◄──── ATrade.Brokers.Ibkr ◄── ATrade.Ibkr.Worker
          ├──► ATrade.Orders ─────────────────────────────┘
          ├──► ATrade.Workspaces ──► Postgres
          ├──► ATrade.Backtesting ──► Postgres
          │              ├────► ATrade.Accounts
          │              ├────► ATrade.MarketData
          │              └────► ATrade.Analysis
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
