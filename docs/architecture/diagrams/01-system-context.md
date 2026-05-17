---
status: active
owner: maintainer
updated: 2026-05-17
summary: C4-ish system context diagram for ATrade external actors, runtime surfaces, provider seams, and major storage boundaries.
see_also:
  - ../../INDEX.md
  - ../overview.md
  - ../modules.md
  - ../provider-abstractions.md
  - ../paper-trading-workspace.md
  - ../../../README.md
  - ../../../PLAN.md
---

# System Context

ATrade is a local-first personal paper-trading platform built as a modular
monolith. The browser talks only to `ATrade.Api`; provider integrations,
analysis runtimes, workers, and storage stay behind server-side seams.

```mermaid
flowchart LR
    trader["Trader / local operator"]
    github["GitHub Issues and PRs"]
    taskplane["Taskplane / Pi agents"]
    ibkr["IBKR Client Portal through local iBeam"]
    lean["Optional LEAN runtime"]
    polygon["Planned Polygon market-data provider"]

    subgraph atrade["ATrade repository and local system"]
        docs["Active docs and Taskplane packets"]
        apphost["Aspire AppHost"]
        frontend["Next.js paper workspace"]
        api["ATrade.Api"]
        hubs["SignalR hubs"]
        modules["Provider-neutral backend modules"]
        worker["ATrade.Ibkr.Worker"]
        defaults["ATrade.ServiceDefaults"]
        postgres["Postgres"]
        timescale["TimescaleDB"]
        redis["Redis"]
        nats["NATS"]
    end

    trader -->|"uses"| frontend
    frontend -->|"HTTP API only"| api
    frontend <-->|"market-data and backtest updates"| hubs
    hubs --- api

    apphost -->|"launches app services"| api
    apphost -->|"launches app services"| worker
    apphost -->|"launches app services"| frontend
    defaults -->|"local runtime contract"| apphost
    defaults -->|"shared configuration and telemetry"| api
    defaults -->|"shared configuration and telemetry"| worker

    api -->|"module contracts"| modules
    worker -->|"paper readiness and status"| modules
    modules -->|"OLTP state: watchlists, capital, backtests"| postgres
    modules -->|"market-data cache and time series"| timescale
    modules -->|"ephemeral cache and locks"| redis
    modules -->|"provider-neutral internal events"| nats

    modules -->|"broker and market-data provider seam"| ibkr
    worker -->|"safe session checks"| ibkr
    modules -.->|"analysis provider seam when enabled"| lean
    modules -.->|"future provider seam"| polygon

    github <-->|"implementation coordination"| taskplane
    taskplane -->|"creates and runs scoped packets"| docs
    docs -->|"authoritative implementation context"| modules
```

## How To Read It

- The box labeled **ATrade repository and local system** is the current local
  architecture boundary, not a production deployment topology.
- `ATrade.Api` is the only browser-facing backend surface. The frontend never
  connects directly to IBKR, Postgres, TimescaleDB, Redis, or NATS.
- `Provider-neutral backend modules` covers the current `Accounts`, `Brokers`,
  `Orders`, `MarketData`, `Analysis`, `Backtesting`, and `Workspaces` seams.
  Concrete providers plug in beneath those contracts.
- Solid external arrows are implemented or current local contracts. Dashed
  arrows show optional or planned provider/runtime seams.
- Taskplane and GitHub are coordination surfaces for repository work; they are
  not part of the runtime trading path.
