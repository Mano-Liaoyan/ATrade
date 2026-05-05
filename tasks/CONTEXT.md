# General — Context

**Last Updated:** 2026-05-05
**Status:** Active
**Next Task ID:** TP-055

---

## Project Overview

ATrade is a personal swing and position trading platform implemented as a
.NET 10 / Next.js modular monolith and orchestrated locally by Aspire 13.2.

Use `README.md` for the human-facing overview and `PLAN.md` for the current
implementation queue.

## Current Repository State

- `src/ATrade.AppHost` launches the local Aspire graph.
- `src/ATrade.Api` exposes health, accounts overview, safe IBKR status,
  simulated orders, market-data HTTP endpoints, analysis endpoints, backend
  workspace watchlist endpoints, and a market-data SignalR hub.
- `workers/ATrade.Ibkr.Worker` provides the current safe IBKR worker shell.
- `frontend/` contains the Next.js paper-trading workspace.
- AppHost-managed local infrastructure includes Postgres, TimescaleDB, Redis,
  and NATS.
- Provider-backed IBKR/iBeam market data, symbol search, backend watchlists,
  provider-neutral analysis/LEAN seams, the `ATrade.slnx` solution-file
  contract, the HTTPS local iBeam Client Portal transport contract,
  AppHost-managed LEAN Docker runtime wiring, durable AppHost Postgres
  watchlists, durable TimescaleDB cache rows, frontend workflow module seams,
  and the completed `TP-045` through `TP-054` frontend reconstruction,
  no-command cutover, simplified workspace layout, top-chrome/filter-density
  cleanup, and restored stock chart visibility are present.

## Domain Vocabulary

- **Exact Instrument Identity** — the backend-owned provider-neutral identity
  tuple for a tradable or chartable instrument: provider, provider symbol id,
  symbol, exchange, currency, and asset class, normalized by
  `ATrade.MarketData.ExactInstrumentIdentity`. Provider-backed market-data
  search, trending, candle, indicator, latest-update, Timescale cache, and
  watchlist flows carry this identity where available. Backend-owned persisted
  keys derive from the normalized tuple and retain the legacy
  `instrumentKey` / `pinKey` segment shape; frontend code may compute
  provisional keys only for optimistic UI state until the backend returns
  authoritative `instrumentKey` / `pinKey` values.

## Active Task Queue

No ready implementation tasks are currently queued after the completed
`TP-053` through `TP-054` wave.

The most recent completed batch:

- `TP-053` — removed the remaining top app brand header/global safety strip and compacted market-monitor filters while preserving module safety surfaces
- `TP-054` — restored visible stock chart rendering with measured `lightweight-charts` sizing, non-collapsing chart layout, truthful empty/provider states, and chart visibility validation

The next new Taskplane packet should use `TP-055`.

Completed task packets through `TP-054` are present in `tasks/`; completed
packets should be archived when convenient.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-055`
- New task prompts and verification commands should use `ATrade.slnx` for repo-level .NET build/test/list operations.
- Task packets must include `PROMPT.md` and `STATUS.md`
- Finished task directories should be moved to `tasks/archive/`

## Runtime Contract

The repo-level solution-file contract is `ATrade.slnx` for active .NET
build/test/list operations, including future task prompts. The legacy
`ATrade.sln` file is retained only as a temporary non-authoritative
compatibility artifact for older tooling.

The repo-local `start` shim is the single startup contract across platforms:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants delegate to the Aspire AppHost.

## Key Files

| Category            | Path                                                      |
| ------------------- | --------------------------------------------------------- |
| Human overview      | `README.md`                                               |
| Current plan        | `PLAN.md`                                                 |
| Documentation index | `docs/INDEX.md`                                           |
| Startup contract    | `scripts/README.md`                                       |
| Active tasks        | None currently queued; next packet is `TP-055`            |
| Completed tasks     | `tasks/TP-042-*` through `tasks/TP-054-*`                 |
| Archived tasks      | `tasks/archive/TP-002-*` through `tasks/archive/TP-041-*` |
| Taskplane config    | `.pi/taskplane-config.json`                               |
| AppHost             | `src/ATrade.AppHost/Program.cs`                           |
| API                 | `src/ATrade.Api/Program.cs`                               |
| Frontend            | `frontend/`                                               |

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- Durable runtime/code changes must update relevant docs in the same change.
- Do not commit secrets, IBKR credentials, account identifiers, tokens, or session cookies.
- Do not add real order placement or live-trading behavior in the current task queue.

## Technical Debt / Future Work

- [ ] Review the frontend dependency audit from TP-018 (`lightweight-charts` and `@microsoft/signalr` reported moderate npm advisories) without forcing breaking upgrades.
- [ ] Review TP-046 frontend npm audit advisories for `next` and `postcss` after the terminal UI stack bootstrap; do not force breaking upgrades inside the reconstruction queue.
- [x] Archive completed `TP-019` through `TP-041` task packets before starting the previous queued run.
- [ ] Archive completed `TP-042` through `TP-054` task packets when convenient.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
- [ ] Keep local iBeam Client Portal transport on HTTPS (`https://127.0.0.1:<gateway-port>`) and restrict self-signed certificate handling to loopback iBeam development traffic.
