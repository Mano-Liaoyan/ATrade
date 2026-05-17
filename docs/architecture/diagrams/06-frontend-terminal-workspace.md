---
status: active
owner: maintainer
updated: 2026-05-17
summary: Frontend terminal workspace route, component, workflow, API-boundary, streaming, and scroll-ownership architecture diagrams.
see_also:
  - ../../INDEX.md
  - ../modules.md
  - ../paper-trading-workspace.md
  - ../../design/atrade-terminal-ui.md
  - ../../../README.md
  - ../../../PLAN.md
---

# Frontend Terminal Workspace Diagrams

This document maps the current Next.js terminal workspace surface. It should be
read as a companion to the active design and architecture docs, not as a new
source of product rules. Names in the diagrams intentionally match current
frontend files such as `ATradeTerminalApp`, `terminalRoutes`,
`terminalModuleRegistry`, and the `frontend/lib/*Workflow.ts` hooks.

The important boundary is simple: the browser owns route state, view models,
local interaction state, and safe streaming clients; `ATrade.Api` owns all
durable, provider-aware, account-aware, and backtest execution behavior.

## Route Map

All active pages render through `TerminalRoutePage`, which converts the route
and query string into initial `ATradeTerminalApp` state. Enabled routes open
working modules, symbol routes preserve provider-neutral Exact Instrument
Identity query metadata when available, and visible-disabled routes render the
future module surface without enabling the workflow.

```mermaid
flowchart LR
  RoutePage["TerminalRoutePage"]
  RouteState["createTerminalRouteAppState()"]
  App["ATradeTerminalApp"]

  RoutePage --> RouteState --> App

  subgraph Enabled["Enabled module routes"]
    HomeRoute["/ -> HOME"]
    SearchRoute["/search -> SEARCH"]
    WatchlistRoute["/watchlist -> WATCHLIST"]
    ChartRoute["/chart -> CHART landing"]
    AnalysisRoute["/analysis -> ANALYSIS"]
    BacktestRoute["/backtest -> BACKTEST"]
    StatusRoute["/status -> STATUS"]
    HelpRoute["/help -> HELP"]
  end

  subgraph SymbolRoutes["Canonical symbol routes"]
    ChartSymbol["/chart/{symbol} -> CHART"]
    AnalysisSymbol["/analysis/{symbol} -> ANALYSIS"]
    BacktestSymbol["/backtest/{symbol} -> BACKTEST"]
    IdentityQuery["provider, providerSymbolId, exchange, currency, assetClass, range"]
  end

  subgraph Disabled["Visible-disabled future routes"]
    NewsRoute["/news -> NEWS"]
    PortfolioRoute["/portfolio -> PORTFOLIO"]
    ResearchRoute["/research -> RESEARCH"]
    ScreenerRoute["/screener -> SCREENER"]
    EconRoute["/econ -> ECON"]
    AiRoute["/ai -> AI"]
    NodeRoute["/node -> NODE"]
    OrdersRoute["/orders -> ORDERS"]
  end

  Enabled --> RoutePage
  SymbolRoutes --> RoutePage
  Disabled --> RoutePage
  IdentityQuery --> RouteState
  App --> ActiveModule["Enabled module content"]
  App --> DisabledModule["TerminalDisabledModule"]
```

Notes:

- `frontend/lib/terminalRoutes.ts` is the route registry for enabled,
  disabled, and symbol module paths.
- `frontend/lib/instrumentIdentity.ts` adapts route query metadata into the
  provider-neutral identity tuple. Backend-returned `instrumentKey` and `pinKey`
  values remain authoritative for persisted pins.
- The retired `/symbols/{symbol}` route is intentionally absent.

## Terminal Frame And Workflow Map

`ATradeTerminalApp` is the route-backed client frame. The rail and workspace are
registry-driven, while workflow hooks normalize API responses into module-ready
state. Home, Search, Watchlist, Chart, Analysis, Backtest, Status, and Help are
composed directly rather than through the retired shell/list wrappers.

```mermaid
flowchart TB
  App["ATradeTerminalApp"]
  Rail["TerminalModuleRail"]
  Registry["terminalModuleRegistry"]
  Layout["TerminalWorkspaceLayout"]
  StatusIndicator["TerminalWorkspaceStatusIndicator"]
  Primary["Primary scroll-owned workspace"]

  App --> Rail --> Registry
  App --> Layout
  Layout --> StatusIndicator
  Layout --> Primary

  Primary --> Home["TerminalHomeModule"]
  Primary --> Search["TerminalSearchModule"]
  Primary --> Watchlist["TerminalWatchlistModule"]
  Primary --> ChartLanding["TerminalChartLandingModule"]
  Primary --> Chart["TerminalChartWorkspace"]
  Primary --> Analysis["TerminalAnalysisWorkspace"]
  Primary --> Backtest["TerminalBacktestWorkspace"]
  Primary --> Status["TerminalStatusModule"]
  Primary --> Help["TerminalHelpModule"]
  Primary --> DisabledSurface["TerminalDisabledModule"]

  Home --> ProviderDiagnostics["TerminalProviderDiagnostics"]
  Home --> MonitorPrimitives["TerminalMarketMonitor primitives"]
  Search --> MonitorPrimitives
  Watchlist --> MonitorPrimitives
  MonitorPrimitives --> MonitorWorkflow["terminalMarketMonitorWorkflow"]
  MonitorWorkflow --> SearchWorkflow["symbolSearchWorkflow"]
  MonitorWorkflow --> WatchlistWorkflow["watchlistWorkflow"]
  MonitorWorkflow --> MarketDataClient["marketDataClient"]
  MonitorWorkflow --> WatchlistClient["watchlistClient"]

  ChartLanding --> WatchlistWorkflow
  Chart --> ChartWorkflow["terminalChartWorkspaceWorkflow + symbolChartWorkflow"]
  ChartWorkflow --> MarketDataStream["marketDataStream"]
  ChartWorkflow --> MarketDataClient
  Chart --> CandleChart["CandlestickChart using lightweight-charts"]

  Analysis --> AnalysisWorkflow["terminalAnalysisWorkflow"]
  AnalysisWorkflow --> AnalysisClient["analysisClient"]

  Backtest --> BacktestWorkflow["terminalBacktestWorkflow"]
  Backtest --> Comparison["BacktestComparisonPanel"]
  BacktestWorkflow --> BacktestClient["backtestClient"]

  StatusIndicator --> WorkspaceStatusClient["workspaceStatusClient"]
  ProviderDiagnostics --> BrokerStatusClient["brokerStatusClient"]
```

Notes:

- `TerminalHomeModule`, `TerminalSearchModule`, and `TerminalWatchlistModule`
  share monitor primitives but keep distinct page purposes.
- Market rows create direct chart, analysis, and backtest intents using
  `createTerminalSymbolRoute()`.
- `TerminalChartLandingModule` owns the `/chart` Stored stocks selector and
  defaults to the first backend watchlist instrument when one is available; it
  does not substitute a demo symbol.

## Browser Boundary

The frontend never calls providers, databases, brokers, NATS, Redis, LEAN, or
order-routing internals directly. Browser code reaches the backend only through
HTTP and SignalR contracts exposed by `ATrade.Api`.

```mermaid
flowchart LR
  Browser["Next.js terminal workspace"]
  Workflows["frontend/lib workflow hooks"]
  Clients["HTTP and SignalR clients"]
  Api["ATrade.Api browser boundary"]

  Browser --> Workflows --> Clients --> Api

  Api --> BrokerStatus["Broker status and account/capital projections"]
  Api --> MarketData["Market-data search, trending, candles, indicators"]
  Api --> Watchlists["Workspace watchlist preferences"]
  Api --> AnalysisApi["Analysis engine discovery and runs"]
  Api --> Backtests["Saved backtest runs and status hub"]

  Browser -. forbidden .-> NoDirect["No direct provider, database, runtime, NATS, Redis, LEAN, or order-routing access"]

  classDef boundary fill:#101820,stroke:#d6a84f,color:#f8ecd0;
  classDef blocked fill:#2a1214,stroke:#d66b6b,color:#ffe1e1;
  class Api boundary;
  class NoDirect blocked;
```

Safe frontend client modules include:

- `marketDataClient` for `/api/market-data/trending`, search, candles, and
  indicators.
- `watchlistClient` for backend-owned exact watchlist pins.
- `analysisClient` for `/api/analysis/engines` and `/api/analysis/run`.
- `backtestClient` for paper capital, saved run history/detail/create/cancel/
  retry, and `/hubs/backtests`.
- `workspaceStatusClient` for `/health` plus a compact hub/read-state
  projection.

## Market Data Streaming And Fallback

Charts use HTTP first for authoritative candle and indicator reads, then subscribe
to SignalR for updates. If streaming closes or is unavailable, the chart workflow
uses HTTP polling fallback and keeps stale, unavailable, or empty states visible
instead of inventing bars.

```mermaid
sequenceDiagram
  participant Browser as Chart workspace
  participant ChartFlow as symbolChartWorkflow
  participant Api as ATrade.Api
  participant Hub as Market data hub
  participant Cache as Timescale cache aside service
  participant Provider as Market-data provider seam

  Browser->>ChartFlow: Open /chart/{symbol} with range and identity query
  ChartFlow->>Api: GET /api/market-data/{symbol}/candles?range=...
  Api->>Cache: Read fresh candles by range and exact identity
  alt fresh cache hit
    Cache-->>Api: Provider-neutral candles with timescale-cache source
  else missing or stale cache
    Cache->>Provider: Refresh through market-data provider contracts
    Provider-->>Cache: Provider-neutral candles or safe provider error
    Cache-->>Api: Persisted fresh data, stale-labeled data, or error
  end
  Api-->>ChartFlow: Candle payload with source/freshness metadata
  ChartFlow->>Api: GET /api/market-data/{symbol}/indicators?range=...
  Api-->>ChartFlow: Indicator payload from cache-aware candles
  ChartFlow->>Hub: Subscribe(symbol, range)
  alt hub connected
    Hub-->>ChartFlow: Safe market-data updates
    ChartFlow-->>Browser: Update chart state
  else hub closed or unavailable
    ChartFlow->>Api: Repeat candle/indicator HTTP reads on fallback interval
    Api-->>ChartFlow: Latest available safe payload
  end
```

## Backtest Status Flow

The BACKTEST module is API-only and simulation-only. It reads effective paper
capital, creates saved single-symbol built-in strategy runs, watches safe status
updates over `/hubs/backtests`, and recovers state through HTTP reads. Completed
comparison uses only persisted saved result/equity payloads.

```mermaid
sequenceDiagram
  participant Browser as TerminalBacktestWorkspace
  participant Flow as terminalBacktestWorkflow
  participant Client as backtestClient
  participant Api as ATrade.Api
  participant Runner as API hosted backtest runner
  participant Hub as Backtest status hub
  participant Modules as Backend modules

  Browser->>Flow: Open BACKTEST with optional symbol identity
  Flow->>Client: Load capital, history, selected detail
  Client->>Api: GET /api/accounts/paper-capital
  Client->>Api: GET /api/backtests
  Api-->>Client: Safe capital and saved run envelopes
  Flow->>Client: Start status stream
  Client->>Hub: Connect to /hubs/backtests
  Browser->>Flow: Create built-in strategy run
  Flow->>Client: POST /api/backtests
  Client->>Api: Built-in strategy, range, identity, costs, benchmark
  Api->>Modules: Validate capital, request, strategy, and identity
  Api-->>Client: 202 queued saved run
  Runner->>Modules: Fetch candles and run configured analysis engine
  Runner->>Api: Persist safe completed, failed, or cancelled envelope
  Api-->>Hub: Broadcast redacted run update
  Hub-->>Client: Status/result/error update
  Client-->>Flow: Merge update with HTTP-authoritative state
  alt reconnect or stream unavailable
    Flow->>Client: Reload history/detail over HTTP
    Client->>Api: GET /api/backtests and GET /api/backtests/{id}
    Api-->>Client: Persisted safe state
  end
```

Guardrails:

- No browser-submitted bars, custom strategy code, runtime paths, account
  identifiers, gateway URLs, order-routing fields, or fake result envelopes.
- Cancel and retry remain saved-run API actions; they do not create broker order
  controls.

## Desktop Scroll Ownership

The terminal is a full-viewport desktop app with page-level scrolling disabled.
Every overflow-prone region must own visible internal/custom scroll affordances,
and wheel input is chained through scroll owners by
`attachTerminalWheelScrollOwnership()`.

```mermaid
flowchart TB
  AppFrame["atrade-terminal-app full viewport"]
  PageScroll["Page-level vertical scroll disabled"]
  WheelOwner["attachTerminalWheelScrollOwnership(root)"]

  AppFrame --> PageScroll
  AppFrame --> WheelOwner

  WheelOwner --> RailScroll["Module rail scroll owner"]
  WheelOwner --> WorkspaceScroll["Primary workspace scroll owner"]
  WheelOwner --> PanelScroll["Panel/module scroll owners"]
  WheelOwner --> TableScroll["Market monitor table x/y scroll owner"]
  WheelOwner --> ChartScroll["Chart, analysis, backtest, status, help, disabled-module overflow"]

  RailScroll --> VisibleRail["Visible/custom rail scrollbar affordance"]
  WorkspaceScroll --> VisibleWorkspace["Visible/custom workspace scrollbar affordance"]
  TableScroll --> VisibleTable["Visible vertical and horizontal table scrollbars"]

  classDef guardrail fill:#13181d,stroke:#d6a84f,color:#f8ecd0;
  class PageScroll,WheelOwner,VisibleRail,VisibleWorkspace,VisibleTable guardrail;
```

This guardrail targets latest stable desktop Safari, Firefox, Chrome, and Edge.
Safari may hide native OS scrollbars, so key terminal regions need app-owned or
explicitly styled tracks/thumbs where reachability matters. Mobile optimization
is limited to preserving the existing responsive fallback.
