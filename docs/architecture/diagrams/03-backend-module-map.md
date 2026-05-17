---
status: active
owner: maintainer
updated: 2026-05-17
summary: Mermaid backend module dependency map for existing and planned ATrade src and worker modules.
see_also:
  - ../modules.md
  - ../overview.md
  - ../provider-abstractions.md
  - ../analysis-engines.md
  - ../backtesting.md
  - ../../INDEX.md
  - ../../../README.md
  - ../../../PLAN.md
---

# Backend Module Map

This diagram shows the current backend modular-monolith shape across `src/` and
`workers/`, plus the planned module and worker seams that are still documented
future work. It is a logical module map, not a deployment map: the current API
host composes most backend modules in-process, while Aspire AppHost starts the
API, IBKR worker, frontend, and Compose-managed infrastructure.

```mermaid
flowchart LR
  Frontend["frontend<br/>Next.js terminal workspace"] -->|"HTTP and SignalR"| Api["ATrade.Api<br/>browser-facing backend"]

  AppHost["ATrade.AppHost<br/>Aspire runtime graph"] --> Api
  AppHost --> IbkrWorker["ATrade.Ibkr.Worker<br/>paper IBKR readiness"]
  AppHost --> Frontend
  AppHost --> Postgres[("Postgres<br/>accounts, watchlists, backtests")]
  AppHost --> Timescale[("TimescaleDB<br/>market-data cache")]
  AppHost --> Redis[("Redis<br/>ephemeral cache planned")]
  AppHost --> Nats[("NATS<br/>internal events planned")]
  AppHost -. optional .-> Ibeam["local iBeam runtime<br/>IBKR Client Portal"]
  AppHost -. optional .-> LeanRuntime["LEAN runtime<br/>CLI or managed container"]

  Api --> Accounts["ATrade.Accounts<br/>overview and paper capital"]
  Api --> Brokers["ATrade.Brokers<br/>broker contracts"]
  Api --> BrokersIbkr["ATrade.Brokers.Ibkr<br/>IBKR paper adapter"]
  Api --> Orders["ATrade.Orders<br/>paper simulation"]
  Api --> Workspaces["ATrade.Workspaces<br/>watchlist preferences"]
  Api --> MarketData["ATrade.MarketData<br/>provider-neutral data seam"]
  Api --> MarketDataIbkr["ATrade.MarketData.Ibkr<br/>IBKR market data"]
  Api --> MarketDataTimescale["ATrade.MarketData.Timescale<br/>cache-aside storage"]
  Api --> Analysis["ATrade.Analysis<br/>engine registry and intake"]
  Api --> AnalysisLean["ATrade.Analysis.Lean<br/>LEAN provider"]
  Api --> Backtesting["ATrade.Backtesting<br/>saved runs and runner"]

  Accounts --> Postgres
  Accounts --> BrokersIbkr
  Orders --> BrokersIbkr
  Workspaces --> MarketData
  Workspaces --> Postgres
  Backtesting --> Accounts
  Backtesting --> MarketData
  Backtesting --> Analysis
  Backtesting --> Postgres
  Backtesting -->|"safe updates"| Api
  MarketDataTimescale --> MarketData
  MarketDataTimescale --> Timescale
  MarketDataIbkr --> MarketData
  MarketDataIbkr --> BrokersIbkr
  MarketDataIbkr -. provider calls .-> Ibeam
  Analysis --> MarketData
  AnalysisLean --> Analysis
  AnalysisLean --> MarketData
  AnalysisLean -. executes through .-> LeanRuntime
  BrokersIbkr --> Brokers
  BrokersIbkr -. readiness and paper balance .-> Ibeam
  IbkrWorker --> Brokers
  IbkrWorker --> BrokersIbkr
  IbkrWorker -. planned event use .-> Nats
  IbkrWorker -. planned state use .-> Redis
  IbkrWorker -. planned correlation use .-> Postgres

  Strategies["ATrade.Strategies<br/>planned"] -.-> MarketData
  Strategies -.-> Timescale
  Strategies -.-> Nats
  StrategyWorker["strategy-worker<br/>planned"] -.-> Strategies
  StrategyWorker -.-> MarketData
  StrategyWorker -.-> Nats
  Polygon["ATrade.MarketData.Polygon<br/>planned"] -.-> MarketData
  Polygon -.-> Timescale
  Polygon -.-> Redis
  Polygon -.-> Nats
  PolygonWorker["polygon-worker<br/>planned"] -.-> Polygon
  PolygonWorker -.-> Timescale
  PolygonWorker -.-> Redis
  PolygonWorker -.-> Nats

  ServiceDefaults["ATrade.ServiceDefaults<br/>hosting and local runtime contract"] -.-> AppHost
  ServiceDefaults -.-> Api
  ServiceDefaults -.-> IbkrWorker
  ServiceDefaults -.-> Accounts
  ServiceDefaults -.-> BrokersIbkr
  ServiceDefaults -.-> MarketDataIbkr
  ServiceDefaults -.-> AnalysisLean

  classDef exists fill:#eef6ff,stroke:#316b9f,color:#102033
  classDef planned fill:#fff7e6,stroke:#a86800,color:#2b1b00,stroke-dasharray: 5 5
  classDef infra fill:#f2f2f2,stroke:#666,color:#111
  classDef external fill:#f6eefc,stroke:#7a4b9f,color:#201020

  class Frontend,AppHost,Api,Accounts,Brokers,BrokersIbkr,Orders,Workspaces,MarketData,MarketDataIbkr,MarketDataTimescale,Analysis,AnalysisLean,Backtesting,IbkrWorker,ServiceDefaults exists
  class Strategies,StrategyWorker,Polygon,PolygonWorker planned
  class Postgres,Timescale,Redis,Nats infra
  class Ibeam,LeanRuntime external
```

## How To Read It

- Solid arrows are implemented module composition, project references, or active
  runtime wiring.
- Dotted arrows are optional runtime resources, infrastructure references that
  are wired ahead of deeper behavior, or planned modules/workers.
- `ATrade.Api` is the browser boundary. Backend modules should not depend upward
  on the API or frontend.
- Concrete providers normalize through their contract modules:
  `ATrade.Brokers.Ibkr` through `ATrade.Brokers`,
  `ATrade.MarketData.Ibkr` through `ATrade.MarketData`, and
  `ATrade.Analysis.Lean` through `ATrade.Analysis`.

## Existing And Planned Project Names

Existing backend projects under `src/` are `ATrade.AppHost`,
`ATrade.ServiceDefaults`, `ATrade.Api`, `ATrade.Accounts`, `ATrade.Orders`,
`ATrade.Brokers`, `ATrade.Brokers.Ibkr`, `ATrade.MarketData`,
`ATrade.MarketData.Ibkr`, `ATrade.MarketData.Timescale`, `ATrade.Analysis`,
`ATrade.Analysis.Lean`, `ATrade.Backtesting`, and `ATrade.Workspaces`.

The existing worker project is `workers/ATrade.Ibkr.Worker`. The planned seams
remain `ATrade.Strategies`, `ATrade.MarketData.Polygon`, `strategy-worker`, and
`polygon-worker`.
