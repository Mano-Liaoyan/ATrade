---
status: active
owner: maintainer
updated: 2026-05-21
summary: Table of contents and recommended reading path for ATrade architecture diagrams.
see_also:
  - ../../INDEX.md
  - ../overview.md
  - ../modules.md
  - ../provider-abstractions.md
  - ../analysis-engines.md
  - ../backtesting.md
  - ../paper-trading-workspace.md
  - ../../../README.md
  - ../../../PLAN.md
---

# ATrade Architecture Diagrams

This folder is the visual reading path for ATrade. The diagrams summarize the
active architecture docs without replacing them; when a diagram and an active
architecture document disagree, the active document listed in
[`docs/INDEX.md`](../../INDEX.md) remains authoritative.

## Recommended Reading Path

| Step | Diagram | Type | Use It To Understand |
| --- | --- | --- | --- |
| 1 | [System Context](01-system-context.md) | C4-style context | The whole local system boundary, actors, providers, storage, workers, and coordination surfaces. |
| 2 | [Local Runtime And Deployment](02-local-runtime-and-deployment.md) | Deployment and startup sequence | How `start run`, Compose, Aspire AppHost, app services, optional iBeam, and optional LEAN fit together. |
| 3 | [Backend Module Map](03-backend-module-map.md) | Module dependency map | Existing `src/` projects, the IBKR worker, infrastructure dependencies, and planned provider/strategy seams. |
| 4 | [Provider And Market-Data Flows](04-provider-and-market-data-flows.md) | Provider/data flow and identity model | Broker status, paper capital, Exact Instrument Identity, Timescale cache-aside, IBKR/iBeam, and watchlist persistence. |
| 5 | [Analysis And Backtesting Flows](05-analysis-and-backtesting-flows.md) | Sequence and state diagrams | Analysis engine dispatch, optional LEAN execution, saved backtest creation, runner lifecycle, SignalR updates, and redaction boundaries. |
| 6 | [Frontend Terminal Workspace Diagrams](06-frontend-terminal-workspace.md) | Route, component, boundary, and streaming diagrams | The Next.js terminal workspace routes, workflow hooks, API-only browser boundary, streaming fallback, and desktop scroll ownership. |
| 7 | [Operations And Safety](07-operations-and-safety.md) | Process and guardrail diagrams | Documentation authority, GitHub coordination, verification entry points, runtime secrets, and paper-only safety rules. |

## Coverage Matrix

| Project Area | Primary Diagrams | Notes |
| --- | --- | --- |
| Human/operator workflow | [01](01-system-context.md), [07](07-operations-and-safety.md) | Covers the local trader/operator, GitHub coordination, docs authority, and verification net. |
| Startup and orchestration | [02](02-local-runtime-and-deployment.md), [07](07-operations-and-safety.md) | Covers Unix, PowerShell, and Command Prompt shims, `.env` precedence, Compose-managed infrastructure, Aspire app services, and dashboard telemetry. |
| Infrastructure | [01](01-system-context.md), [02](02-local-runtime-and-deployment.md), [03](03-backend-module-map.md), [04](04-provider-and-market-data-flows.md) | Covers Postgres, TimescaleDB, Redis, NATS, named volumes, cache-aside reads, optional iBeam, and optional LEAN Docker runtime. |
| Backend API and modules | [03](03-backend-module-map.md), [04](04-provider-and-market-data-flows.md), [05](05-analysis-and-backtesting-flows.md) | Covers `ATrade.Api`, Accounts, Brokers, Orders, MarketData, Analysis, Backtesting, Workspaces, concrete IBKR/LEAN providers, and planned strategy/Polygon seams. |
| Workers | [01](01-system-context.md), [02](02-local-runtime-and-deployment.md), [03](03-backend-module-map.md) | Covers `ATrade.Ibkr.Worker` today plus documented planned worker seams. |
| Frontend | [06](06-frontend-terminal-workspace.md) | Covers routes, components, workflow hooks, HTTP/SignalR clients, chart/backtest flows, visible-disabled modules, and desktop reachability guardrails. |
| Provider safety | [04](04-provider-and-market-data-flows.md), [05](05-analysis-and-backtesting-flows.md), [07](07-operations-and-safety.md) | Covers provider-neutral payloads, safe unavailable states, no synthetic production data, no secret leaks, and no live order placement. |
| Testing and verification | [07](07-operations-and-safety.md) | Points readers to the solution, start-wrapper, AppHost/Compose, backend contract, and frontend regression verification families. |

## Diagram Conventions

- Solid arrows show current implemented contracts, composition, or runtime
  wiring.
- Dotted arrows show optional local runtimes, planned seams, or future deeper
  use of already wired infrastructure.
- Storage nodes show ownership boundaries, not direct browser access.
- Provider names such as IBKR/iBeam and LEAN appear only behind ATrade
  provider-neutral seams.
- These diagrams describe local development architecture. Production deployment
  topology is intentionally out of scope for the current active docs.
