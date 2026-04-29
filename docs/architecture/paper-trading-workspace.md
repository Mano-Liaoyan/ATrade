---
status: active
owner: maintainer
updated: 2026-04-29
summary: Authoritative paper-trading workspace architecture and paper-only configuration contract for the staged IBKR-backed trading UI slice.
see_also:
  - ../INDEX.md
  - overview.md
  - modules.md
  - provider-abstractions.md
  - ../../README.md
  - ../../PLAN.md
  - ../../scripts/README.md
---

# Paper-Trading Workspace Architecture

> **Status note:** This document defines the staged architecture and safety
> contract for the broader paper-trading workspace. The current repository now
> uses provider-neutral broker and market-data contracts with IBKR/iBeam as the
> first real market-data provider behind API/frontend-stable seams. The current
> repository ships `ATrade.Brokers.Ibkr` as a paper-only broker adapter,
> `ATrade.MarketData.Ibkr` as the IBKR/iBeam market-data provider,
> `ATrade.Api` endpoints for `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/{symbol}/candles`, and
> `GET /api/market-data/{symbol}/indicators`, a `/hubs/market-data` SignalR
> hub, backend-owned `GET` / `PUT` / `POST` / `DELETE /api/workspace/watchlist`
> endpoints backed by the AppHost-managed Postgres resource, AppHost-driven
> paper-safe broker/iBeam configuration wiring, and a Next.js workspace with
> IBKR scanner-driven trending symbols, Postgres-backed watchlists,
> `lightweight-charts` candlesticks, timeframe switching, indicators, source
> metadata, and SignalR-to-HTTP fallback behavior. Production mocked
> market-data providers have been removed; missing iBeam runtime, credentials,
> or authentication returns safe provider-not-configured/provider-unavailable
> errors rather than fallback data. Durable paper-order storage and real broker
> order placement remain future work.

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
state transitions, data access, and streaming contracts.

## 3. Runtime Boundaries

The paper-trading slice uses the existing ATrade modular-monolith topology.
No extra deployable services are introduced.

### 3.1 Next.js frontend

The `frontend/` application owns:

- route composition for the paper-trading workspace
- watchlist, chart, order-ticket, and account widgets
- browser-side session state for active tabs, open panels, non-authoritative
  watchlist cache/migration state, and optimistic UI interactions
- SignalR subscriptions for real-time account, order, and market updates

The frontend does **not** talk directly to IBKR, Redis, NATS, Postgres, or
TimescaleDB. All durable and broker-aware behavior goes through the API.

### 3.2 `ATrade.Api`

`ATrade.Api` remains the only browser-facing backend surface and expands with:

- HTTP endpoints for workspace bootstrap data, Postgres-backed watchlists,
  account state, paper orders, and chart history
- SignalR hubs that push account, order, quote, bar, and trending updates to
  the browser
- translation between browser commands and internal module calls / NATS events
- enforcement of the paper-only guardrails described in this document

The current backend slice exposes `GET /api/broker/ibkr/status`,
`POST /api/orders/simulate`, `GET /api/market-data/trending`,
`GET /api/market-data/{symbol}/candles?timeframe=...`,
`GET /api/market-data/{symbol}/indicators?timeframe=...`, `GET /api/workspace/watchlist`,
`PUT /api/workspace/watchlist`, `POST /api/workspace/watchlist`,
`DELETE /api/workspace/watchlist/{symbol}`, and the `/hubs/market-data` SignalR hub while keeping the browser-to-broker boundary
strictly server-side. The broker endpoint resolves the provider-neutral
`IBrokerProvider` contract. The market-data endpoints use `IMarketDataService`
and the `ATrade.MarketData.Ibkr` provider to translate IBKR Client Portal/iBeam
contract lookup, scanner, snapshot, and historical bar responses into
provider-neutral trending, OHLCV candle, moving-average, RSI, MACD, and source
metadata payloads for `1m`, `5m`, `1h`, and `1D`. SignalR is the outward-facing
streaming layer for browsers and creates provider-backed snapshots when the
IBKR/iBeam provider is available; NATS remains the internal event backbone
between API and workers.

### 3.3 Backend modules and workers

The paper-trading slice extends existing planned responsibilities as follows:

- `ATrade.Accounts` owns paper account projections, balances, positions, and
  broker-session summaries
- `ATrade.Brokers` owns the provider-neutral broker identity, capability,
  account-mode, and status contracts shared by API, worker, and adapters
- `ATrade.Brokers.Ibkr` owns typed paper-mode configuration, the official
  Gateway session/status client boundary, paper-only guardrails, and the safe
  `IBrokerProvider` implementation shared by the API and worker
- `ATrade.Orders` owns paper-order validation, lifecycle state, and simulated
  fills; the current backend slice already returns deterministic simulated
  fills directly from this module
- `ATrade.MarketData` owns provider-neutral quote/bar contracts, provider
  status/error states, symbol-search readiness hooks, historical chart queries,
  compatibility services, and SignalR snapshot contracts
- `ATrade.MarketData.Ibkr` owns the first real market-data provider: IBKR/iBeam
  Client Portal contract lookup, scanner/trending-equivalent mapping,
  snapshots, historical bars, indicator inputs, source metadata, and safe
  not-configured/unavailable responses without reading credentials directly
- `ATrade.Workspaces` owns backend workspace preferences, including the current
  Postgres schema/repository for pinned watchlist symbols and metadata fields
  (`provider`, optional provider id / IBKR `conid`, exchange, currency, asset
  class, sort order, and timestamps)
- `ATrade.Ibkr.Worker` owns IBKR Gateway session management and any future
  paper-safe broker polling/streaming work

The worker may surface broker connectivity and capability information from the
official IBKR Gateway APIs, but the browser never binds to the worker directly.

## 4. IBKR Gateway / iBeam Session And Connectivity Model

IBKR integration for this slice is **session-aware and paper-only**. The approved
local runtime for user-driven IBKR API login is the AppHost-managed
iBeam/Gateway container image `voyz/ibeam:latest`, which is disabled by default
and only starts when ignored local `.env` values enable broker integration and
replace the fake credential placeholders.

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

In the currently implemented backend slice, the worker and API share the same
`ATrade.Brokers.Ibkr` status service so disabled, credentials-missing, configured-iBeam,
and rejected-live outcomes are normalized before any unsafe broker action is attempted.
Raw usernames, passwords, tokens, session cookies, and account ids never appear in
status payloads; account presence is exposed only as a boolean.

The normalized session states are:

- `disabled` — broker integration is not enabled locally
- `credentials-missing` — integration is enabled, but the ignored `.env` still
  lacks real paper-login username, password, or paper account id values
- `not-configured` — required local paper/iBeam settings such as URL, port, or
  image contract are inconsistent
- `ibeam-container-configured` — the local iBeam container contract and
  credentials are present, but the auth status endpoint is not reachable yet
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
- `ATrade.Api` talks to `IMarketDataService` / `IMarketDataStreamingService`,
  which compose swappable provider contracts under `ATrade.MarketData`
- the backend now sources market data from the official IBKR Client Portal /
  iBeam APIs when the local paper iBeam session is configured and authenticated
- local runtime, credential, authentication, or gateway gaps are reported as
  provider `not-configured` / `unavailable` states rather than as automatic
  fallback data

This keeps the UI contract stable while making the current market-data source
explicitly real-provider backed and safely unavailable when iBeam is not ready.

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

Current implementation note: pinned workspace watchlists are already stored in
Postgres by `ATrade.Workspaces` under the AppHost-provided `postgres`
connection string. Rows carry `user_id` and `workspace_id`; until authentication
and named workspaces exist, the API deliberately uses the temporary
`local-user` / `paper-trading` identity seam documented in
`LocalWorkspaceIdentityProvider`.

### 6.2 TimescaleDB

TimescaleDB stores time-series data needed by the workspace:

- historical OHLCV bars for charts
- intraday paper-market snapshots when retained for analysis
- derived factor time series used by trending calculations

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

- active tab and panel arrangement during a browser session
- a non-authoritative cached copy of backend watchlist symbols under
  `atrade.paperTrading.watchlist.v1`, used only for read-only unavailable states
  and one-time migration of pre-Postgres pins
- unsaved chart drawing state that is not yet persisted
- optimistic rendering between command submission and SignalR confirmation

### 7.2 Backend-owned state

The backend owns all state that must survive refresh, sign-in changes, or
machine changes:

- watchlists
- chart interval / indicator presets that are meant to roam with the user
- paper orders and fills
- positions, balances, and account summaries
- server-side trending lists and factor explanations

### 7.3 Preference storage choice

Durable watchlist preferences are now stored in **Postgres** as workspace-scoped
settings owned by `ATrade.Workspaces` and exposed through `ATrade.Api`. The
frontend loads, pins, and unpins through the backend watchlist API, then updates
its browser cache from the backend response. The `localStorage` key
`atrade.paperTrading.watchlist.v1` is intentionally non-authoritative: it may
seed a one-time migration into Postgres and may render a clearly labeled
read-only cached snapshot when the backend/database is unavailable, but it must
not be treated as saved state and must not contain secrets, broker account
identifiers, or tokens.

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
- `frontend/components/SymbolChartView.tsx` combines HTTP candle/indicator
  fetches with SignalR updates from `/hubs/market-data` and falls back to HTTP
  polling when streaming is unavailable

Licensing guardrail:

- do **not** adopt the proprietary TradingView Charting Library in this
  repository unless explicit licensing approval is obtained first
- if that approval is ever granted, this document, `README.md`, and the docs
  index must be updated in the same change

## 9. IBKR Scanner Trending Factors Now

Trending symbols now come from the IBKR/iBeam provider rather than a production
symbol catalog. `ATrade.MarketData.Ibkr` runs the IBKR scanner query documented
in source metadata (`ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN`) and enriches
scanner rows with IBKR snapshots when available.

The factor model explains a symbol's score using provider-derived components:

- **volume spike** — day volume / scanner volume contribution from IBKR data
- **price momentum** — percentage move from IBKR scanner or snapshot data
- **volatility** — absolute move contribution derived from provider values
- **external signal** — currently neutral until a dedicated news/sentiment
  provider exists

The API exposes these as transparent factor contributions rather than a
black-box "hotness" number via `GET /api/market-data/trending`. The Next.js
landing workspace renders the backend-provided IBKR source metadata and clearly
surfaces provider-not-configured/provider-unavailable states when local iBeam is
not ready.

## 10. Future LEAN Seam

LEAN is a **future plug-in seam**, not a dependency of the first
paper-trading slice.

The architecture should therefore preserve provider-neutral market-data and
signal contracts:

- market/trending signals are normalized before they reach the UI
- NATS events and persisted factor/signal records should not assume LEAN types
- the frontend should render signal source metadata without caring whether the
  source is IBKR/iBeam, internal analytics, or future LEAN integration
- future LEAN work belongs behind analysis-engine contracts that consume the
  normalized market-data/provider shapes rather than becoming an API or UI
  assumption

When LEAN is introduced later, it should plug into the existing market-data /
strategy signal boundary rather than forcing the paper-trading workspace to be
redesigned.

## 11. Configuration Contract Summary

The committed `.env.example` and synchronized `.env.template` for this feature
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

Rules:

- committed defaults remain disabled and paper-only
- `ATRADE_IBKR_GATEWAY_IMAGE` is the approved `voyz/ibeam:latest` local runtime
  contract, but AppHost still does not start it until integration is enabled and
  fake credentials have been replaced in ignored `.env`
- usernames, passwords, tokens, session cookies, and real account identifiers stay out of git
- any real local secret belongs only in the ignored repo-root `.env`
- AppHost passes only `IBEAM_ACCOUNT` and `IBEAM_PASSWORD` to iBeam via secret
  parameters and never passes the paper account id to the container
- changing these variables must never create a live-trading or real-order path

## 12. Change Control

This document is `status: active` and authoritative for the paper-trading
workspace direction. Any change that weakens the paper-only guardrails,
introduces live trading, changes the charting-library decision, or makes LEAN
an immediate dependency requires a maintainer-approved update to this file and
matching updates to the active repository docs that summarize the same area.
