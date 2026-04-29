---
status: active
owner: scrum-master
updated: 2026-04-29
summary: Bootstrap plan for the governance-first ATrade reboot.
see_also:
  - AGENTS.md
  - scripts/README.md
  - docs/INDEX.md
---

# ATrade Bootstrap Plan

**Last updated:** 2026-04-29

## Current Focus

Use the implemented paper-trading workspace MVP — safe IBKR status/simulation, deterministic mocked market data, SignalR updates, and the `lightweight-charts` Next.js workspace — as the baseline for deeper backend-owned preferences, provider-backed data, durable paper orders, and strategy/LEAN seams while preserving the current AppHost graph.

## Milestones

- [x] ~~Rewrite top-level repository identity around Aspire 13.2, Next.js, and autonomous agents~~
- [x] ~~Create the first baseline commit so git worktrees become available~~
- [x] ~~Bootstrap the repo-local `start run` wrapper contract and Linux-hosted AppHost path from `scripts/README.md`~~
- [x] ~~Verify `./start.ps1 run` and `./start.cmd run` on a Windows-hosted runtime or CI worker~~
- [x] ~~Bootstrap the first Aspire AppHost graph for `ATrade.Api` plus the Next.js home page~~
- [x] ~~Author the first implementation-facing architecture and module docs for the new codebase~~
- [x] ~~Establish GitHub labels, issue templates, and Actions for autonomous coordination~~
- [x] ~~Scaffold the first .NET 10 backend projects and Next.js frontend~~
- [x] ~~Declare managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources in the AppHost graph~~
- [x] ~~Add the first backend feature-module shells and the inert `ATrade.Ibkr.Worker` shell~~
- [x] ~~Extend the AppHost graph with real worker wiring and application resource consumers~~
- [x] ~~Add the first backend feature behavior on top of the bootstrap slice~~
- [x] ~~Stage and deliver the first paper-trading workspace slice (paper-only IBKR session status, mocked market/trending data, SignalR updates, `lightweight-charts` UI, and simulated order workflow)~~

## Active Cross-Role Dependencies

- Senior Engineer and DevOps must preserve the new infrastructure-aware AppHost graph while adding future workers without breaking the cross-platform `start run` contract.
- Architect and Scrum Master must keep the roadmap, task inventory, and active docs aligned as the first feature-module slices are staged.

## Notes

- Only indexed `active` docs are authoritative. Legacy docs must be explicitly reintroduced and marked before use.
- The single-command local startup contract is `start run` on both Unix and Windows.
- Aspire 13.2 remains the preferred orchestrator and currently manages `ATrade.Api`, `ATrade.Ibkr.Worker`, the Next.js home page, and named `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources, with explicit AppHost resource references wired into the API and worker graph. The first backend feature behavior is now live as the read-only Accounts overview endpoint at `GET /api/accounts/overview` alongside `GET /health`.
- `docs/architecture/paper-trading-workspace.md` now defines the paper-only workspace contract: official IBKR Gateway session status, mocked market/trending data for the first slice, SignalR browser updates, `lightweight-charts` as the MVP charting baseline, and LEAN as a future seam rather than an immediate dependency. TP-016 implemented the safe IBKR status/order-simulation backend; TP-018 recovered the deterministic mocked market-data HTTP/SignalR contract locally and added the first Next.js trading workspace with localStorage watchlists, candlestick charts, indicators, SignalR fallback, and no-real-orders guardrails.
- `.worktrees/` is now available for isolated parallel feature delivery.
