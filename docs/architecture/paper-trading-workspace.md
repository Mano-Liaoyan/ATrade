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

> **Status note:** This document still defines the staged architecture and
> safety contract for the broader paper-trading workspace, and the first
> paper-trading UI slice is now implemented against deterministic mocked data.
> The current repository now also defines provider-neutral broker and
> market-data contracts so IBKR/iBeam and future analysis providers plug in
> behind API/frontend-stable seams. The current repository ships
> `ATrade.Brokers.Ibkr` as a paper-only broker adapter, `ATrade.Api` endpoints for `GET /api/broker/ibkr/status`,
> `POST /api/orders/simulate`, `GET /api/market-data/trending`,
> `GET /api/market-data/{symbol}/candles`, and
> `GET /api/market-data/{symbol}/indicators`, a `/hubs/market-data` SignalR
> hub, deterministic mocked market-data providers behind compatibility services,
> AppHost-driven paper-safe broker configuration wiring, and a Next.js workspace with trending symbols,
> local browser watchlists, `lightweight-charts` candlesticks, timeframe
> switching, indicators, and SignalR-to-HTTP fallback behavior. Durable
> paper-order storage, backend-owned user preferences, provider-backed market
> data, and real broker order placement remain future work.

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
5. **Mocked market/trending data is acceptable now; unsafe realism is not.**
   Until the follow-on provider work lands, the UI may rely on deterministic
   mocked quotes, bars, watchlists, and trending signals only through the
   provider abstraction layer. Once a real provider is selected, missing local
   runtime or credentials must surface as safe not-configured/unavailable
   states rather than silently falling back to fake data.

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
- browser-side session state for active tabs, open panels, and optimistic UI
  interactions
- SignalR subscriptions for real-time account, order, and market updates

The frontend does **not** talk directly to IBKR, Redis, NATS, Postgres, or
TimescaleDB. All durable and broker-aware behavior goes through the API.

### 3.2 `ATrade.Api`

`ATrade.Api` remains the only browser-facing backend surface and expands with:

- HTTP endpoints for workspace bootstrap data, watchlists, account state,
  paper orders, and chart history
- SignalR hubs that push account, order, quote, bar, and trending updates to
  the browser
- translation between browser commands and internal module calls / NATS events
- enforcement of the paper-only guardrails described in this document

The current backend slice exposes `GET /api/broker/ibkr/status`,
`POST /api/orders/simulate`, `GET /api/market-data/trending`,
`GET /api/market-data/{symbol}/candles?timeframe=...`,
`GET /api/market-data/{symbol}/indicators?timeframe=...`, and the
`/hubs/market-data` SignalR hub while keeping the browser-to-broker boundary
strictly server-side. The broker endpoint resolves the provider-neutral
`IBrokerProvider` contract. The market-data endpoints serve deterministic
mocked stocks/ETFs, OHLCV candles for `1m`, `5m`, `1h`, and `1D`, and
moving-average / RSI / MACD payloads through `IMarketDataService`, which now
composes `IMarketDataProvider` instead of binding endpoint code to the mock.
SignalR is the outward-facing streaming layer for browsers; NATS remains the
internal event backbone between API and workers.

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
  status/error states, symbol-search readiness hooks, and historical chart
  queries; the current slice provides deterministic temporary symbol, candle,
  indicator, trending-factor, and SignalR snapshot provider implementations
  without Polygon, TimescaleDB, Redis, NATS, LEAN, or paid news/data services
- `ATrade.Ibkr.Worker` owns IBKR Gateway session management and any future
  paper-safe broker polling/streaming work

The worker may surface broker connectivity and capability information from the
official IBKR Gateway APIs, but the browser never binds to the worker directly.

## 4. IBKR Gateway Session And Connectivity Model

IBKR integration for this slice is **session-aware and paper-only**.

### 4.1 Authentication and session status

`ATrade.Ibkr.Worker` is the single owner of the IBKR Gateway session. Its
responsibilities are:

- read paper-mode broker configuration from the ignored local `.env`
- establish or verify a session against the official IBKR Gateway APIs
- publish normalized session state changes onto NATS
- expose the provider-neutral `BrokerProviderStatus` shape that `ATrade.Api`
  can project to the frontend

In the currently implemented backend slice, the worker and API share the same
`ATrade.Brokers.Ibkr` status service so disabled and rejected-live outcomes are
normalized before any broker call is attempted.

The normalized session states are:

- `disabled` — broker integration is not enabled locally
- `not-configured` — required local paper settings are missing
- `rejected-live-mode` — local configuration requested `Live` mode and the
  backend refused it before any broker action
- `connecting` — the worker is attempting to reach the paper gateway
- `authenticated` — the worker has an active paper session
- `degraded` — the gateway is reachable but market/account features are
  partially unavailable
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
- the backend may later source market data from the official IBKR Gateway or
  iBeam APIs when paper-safe subscriptions are wired in
- until that provider work lands, the API may serve deterministic mocked quote
  and bar streams with the same payload shape
- after a real provider is selected, local runtime or credential gaps must be
  reported as provider `not-configured` / `unavailable` states rather than as
  automatic mock fallback

This keeps the UI contract stable while allowing the market-data source to move
from mocked data to real paper-safe streaming later.

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
   `partially-filled`, `filled`, `cancelled`, `rejected`) using mocked or
   paper-safe market inputs.
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
IBKR session / mocked market events / paper-order simulation
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
- the current MVP watchlist stored under `atrade.paperTrading.watchlist.v1` in
  browser `localStorage` as a convenience cache until backend preferences land
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

Durable user preferences are stored in **Postgres** as user-scoped workspace
settings in the target architecture. In the current MVP, the frontend persists
only a local browser watchlist in `localStorage` to survive refreshes on the
same machine. That cache is intentionally not authoritative, not shared across
machines, and must not contain secrets, broker account identifiers, or tokens.

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

## 9. Mocked Trending Factors Now

Trending symbols are intentionally mocked in the first slice so the UI can be
built without waiting for real provider ingestion.

The mocked factor model should explain a symbol's score using four explicit
components:

- **volume spike** — unusual volume relative to the symbol's recent baseline
- **price momentum** — directional move across the selected lookback window
- **volatility** — realized intraday or short-window range expansion
- **news-sentiment placeholder** — a clearly labeled placeholder factor until a
  real news/sentiment source exists

The API exposes these as transparent factor contributions rather than a
black-box "hotness" number via `GET /api/market-data/trending`. The Next.js
landing workspace renders those backend-provided stock/ETF factors and never
pretends they came from a real provider.

## 10. Future LEAN Seam

LEAN is a **future plug-in seam**, not a dependency of the first
paper-trading slice.

The architecture should therefore preserve provider-neutral market-data and
signal contracts:

- market/trending signals are normalized before they reach the UI
- NATS events and persisted factor/signal records should not assume LEAN types
- the frontend should render signal source metadata without caring whether the
  source is mocked logic, internal analytics, or future LEAN integration
- future LEAN work belongs behind analysis-engine contracts that consume the
  normalized market-data/provider shapes rather than becoming an API or UI
  assumption

When LEAN is introduced later, it should plug into the existing market-data /
strategy signal boundary rather than forcing the paper-trading workspace to be
redesigned.

## 11. Configuration Contract Summary

The committed `.env.example` for this feature family must expose only paper-safe
placeholders:

- `ATRADE_BROKER_INTEGRATION_ENABLED`
- `ATRADE_BROKER_ACCOUNT_MODE`
- `ATRADE_IBKR_GATEWAY_URL`
- `ATRADE_IBKR_GATEWAY_PORT`
- `ATRADE_IBKR_GATEWAY_IMAGE`
- `ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS`
- `ATRADE_IBKR_PAPER_ACCOUNT_ID`
- `ATRADE_FRONTEND_API_BASE_URL`
- `NEXT_PUBLIC_ATRADE_API_BASE_URL`

Rules:

- committed defaults remain disabled and paper-only
- usernames, passwords, tokens, and real account identifiers stay out of git
- any real local secret belongs only in the ignored repo-root `.env`
- `ATRADE_IBKR_GATEWAY_IMAGE` stays a placeholder in committed files and only
  enables an optional AppHost-managed Gateway container when a non-placeholder
  official image is provided locally
- changing these variables must never create a live-trading path

## 12. Change Control

This document is `status: active` and authoritative for the paper-trading
workspace direction. Any change that weakens the paper-only guardrails,
introduces live trading, changes the charting-library decision, or makes LEAN
an immediate dependency requires a maintainer-approved update to this file and
matching updates to the active repository docs that summarize the same area.
