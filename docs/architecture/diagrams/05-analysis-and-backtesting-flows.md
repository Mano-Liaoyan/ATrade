---
status: active
owner: maintainer
updated: 2026-05-17
summary: Mermaid analysis engine and saved backtesting flow diagrams covering LEAN, Postgres persistence, async runner lifecycle, SignalR updates, and redaction boundaries.
see_also:
  - ../analysis-engines.md
  - ../backtesting.md
  - ../provider-abstractions.md
  - ../modules.md
  - ../paper-trading-workspace.md
  - ../../INDEX.md
  - ../../../README.md
  - ../../../PLAN.md
---

# Analysis And Backtesting Flows

Analysis and saved backtesting share the same provider-neutral engine seam.
Direct analysis requests and saved backtest runs both feed normalized ATrade
market-data bars into `ATrade.Analysis`; LEAN is only the first concrete
provider behind that seam.

```mermaid
flowchart TD
  UI["Next.js ANALYSIS or BACKTEST workspace"] -->|"GET engines or POST run"| API["ATrade.Api"]
  API --> Intake["IAnalysisRequestIntake<br/>ATrade.Analysis"]
  Intake -->|"symbol and chart range"| MarketData["IMarketDataService<br/>cache-aware candle read"]
  MarketData --> Candles["Normalized OhlcvCandle list<br/>MarketDataSymbolIdentity"]
  Candles --> Registry["IAnalysisEngineRegistry"]
  Registry --> NoEngine["NoConfiguredAnalysisEngine<br/>explicit not-configured result"]
  Registry --> Lean["ATrade.Analysis.Lean<br/>configured engine"]
  Lean --> Workspace["Generated analysis-only<br/>LEAN workspace"]
  Lean -. executes .-> Runtime["LEAN CLI or managed container"]
  Runtime --> Parser["LeanAnalysisResultParser"]
  Parser --> Result["Provider-neutral AnalysisResult<br/>signals, metrics, summary, details"]
  NoEngine --> Result
  Result --> API
  API --> UI

  classDef contract fill:#eef6ff,stroke:#316b9f,color:#102033
  classDef provider fill:#fff7e6,stroke:#a86800,color:#2b1b00
  classDef runtime fill:#f6eefc,stroke:#7a4b9f,color:#201020

  class API,Intake,MarketData,Candles,Registry,Result contract
  class NoEngine,Lean,Workspace,Parser provider
  class Runtime runtime
```

```mermaid
sequenceDiagram
  autonumber
  participant UI as Next.js BACKTEST workspace
  participant API as ATrade.Api
  participant Factory as IBacktestRunFactory
  participant Accounts as IPaperCapitalService
  participant Repo as Postgres saved-run repository
  participant Runner as BacktestRunHostedService
  participant Market as IMarketDataService
  participant Registry as IAnalysisEngineRegistry
  participant Hub as /hubs/backtests

  UI->>API: POST /api/backtests
  API->>Factory: validate single-symbol built-in strategy request
  Factory->>Accounts: get effective paper capital
  Accounts-->>Factory: IBKR paper balance, local ledger, or unavailable
  alt positive capital source
    Factory->>Repo: create queued run with request and capital snapshot
    Repo-->>API: saved run envelope
    API->>Hub: backtestRunCreated
    API-->>UI: 202 Accepted
  else no usable capital
    API-->>UI: 409 backtest-capital-unavailable
  end

  Runner->>Repo: fail interrupted running rows on startup
  Runner->>Repo: claim next queued run
  Repo-->>Runner: running run snapshot
  Runner->>Hub: backtestRunStatusChanged
  Runner->>Market: fetch candles server-side
  alt market data available
    Market-->>Runner: normalized candles and source metadata
    Runner->>Registry: AnalyzeAsync with strategy, engine id, bars, costs
    Registry-->>Runner: provider-neutral AnalysisResult
    Runner->>Repo: persist completed result or safe failure
    Runner->>Hub: completed or failed update
  else market data error or empty series
    Runner->>Repo: persist failed safe error
    Runner->>Hub: backtestRunFailed
  end
  Hub-->>UI: safe status, result, or error payload
```

```mermaid
stateDiagram-v2
  [*] --> queued: create saved run
  queued --> running: runner claims row
  queued --> cancelled: cancel request
  running --> completed: analysis result completed
  running --> failed: market-data, analysis, runtime, or storage error
  running --> cancelled: best-effort cancellation
  running --> failed: startup recovery marks interrupted run
  failed --> queued: retry creates new run
  cancelled --> queued: retry creates new run
  completed --> [*]
  cancelled --> [*]
  failed --> [*]
```

## How To Read It

- `ATrade.Analysis` owns the engine registry, API-facing intake, normalized
  request/result records, source metadata, and explicit no-engine fallback.
- `ATrade.Analysis.Lean` is optional and selected by configuration. It generates
  an analysis-only LEAN workspace, runs the configured runtime, parses the result
  marker, and maps output back into ATrade contracts.
- `ATrade.Backtesting` persists saved run history and runner state in Postgres,
  then executes queued jobs inside the API process through
  `BacktestRunHostedService`.
- Saved backtests fetch candles server-side through `IMarketDataService`; the
  browser never submits direct bars.
- Retry creates a new queued run from the saved request snapshot. It does not
  mutate the failed or cancelled source run.
- SignalR updates are best-effort browser notifications. Postgres state remains
  authoritative for reconnect and detail loads.

## Safety And Redaction Boundary

Saved backtest creation accepts only the provider-neutral instrument tuple,
built-in strategy id, optional engine id, bounded parameter JSON, chart range,
cost/slippage settings, and benchmark mode. Validation rejects direct bars,
custom strategy code, scripts, LEAN workspace paths, broker/order-routing
fields, credentials, gateway URLs, tokens, cookies, sessions, account
identifiers, multi-symbol requests, and portfolio payloads.

Persisted rows and SignalR payloads keep safe run ids, statuses, timestamps,
instrument identity, strategy metadata, safe errors, and provider-neutral result
envelopes. They omit account identifiers, credentials, gateway URLs, LEAN
workspace paths, raw process command lines, direct candle arrays, tokens,
cookies, session details, and order-routing fields.
