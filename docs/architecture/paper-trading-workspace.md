---
status: active
owner: maintainer
updated: 2026-05-05
summary: Authoritative paper-trading workspace architecture and paper-only configuration contract for the staged IBKR-backed trading UI slice.
see_also:
  - ../INDEX.md
  - ../design/atrade-terminal-ui.md
  - overview.md
  - modules.md
  - provider-abstractions.md
  - analysis-engines.md
  - ../../README.md
  - ../../PLAN.md
  - ../../scripts/README.md
---

# Paper-Trading Workspace Architecture

> **Status note:** This document defines the staged architecture and safety
> contract for the broader paper-trading workspace. The active frontend UI
> authority is [`docs/design/atrade-terminal-ui.md`](../design/atrade-terminal-ui.md):
> it governs the clean-room visual target, direct module/workflow navigation,
> simplified full-viewport layout, disabled future surfaces, and frontend
> replacement constraints while this document continues to govern paper-only safety and
> backend/API boundaries. The current repository now
> uses provider-neutral broker and market-data contracts with IBKR/iBeam as the
> first real market-data provider behind API/frontend-stable seams. The current
> repository ships `ATrade.Brokers.Ibkr` as a paper-only broker adapter,
> `ATrade.MarketData.Ibkr` as the IBKR/iBeam market-data provider,
> `ATrade.Api` endpoints for `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/search`, `GET /api/market-data/{symbol}/candles`, and
> `GET /api/market-data/{symbol}/indicators`, `GET /api/analysis/engines`,
> `POST /api/analysis/run`, a `/hubs/market-data` SignalR hub,
> backend-owned `GET` / `PUT` / `POST` / legacy symbol `DELETE`
> `/api/workspace/watchlist` endpoints plus exact
> `DELETE /api/workspace/watchlist/pins/{instrumentKey}` backed by the
> AppHost-managed Postgres resource, a TimescaleDB-backed market-data
> cache-aside path in `ATrade.MarketData.Timescale`, AppHost-driven paper-safe
> broker/iBeam configuration wiring, and a Next.js ATrade paper workspace
> with direct module/workflow navigation, enabled/disabled module registry and
> rail, a rail-first full-bleed single-primary workspace with no top app brand
> header, visible global safety strip, shell context panel, monitor strip,
> footer/status strip, resizable splitters, layout reset, or page-level vertical
> scrolling, IBKR scanner-driven or fresh persisted trending symbols,
> bounded/ranked/compact-filterable IBKR stock search, exact market-specific
> Postgres-backed watchlists, local market badges, terminal chart workspaces
> that reuse `lightweight-charts` candlesticks, chart range lookback controls
> (`1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, and All time),
> indicator grids, source/exact-identity metadata, terminal analysis workspaces
> that can run LEAN when the analysis runtime is configured, provider
> diagnostics, and SignalR-to-HTTP fallback behavior.
> Production mocked market-data providers have been removed; missing iBeam
> runtime, credentials, or authentication returns safe
> provider-not-configured/provider-unavailable/authentication-required errors
> rather than fallback data. Durable paper-order storage and real broker order
> placement remain future work.

## 1. Scope And Non-Negotiable Safety Rules

The paper-trading workspace is the first trading-oriented user experience for
ATrade. It must let the frontend present charts, watchlists, account state,
order entry, and trending symbols **without** creating any path to real
trading.

The slice is governed by five non-negotiable rules:

1. **Paper-only mode is the only supported broker mode.** Any committed
   default or documented example must stay in `Paper` mode.
2. **Real trades are forbidden.** No code path in this feature family may
   send a live order to IBKR or to any other broker.
3. **Official IBKR Gateway APIs are the only broker baseline.** No unofficial
   SDKs, screen scraping, or undocumented broker behaviors are part of this
   contract.
4. **Secrets stay in ignored local `.env` only.** Usernames, passwords,
   tokens, and real account identifiers must never be committed.
5. **Market/trending data must be honest about provider state.** Production
   market data now comes from the IBKR/iBeam provider through the provider
   abstraction layer. Missing local runtime, credentials, authentication, or
   degraded provider state must surface as safe not-configured/unavailable
   responses rather than silently falling back to synthetic data.

## 2. Product Shape

The target paper-trading workspace combines six user-facing areas inside the
Next.js application:

- account summary and connection health
- watchlists and symbol search
- TradingView-like price charts
- staged paper-order entry and order history
- positions and paper P/L views
- trending symbols and factor explanations

The workspace is intentionally **frontend-rich but backend-governed**:
Next.js owns layout and interaction, while the backend owns trading rules,
state transitions, data access, and streaming contracts. The current frontend
surface is the clean-room ATrade paper workspace defined in
[`atrade-terminal-ui.md`](../design/atrade-terminal-ui.md): a completed frontend
replacement with enabled modules for current API-backed workflows,
visible-disabled future modules, a rail-first simplified full-viewport
single-primary layout without a top app brand header or global visible safety
strip, and a responsive fallback. The home and symbol routes now render directly through
`ATradeTerminalApp`, which provides the direct module/workflow frame, module
rail, single primary workspace region, module-owned scrolling, STATUS/HELP
modules, and honest disabled-module surfaces for future modules
(`NEWS`, `PORTFOLIO`, `RESEARCH`, `SCREENER`, `ECON`, `AI`, `NODE`, and
`ORDERS`). Users open modules through the
rail, market-monitor chart/analysis actions, and symbol route state; no command
input, command parser, or backend command route is part of the active frontend.
The visual direction is inspired only by broad finance-workstation information
architecture and is implemented with original ATrade black/graphite/amber tokens,
red/green market-state colors, warm gray dividers, and restrained information
contrast; it does not copy proprietary terminal layouts, assets, trademarks, or
colors.

## 3. Runtime Boundaries

The paper-trading slice uses the existing ATrade modular-monolith topology.
No extra deployable services are introduced.

### 3.1 Next.js frontend

The `frontend/` application owns:

- route composition for the paper-trading workspace
- market monitor, chart, analysis, status, help, and provider/status widgets
- browser-side session state for active modules, non-authoritative watchlist
  cache/migration state, optimistic UI interactions, and route-local workflow
  state; the active shell no longer persists context/monitor split sizes or
  layout reset state
- SignalR subscriptions for market-data stream updates plus HTTP fallback; broker
  status is diagnostics-only and no order-entry or order-submit UI is rendered

The frontend does **not** talk directly to IBKR, Redis, NATS, Postgres, or
TimescaleDB. All durable and broker-aware behavior goes through the API.
Frontend orchestration is centralized in `frontend/lib/*Workflow.ts` modules so
rendering components receive normalized state and operations: `watchlistWorkflow`
owns backend watchlist loads, one-time symbol-only legacy cache migration,
read-only cached fallback, exact pin/unpin/remove operations, saving state, and
stable watchlist error copy; `symbolSearchWorkflow` owns search query debounce,
minimum-length validation, provider/authentication error copy, explicit bounded
search limits, ranked result view models, metadata filter state, short visible
result limits, and show-more/show-less exploration operations;
`terminalMarketMonitorWorkflow` wraps those hooks with provider-backed trending
state, unified dense row view models, local source/provider/pin filters, sorting,
selection, show-more/show-less row exploration, and exact chart/analysis action
intents while `MarketMonitorFilters` presents those filters as compact controls;
`symbolChartWorkflow` owns the selected chart range lookback,
candle/indicator HTTP reads, source-label formatting, SignalR subscription
state, stream update application, and HTTP polling fallback when streaming closes
or is unavailable; `terminalChartWorkspaceWorkflow` adapts that contract into
workspace-ready range/source/identity/stream view models, including
`hasCandleData` so empty candle arrays remain explicit no-data states;
`TerminalChartWorkspace` only mounts `CandlestickChart` when real candle rows
exist, and `CandlestickChart` measures/resizes its `lightweight-charts` canvas so
stock charts receive non-zero dimensions after module or viewport layout changes;
and `terminalAnalysisWorkflow` adapts `analysisClient` discovery/run behavior into
explicit no-engine, unavailable, running, and result states. The workspace frame
composes those workflow/client modules through `ATradeTerminalApp`,
`TerminalMarketMonitor`, `MarketMonitorTable`, `MarketMonitorSearch`,
`MarketMonitorFilters`, `MarketMonitorDetailPanel`, `TerminalChartWorkspace`,
`TerminalInstrumentHeader`, `TerminalIndicatorGrid`, `TerminalAnalysisWorkspace`,
`TerminalProviderDiagnostics`, `TerminalModuleRail`, and `TerminalWorkspaceLayout`;
the old `TradingWorkspace` / `SymbolChartView` route
wrappers, `SymbolSearch`, `TrendingList`, `Watchlist`, `MarketLogo`,
`TimeframeSelector`, `IndicatorPanel`, `AnalysisPanel`, and `BrokerPaperStatus`
renderers plus the retired `TerminalWorkspaceShell`, `WorkspaceCommandBar`,
`WorkspaceNavigation`, and `WorkspaceContextPanel` primitives are no longer
present as active route dependencies.

### 3.2 `ATrade.Api`

`ATrade.Api` remains the only browser-facing backend surface and expands with:

- HTTP endpoints for workspace bootstrap data, Postgres-backed watchlists,
  account state, paper orders, and chart history
- SignalR hubs that push account, order, quote, bar, and trending updates to
  the browser
- translation between browser workflow actions and internal module calls / NATS events
- enforcement of the paper-only guardrails described in this document

The current backend slice exposes `GET /api/broker/ibkr/status`,
`POST /api/orders/simulate`, `GET /api/market-data/trending`,
`GET /api/market-data/search?query=...&assetClass=stock&limit=...`,
`GET /api/market-data/{symbol}/candles?range=...`,
`GET /api/market-data/{symbol}/indicators?range=...`, `GET /api/workspace/watchlist`,
`PUT /api/workspace/watchlist`, `POST /api/workspace/watchlist`,
exact `DELETE /api/workspace/watchlist/pins/{instrumentKey}`, legacy
`DELETE /api/workspace/watchlist/{symbol}` for unambiguous symbol-only rows,
`GET /api/analysis/engines`, `POST /api/analysis/run`, and the
`/hubs/market-data` SignalR hub while keeping the browser-to-broker boundary
strictly server-side. The broker endpoint resolves the provider-neutral
`IBrokerProvider` contract. The market-data endpoints await the async
`IMarketDataService` read seam; in the current API composition that contract is a
Timescale-backed cache-aside service over the provider-backed `MarketDataService`
and the `ATrade.MarketData.Ibkr` provider.
Trending and candle requests initialize the Timescale schema idempotently, read
fresh rows newer than `now - ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` before
calling IBKR/iBeam, and return cache hits as the same provider-neutral payloads
with exact identity metadata and source metadata such as
`timescale-cache:ibkr-ibeam-history` or
`timescale-cache:ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN`. Candle and
indicator reads keep the legacy `/api/market-data/{symbol}/...` paths while
accepting `range` / `chartRange` query values and still accepting legacy
`timeframe` as a query-name alias. Supported chart range values are `1min`,
`5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, and `all`; they mean
lookbacks from the current time, so `1D` means the past day, `1m` means the past
month, and `6m` means the past six months. Optional `provider`,
`providerSymbolId`, `exchange`, `currency`, and `assetClass` query metadata is
accepted for exact cache filtering/chart handoff. The AppHost `timescaledb`
resource is backed by a named data volume, so those fresh rows can survive a full
`start run` / AppHost stop-start cycle and serve the API after reboot without
another provider call. Missing, stale, mismatched-range, or lookback-incompatible
rows trigger the provider-backed scanner/historical-bar fetch, persist the
provider response to TimescaleDB, and return the provider response; stale rows are
not silently promoted to success when provider refresh fails. Indicator requests
reuse the cache-aware candle path before computing moving average, RSI, and MACD
payloads for the same normalized chart ranges. The search endpoint remains
provider-backed, enforces a minimum query length, stock-only asset class, and a
capped result limit before returning provider-neutral `symbol`, `name`,
`assetClass`, `exchange`, `currency`, `provider`, and provider-symbol-id
metadata (IBKR `conid` for the current provider). The frontend always calls
this endpoint through `searchSymbols()` with an explicit capped limit, ranks
exact/best matches first, shows a short default list, and exposes market,
currency, and asset-class chips plus deliberate show-more/show-less controls
without fetching an unbounded browser result set. Pin and chart actions keep the
same provider, provider symbol id / IBKR `conid`, exchange, currency, and asset
class tuple. Provider-backed search, trending, candle, indicator, and
latest-update payloads carry `MarketDataSymbolIdentity` where available. SignalR
is the outward-facing streaming layer for browsers and awaits
`IMarketDataStreamingService`, which
owns provider-status checks and creates provider-backed snapshots when the
IBKR/iBeam provider is available. The analysis endpoints use
`IAnalysisEngineRegistry` for discovery and `IAnalysisRequestIntake` for runs;
the intake owns direct-bar validation, symbol/range (`timeframe` payload field)
defaults, async `IMarketDataService` candle reads, symbol identity resolution,
invalid-request / market-data error propagation, and engine handoff. With no
engine selected the
HTTP projection still returns explicit `analysis-engine-not-configured` metadata,
and when `ATRADE_ANALYSIS_ENGINE=Lean` the configured LEAN provider analyzes the
normalized bars; in Docker mode that provider uses the AppHost-managed
`lean-engine` runtime and returns explicit `analysis-engine-unavailable` errors
when the managed runtime is absent or unreachable. Watchlist endpoints use
`IWorkspaceWatchlistIntake`; Workspaces owns local identity use, schema
initialization ordering, pin/replace/unpin normalization, exact instrument-key
validation, and storage/validation error shapes while the API only binds and
projects HTTP requests. NATS remains the internal event backbone between API and workers.

### 3.3 Backend modules and workers

The paper-trading slice extends existing planned responsibilities as follows:

- `ATrade.Accounts` owns paper account projections, balances, positions, and
  broker-session summaries
- `ATrade.Brokers` owns the provider-neutral broker identity, capability,
  account-mode, and status contracts shared by API, worker, and adapters
- `ATrade.Brokers.Ibkr` owns typed paper-mode configuration, the official
  Gateway session/status client boundary, paper-only guardrails, the normalized
  IBKR/iBeam readiness result, and the safe `IBrokerProvider` projection used by
  the API
- `ATrade.Orders` owns paper-order validation, lifecycle state, and simulated
  fills; the current backend slice already returns deterministic simulated
  fills directly from this module
- `ATrade.MarketData` owns provider-neutral quote/bar contracts, provider
  status/error states, the `ExactInstrumentIdentity` backend normalization/key
  helper, chart range preset normalization/lookback semantics, symbol-search
  readiness hooks, historical chart queries, compatibility services, and SignalR
  snapshot contracts
- `ATrade.MarketData.Ibkr` owns the first real market-data provider: IBKR/iBeam
  Client Portal contract search/detail lookup, scanner/trending-equivalent
  mapping, snapshots, historical bars, indicator inputs, source metadata, and
  safe not-configured/unavailable/authentication-required responses projected
  from the shared IBKR/iBeam readiness result without reading credentials
  directly
- `ATrade.MarketData.Timescale` owns provider-neutral TimescaleDB persistence
  and the API cache-aside decorator for provider-backed OHLCV candle series and
  scanner/trending snapshots. It creates the `atrade_market_data` schema, stores
  provider metadata as generic `provider` / `provider_symbol_id` values plus
  symbol, exchange, currency, and asset class, exposes freshness-aware repository
  contracts with optional exact identity filters, and wraps the provider-backed
  market-data service so fresh rows can serve HTTP trending, candle, and
  indicator requests without collapsing provider-backed instruments to a bare
  symbol.
- `ATrade.Analysis` owns the provider-neutral analysis engine seam, analysis run
  intake, normalized request/result contracts, engine/source metadata,
  API-facing registry, cache-aware candle acquisition for analysis runs, and
  no-configured-engine fallback for LEAN or alternate analysis runtimes
- `ATrade.Analysis.Lean` owns the first concrete analysis provider. It builds a
  temporary official-LEAN workspace from ATrade OHLCV bars, runs an
  analysis-only moving-average/backtest algorithm through the configured LEAN
  CLI or AppHost-managed Docker runtime (`lean-engine`), parses
  provider-neutral signals/metrics, and rejects brokerage/order-routing source
  tokens.
- `ATrade.Workspaces` owns backend workspace preferences and watchlist request
  intake, including the current Postgres schema/repository for exact pinned
  watchlist instruments. Rows store a durable `instrument_key` / API
  `instrumentKey` and `pinKey` derived from the normalized provider, provider
  symbol id / IBKR `conid`, symbol, exchange, currency, and asset class tuple,
  plus display name, sort order, and timestamps. Duplicate handling merges only
  exact instrument keys so the same symbol or company name can be pinned
  separately for different markets; exact unpins validate the supplied
  `instrumentKey`, while legacy symbol unpins remain limited to unambiguous rows.
- `ATrade.Ibkr.Worker` owns IBKR Gateway readiness monitoring through the shared
  IBKR/iBeam readiness module and any future paper-safe broker polling/streaming
  work

The worker may surface broker connectivity and capability information from the
official IBKR Gateway APIs, but the browser never binds to the worker directly.

## 4. IBKR Gateway / iBeam Session And Connectivity Model

IBKR integration for this slice is **session-aware and paper-only**. The approved
local runtime for user-driven IBKR API login is the AppHost-managed
iBeam/Gateway container image `voyz/ibeam:latest`, which is disabled by default
and only starts when ignored local `.env` values enable broker integration and
replace the fake credential placeholders. The Client Portal API uses HTTPS on
iBeam's internal container port `5000`; AppHost publishes that internal port on
the configured local host port from `ATRADE_IBKR_GATEWAY_PORT` and mounts the
repo-local non-secret `src/ATrade.AppHost/ibeam-inputs/conf.yaml` into
`/srv/inputs` read-only. That inputs file keeps Client Portal locked to
loopback/private local-development callers while allowing the Docker bridge
source addresses that Aspire published-port requests use. The committed gateway
URL default is `https://127.0.0.1:5000`, and custom local ports must keep
`ATRADE_IBKR_GATEWAY_URL=https://127.0.0.1:<ATRADE_IBKR_GATEWAY_PORT>` while
still mapping to container target port `5000`. AppHost resolves those values
through the shared `ATrade.ServiceDefaults` local runtime contract loader, which
classifies the IBKR username, password, and paper account id as secret values
before projecting them through Aspire secret parameters. `http://127.0.0.1:<port>` is the
known-bad transport shape that can reset authenticated refresh requests before
application logic sees an auth response.

### 4.1 Authentication and session status

`ATrade.Ibkr.Worker` is the single owner of the IBKR Gateway session. Its
responsibilities are:

- read paper-mode broker configuration from the ignored local `.env`
- rely on AppHost to map `ATRADE_IBKR_USERNAME` and `ATRADE_IBKR_PASSWORD` to
  the iBeam container variables `IBEAM_ACCOUNT` and `IBEAM_PASSWORD`
- establish or verify a session against the official IBKR Gateway/iBeam APIs
- publish normalized session state changes onto NATS
- expose the provider-neutral `BrokerProviderStatus` shape that `ATrade.Api`
  can project to the frontend

In the currently implemented backend slice, broker status, market-data
status/read guards, and the worker share the same `ATrade.Brokers.Ibkr`
readiness service and shared gateway transport helper so broker status and
market-data refreshes use the same HTTPS base URL, timeout, and
local-certificate policy. Disabled, credentials-missing, configured-iBeam,
timeout/unreachable transport, unauthenticated, authenticated, degraded, error,
and rejected-live outcomes are normalized before any unsafe broker action is
attempted. Raw usernames, passwords, tokens, session cookies, gateway URLs, and
account ids never appear in status payloads or logs; account presence is exposed
only as a boolean. The shared Gateway HTTP transport also sends a stable Client
Portal-compatible user agent because the local Client Portal runtime rejects
anonymous/no-user-agent status requests with `403`. The iBeam self-signed
certificate exception is intentionally narrow: it applies only to loopback/local
HTTPS traffic for the configured `voyz/ibeam:latest` runtime and does not
disable certificate validation for arbitrary hosts.

The normalized session states are:

- `disabled` — broker integration is not enabled locally
- `credentials-missing` — integration is enabled, but the ignored `.env` still
  lacks real paper-login username, password, or paper account id values
- `not-configured` — required local paper/iBeam settings such as URL, HTTPS
  scheme, port, or image contract are inconsistent
- `ibeam-container-configured` — the local iBeam container contract and
  credentials are present, but the HTTPS auth status endpoint is not reachable
  yet; verify the local iBeam URL uses `https://`, authenticate iBeam, and retry
  the workspace refresh
- `rejected-live-mode` — local configuration requested `Live` mode and the
  backend refused it before any broker action
- `connecting` — iBeam is reachable and waiting for paper IBKR authentication
- `authenticated` — the worker has an active paper iBeam session
- `degraded` — iBeam is reachable but market/account features are partially unavailable
- `error` — the worker failed to establish or maintain a safe paper session

The frontend uses those states to render connection banners, not to infer that
orders may be transmitted.

### 4.2 Market-data streaming

The architecture separates the **stream contract** from the **current data
source**:

- the frontend consumes provider-neutral quotes/bars/trending updates from
  `ATrade.Api` over HTTP + SignalR
- `ATrade.Api` awaits `IMarketDataService` / `IMarketDataStreamingService`,
  which compose swappable provider contracts under `ATrade.MarketData`
- HTTP trending, candle, and indicator requests read fresh provider-backed rows
  from the AppHost volume-backed TimescaleDB cache before making a live
  IBKR/iBeam call, including after a full AppHost restart when the same
  TimescaleDB data volume is reused
- cache misses or stale rows refresh from the official IBKR Client Portal /
  iBeam APIs when the local paper iBeam session is configured and authenticated,
  then persist the provider response for later API reads
- local runtime, credential, authentication, HTTPS transport/certificate, or
  gateway gaps are reported as provider `not-configured` / `unavailable` states
  rather than as automatic fallback data; if a fresh Timescale row already
  exists, the API can still serve that fresh persisted payload with cache source
  metadata while iBeam is unavailable

This keeps the UI contract stable while making the current market-data source
explicitly provider-backed, Timescale-first for fresh persisted data, and safely
unavailable when neither a fresh cache entry nor iBeam is ready.

## 5. No-Real-Trades Order Model

The first paper-trading workspace must model order entry as **simulation**, not
broker transmission.

The order flow is:

1. The frontend submits a paper-order intent to `ATrade.Api`.
2. `ATrade.Api` and `ATrade.Orders` validate symbol, side, quantity, order
   type, and paper-only eligibility.
3. The order is stored as a paper order owned by ATrade, not as a live broker
   order.
4. A simulation component publishes lifecycle updates (`accepted`, `working`,
   `partially-filled`, `filled`, `cancelled`, `rejected`) using paper-safe
   provider market inputs.
5. `ATrade.Api` projects those updates to the frontend through SignalR.

Current implementation note: the backend now ships the safe first subset of
that flow by exposing `POST /api/orders/simulate`, which validates paper-only
eligibility and returns a deterministic `simulated-filled` response
immediately. Durable paper-order storage, lifecycle fan-out, and SignalR
projection remain future work.

Hard guardrails:

- no live-order endpoint exists in this slice
- no configuration value may enable live trading
- broker mode other than `Paper` is invalid
- any future broker-backed paper-order transmission requires a separate task,
  separate review, and a doc update to this file

## 6. Data Ownership And Storage Choices

The paper-trading workspace depends on the existing infrastructure roles rather
than introducing new stores.

### 6.1 Postgres

Postgres remains the canonical relational store for:

- paper orders and order-history state
- paper positions and account projections
- watchlists and symbol collections
- durable user workspace preferences
- audit-friendly snapshots of broker/session capability state

Current implementation note: pinned workspace watchlists are stored in Postgres
by `ATrade.Workspaces` under the AppHost-provided `postgres` connection string.
The AppHost `postgres` resource uses a writable named data volume
(`ATRADE_POSTGRES_DATA_VOLUME`, default `atrade-postgres-data`) plus a stable
local-dev secret parameter (`ATRADE_POSTGRES_PASSWORD`) so rows survive a full
`start run` / AppHost stop/start cycle, not just an API process restart. Rows
carry `user_id`, `workspace_id`, and a durable `instrument_key` primary key so
duplicate same-symbol instruments can coexist when provider/market identity
differs; until authentication and named workspaces exist, the API deliberately
uses the temporary `local-user` / `paper-trading` identity seam documented in
`LocalWorkspaceIdentityProvider`.

### 6.2 TimescaleDB

TimescaleDB stores time-series data needed by the workspace. The AppHost
`timescaledb` resource uses a writable named data volume
(`ATRADE_TIMESCALEDB_DATA_VOLUME`, default `atrade-timescaledb-data`) plus a
stable local-dev secret parameter (`ATRADE_TIMESCALEDB_PASSWORD`) so
provider-backed cache rows survive a full `start run` / AppHost stop-start cycle,
not just an API process restart. The current foundation creates an
`atrade_market_data` schema with hypertable-ready candle and scanner/trending
snapshot tables for provider-backed market data:

- historical OHLCV bars for charts, keyed by provider, source, symbol,
  normalized chart range, and candle timestamp, with provider symbol id,
  exchange, currency, and asset class metadata persisted where available for
  exact cache reads
- scanner/trending snapshots with provider-neutral symbol identity, source,
  generated timestamp, score/factor details, reasons metadata, and provider/market
  identity fields
- derived factor time series used by trending calculations

`ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` controls the non-secret freshness
window for API cache-aside reads. The committed default is `30`, meaning
`/api/market-data/trending`, `/api/market-data/{symbol}/candles`, and indicator
requests may use provider-backed Timescale rows generated in the last 30 minutes
before refreshing from the provider. Fresh hits are returned through
`ATrade.Api` with `timescale-cache:{originalSource}` source metadata and can be
served after an AppHost reboot without contacting IBKR/iBeam when the same
TimescaleDB volume is reused. Missing or stale data refreshes from IBKR/iBeam
and is persisted, and stale data is not presented as current when the refresh
fails. Automated reboot tests use isolated temporary TimescaleDB volumes and do
not remove the shared developer default cache volume. The browser still reaches
market data only through `ATrade.Api`; it never connects directly to
TimescaleDB.

### 6.3 Redis

Redis is limited to ephemeral acceleration data such as:

- short-lived quote caches
- rate-limit counters for broker/data APIs
- transient workspace cache entries safe to lose on restart

Redis is not the source of truth for paper orders, user preferences, or
portfolio state.

### 6.4 NATS and SignalR

- **NATS** carries internal events between modules and workers
- **SignalR** carries browser-facing real-time updates after the API projects
  those internal events into UI-safe payloads

The intended data path is:

```text
IBKR session / IBKR market-data events / paper-order simulation
        ▼
      NATS
        ▼
   ATrade.Api projections
        ▼
     SignalR hubs
        ▼
   Next.js paper-trading workspace
```

## 7. Frontend/Backend Separation And Preference Storage

The paper-trading workspace should feel responsive, but durable state must stay
server-owned.

### 7.1 Frontend-owned state

The Next.js frontend may own short-lived UI state such as:

- active workspace module, selected symbol/range route state, visible-disabled
  module selection, and short-lived focus/navigation status; the simplified
  shell does not use a versioned local layout-persistence key for
  context/monitor split sizes
- a non-authoritative cached copy of backend watchlist symbols under
  `atrade.paperTrading.watchlist.v1`, used only for read-only unavailable states
  and one-time migration of pre-Postgres pins
- unsaved chart drawing state that is not yet persisted
- optimistic rendering between direct workflow actions and SignalR confirmation

### 7.2 Backend-owned state

The backend owns all state that must survive refresh, sign-in changes, or
machine changes:

- watchlists
- chart range / indicator presets that are meant to roam with the user
- paper orders and fills
- positions, balances, and account summaries
- server-side trending lists and factor explanations

### 7.3 Preference storage choice

Durable watchlist preferences are now stored in **Postgres** as workspace-scoped
settings owned by `ATrade.Workspaces` and exposed through `ATrade.Api`. Because
the AppHost-managed Postgres data directory is backed by the named
`ATRADE_POSTGRES_DATA_VOLUME` volume, pins survive full local application
reboots that recreate the AppHost/Postgres container when the same volume and
stable `ATRADE_POSTGRES_PASSWORD` value are reused. The frontend loads, pins,
and unpins through the backend watchlist API, then updates its browser cache
from the backend response. Search-result pins send the provider-neutral metadata
returned by `GET /api/market-data/search`: provider, provider symbol id (IBKR
`conid` today), optional `ibkrConid`, name, exchange, currency, and asset class.
The Workspaces watchlist intake normalizes those fields through
`ATrade.MarketData.ExactInstrumentIdentity` into a stable
`instrumentKey`/`pinKey` tuple before repository persistence and uses it as the
Postgres identity; pinning `AAPL` on NASDAQ and `AAPL` on LSE creates two rows,
and unpinning one exact key must not remove the other. Legacy
`DELETE /api/workspace/watchlist/{symbol}` is kept only for unambiguous
symbol-only rows; exact removals use
`DELETE /api/workspace/watchlist/pins/{instrumentKey}`. The `localStorage` key
`atrade.paperTrading.watchlist.v1` is intentionally non-authoritative and
symbol-only: it may seed a one-time manual-symbol migration into Postgres and
may render a clearly labeled read-only cached snapshot when the backend/database
is unavailable, but it must not be treated as saved state and must not contain
secrets, broker account identifiers, provider ids, or tokens. The simplified
workspace removed the separate `atrade.terminal.layout.v1` context/monitor split
preference key and its reset behavior; there is no active browser-local layout
size authority. Any future non-sensitive UI preference key must be versioned,
reset stale data safely, and never write broker/provider data to a backend.
Local cleanup is a manual developer action: stop AppHost first, then remove only
a volume you own (for example an isolated test volume), never a shared/default
volume that may contain desired watchlist state.

## 8. Charting Library Decision

For the open-source MVP, the charting baseline is **`lightweight-charts`**.

Why:

- it is open-source and easy to adopt inside the existing Next.js frontend
- it supports the candlestick/line/volume primitives needed for the first
  paper-trading workspace
- it keeps licensing and distribution risk low for an early staged slice

Current implementation:

- `frontend/components/CandlestickChart.tsx` uses `lightweight-charts` for
  OHLC candlesticks, volume, moving-average overlays, crosshair legend,
  zooming, and panning
- `frontend/lib/watchlistWorkflow.ts` owns backend watchlist API load/retry,
  one-time symbol-only legacy cache migration, read-only cached fallback, exact
  pin/unpin/remove operations, backend-authoritative `instrumentKey`/`pinKey`
  matching, saving state, and stable watchlist error text for the market monitor
- `frontend/lib/symbolSearchWorkflow.ts` owns reusable IBKR stock search query
  state, debounce, minimum-length validation, result state, ranked/filterable
  bounded result view models, show-more/show-less exploration operations, and
  provider / authentication error text
- `frontend/lib/terminalMarketMonitorWorkflow.ts` owns the combined market
  monitor view model over provider trending rows, bounded search rows, and
  backend watchlist rows, including source/provider/market filters, sorting,
  selected-row state, pin state projection, cached-watchlist fallback copy, and
  exact chart/analysis navigation intents
- `frontend/components/terminal/TerminalMarketMonitor.tsx` with
  `MarketMonitorTable`, `MarketMonitorSearch`, compact `MarketMonitorFilters`,
  and `MarketMonitorDetailPanel` renders the dense terminal monitor for `HOME`,
  `SEARCH`, and `WATCHLIST`; the old long/list `SymbolSearch`, `TrendingList`,
  `Watchlist`, and `MarketLogo` renderers are retired
- `frontend/lib/symbolChartWorkflow.ts` owns the selected lookback chart range,
  HTTP candle/indicator fetches, source-label formatting, SignalR subscription
  state and updates from `/hubs/market-data`, and HTTP polling fallback when
  streaming closes or is unavailable while `frontend/lib/terminalChartWorkspaceWorkflow.ts`
  adapts range/source/identity/stream state for `TerminalChartWorkspace`,
  `TerminalInstrumentHeader`, and `TerminalIndicatorGrid`
- `frontend/lib/terminalAnalysisWorkflow.ts` owns provider-neutral engine
  discovery/run states for `TerminalAnalysisWorkspace`, including no-engine,
  runtime-unavailable, running, and result states; `TerminalProviderDiagnostics`
  shows broker/provider/source diagnostics without credentials, account IDs,
  order tickets, or broker-routing controls

Licensing guardrail:

- do **not** adopt the proprietary TradingView Charting Library in this
  repository unless explicit licensing approval is obtained first
- if that approval is ever granted, this document, `README.md`, and the docs
  index must be updated in the same change

## 9. IBKR Scanner Trending Factors Now

Trending symbols now come from fresh TimescaleDB scanner snapshots first, then
from the IBKR/iBeam provider when the persisted snapshot is missing or stale;
there is no production symbol catalog fallback. `ATrade.MarketData.Ibkr` runs
the IBKR scanner query documented in source metadata
(`ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN`) and enriches scanner rows with
IBKR snapshots when available. The scanner transport sends a buffered JSON
`POST /v1/api/iserver/scanner/run` body with an explicit positive
`Content-Length` and no chunked transfer so authenticated Client Portal/iBeam
sessions do not fail `/api/market-data/trending` with edge `411 Length Required`
responses. If iBeam still returns `411` or another provider failure, the API
serves a fresh persisted snapshot when one exists; otherwise it surfaces a safe
provider error rather than fallback symbols or raw secrets.

The factor model explains a symbol's score using provider-derived components:

- **volume spike** — day volume / scanner volume contribution from IBKR data
- **price momentum** — percentage move from IBKR scanner or snapshot data
- **volatility** — absolute move contribution derived from provider values
- **external signal** — currently neutral until a dedicated news/sentiment
  provider exists

The API exposes these as transparent factor contributions rather than a
black-box "hotness" number via `GET /api/market-data/trending`. The Next.js
terminal market monitor renders the backend-provided source metadata in dense
ranked rows, including `timescale-cache:{originalSource}` for fresh persisted
snapshots, and clearly surfaces provider-not-configured/provider-unavailable/
authentication-required states when no fresh cache entry is available and local
iBeam is not ready.

### 9.1 IBKR stock search and pin-any-symbol workflow

Users are no longer constrained to a trending/default list. The terminal market
monitor calls `GET /api/market-data/search` through
`frontend/lib/marketDataClient.ts` via `symbolSearchWorkflow`, always supplies an
explicit capped limit, ranks and filters the bounded result set locally through
compact source/provider/pin/market controls, and renders IBKR/iBeam stock
results as dense rows with explicit provider,
provider-symbol-id/IBKR `conid`, market/exchange, currency, asset class, source,
rank/score, and saved-pin state. Chart and analysis actions route through the
terminal app using `/symbols/{symbol}` query state that preserves exact identity
metadata when available, and pin/unpin actions use the backend watchlist API for
the selected exact provider-market instrument. The frontend uses the centralized
`frontend/lib/instrumentIdentity.ts` adapter to compute provisional optimistic
keys, normalize asset classes, parse an IBKR `conid` only when the provider is
`ibkr` and the provider symbol id is numeric, and build exact chart/analysis
handoff query strings without changing the selected chart range.
Backend-owned `instrumentKey` / `pinKey` values returned by watchlist responses
remain authoritative for persisted pins. Duplicate search results sharing a
symbol or company name are keyed and rendered by exact instrument identity, not
by bare symbol.

The backend search path uses IBKR Client Portal `/iserver/secdef/search` plus
`/iserver/secdef/info` enrichment when Client Portal accepts the detail request;
if the stock detail endpoint returns the derivative-oriented `month required`
validation error, search uses the search contract payload rather than failing or
falling back to a committed symbol allowlist. Automated tests use fake IBKR HTTP
responses; production search never falls back to a committed symbol allowlist.
If iBeam is disabled, missing credentials, unauthenticated, or unreachable,
search returns a stable provider error payload instead of fake results.

## 10. LEAN Analysis Provider

LEAN is now the first **analysis engine provider**, not an API/frontend
dependency. The repository has the `ATrade.Analysis` seam, the
`ATrade.Analysis.Lean` provider module, and HTTP contracts for discovery and
execution: `GET /api/analysis/engines` and `POST /api/analysis/run`.

When no provider is configured, those endpoints still return explicit
`analysis-engine-not-configured` metadata rather than fake signals. When an
ignored local `.env` sets `ATRADE_ANALYSIS_ENGINE=Lean`, the API registers the
LEAN provider and `POST /api/analysis/run` delegates to `ATrade.Analysis`
intake, which can fetch normalized candles for the selected chart range through
the async cache-aware `IMarketDataService` before invoking LEAN. Docker mode is
the no-paid-account
local path: the local Aspire graph shows `lean-engine`,
bind-mounts the generated-workspace root, and passes container metadata to the
API so execution uses `docker exec` to invoke `dotnet
QuantConnect.Lean.Launcher.dll` with a generated local engine config inside that
resource. CLI mode remains available for users with a usable official `lean`
workspace, but that path inherits the CLI's organization-tier requirements.
Runtime absence, missing managed-container metadata, missing Docker or
image/container availability, timeout, parse failure, or non-zero LEAN exits
return `analysis-engine-unavailable` instead of successful synthetic results.

The architecture preserves provider-neutral market-data, analysis, and signal
contracts:

- market/trending signals are normalized before they reach the UI
- analysis requests consume `MarketDataSymbolIdentity` plus normalized
  `OhlcvCandle` bars instead of LEAN runtime types
- analysis results include engine/source metadata so the frontend can display
  whether output came from LEAN or another engine
- NATS events and persisted factor/signal records must not assume LEAN types
- the frontend renders signal source metadata through `TerminalAnalysisWorkspace`
  without binding its types to QuantConnect/LEAN classes
- LEAN remains behind `ATrade.Analysis` contracts and the generated algorithm is
  analysis-only: no brokerage model, no live mode, no order placement, and no
  calls to ATrade order endpoints

Future analysis engines should plug into the same analysis / market-data /
strategy signal boundary without redesigning the paper-trading workspace.

## 11. Configuration Contract Summary

The committed `.env.template` for this feature
family must expose only paper-safe placeholders:

- `ATRADE_BROKER_INTEGRATION_ENABLED`
- `ATRADE_BROKER_ACCOUNT_MODE`
- `ATRADE_IBKR_GATEWAY_URL`
- `ATRADE_IBKR_GATEWAY_PORT`
- `ATRADE_IBKR_GATEWAY_IMAGE`
- `ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS`
- `ATRADE_IBKR_USERNAME`
- `ATRADE_IBKR_PASSWORD`
- `ATRADE_IBKR_PAPER_ACCOUNT_ID`
- `ATRADE_FRONTEND_API_BASE_URL`
- `NEXT_PUBLIC_ATRADE_API_BASE_URL`
- `ATRADE_ANALYSIS_ENGINE`
- `ATRADE_LEAN_RUNTIME_MODE`
- `ATRADE_LEAN_CLI_COMMAND`
- `ATRADE_LEAN_DOCKER_COMMAND`
- `ATRADE_LEAN_DOCKER_IMAGE`
- `ATRADE_LEAN_WORKSPACE_ROOT`
- `ATRADE_LEAN_TIMEOUT_SECONDS`
- `ATRADE_LEAN_KEEP_WORKSPACE`
- `ATRADE_LEAN_MANAGED_CONTAINER_NAME`
- `ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT`

Rules:

- committed defaults remain disabled and paper-only
- `ATRADE_IBKR_GATEWAY_URL` and `ATRADE_IBKR_GATEWAY_PORT` describe the local
  HTTPS host endpoint clients call; AppHost publishes that host port to iBeam's
  fixed internal Client Portal target port `5000` and mounts the non-secret
  iBeam inputs config required for local/private Docker bridge callers
- `ATRADE_IBKR_GATEWAY_IMAGE` is the approved `voyz/ibeam:latest` local runtime
  contract, but AppHost still does not start it until integration is enabled and
  fake credentials have been replaced in ignored `.env`
- usernames, passwords, tokens, session cookies, and real account identifiers stay out of git
- any real local secret belongs only in the ignored repo-root `.env`
- AppHost passes only `IBEAM_ACCOUNT` and `IBEAM_PASSWORD` to iBeam via secret
  parameters and never passes the paper account id to the container
- LEAN placeholders are non-secret local runtime settings and stay disabled by
  default with `ATRADE_ANALYSIS_ENGINE=none`; when Docker mode is selected, the
  AppHost declares `lean-engine` and the managed container/workspace variables
  must remain non-secret local runtime metadata
- changing these variables must never create a live-trading or real-order path

## 12. Change Control

This document is `status: active` and authoritative for the paper-trading
workspace direction. Any change that weakens the paper-only guardrails,
introduces live trading, changes the charting-library decision, or makes LEAN
an API/frontend dependency requires a maintainer-approved update to this file and
matching updates to the active repository docs that summarize the same area.
