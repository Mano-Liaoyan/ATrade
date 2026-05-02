# General — Context

**Last Updated:** 2026-05-02
**Status:** Active
**Next Task ID:** TP-042

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
  watchlists, and durable TimescaleDB cache rows are present from the completed
  TP-019 through TP-035 batches.

## Domain Vocabulary

- **Exact Instrument Identity** — the provider-neutral identity tuple for a
  tradable or chartable instrument: provider, provider symbol id, symbol,
  exchange, currency, and asset class. Backend-owned persisted keys derive from
  this tuple; frontend code may compute provisional keys only for optimistic UI
  state until the backend returns authoritative `instrumentKey` / `pinKey`
  values.

## Active Task Queue

Ready implementation tasks now queued:

- `TP-036` — deepen the local runtime contract module and fix committed runtime/default drift
- `TP-037` — deepen the Exact Instrument Identity module across market data, Timescale, Workspaces, and frontend pins
- `TP-038` — deepen the market-data read module into an async, cache-aware read seam
- `TP-039` — deepen the shared IBKR/iBeam session readiness module for broker, market-data, and worker callers
- `TP-040` — deepen analysis and workspace watchlist intake modules so `ATrade.Api` delegates domain ordering
- `TP-041` — deepen frontend workspace workflow modules for watchlist, search, chart, and stream fallback orchestration

Recommended orchestration order is sequential from `TP-036` through `TP-041`
because each task stabilizes a seam used by the next task.

The next new Taskplane packet should use `TP-042`.

Completed task packets `TP-019` through `TP-035` currently remain under
`tasks/` with `.DONE` markers pending archival. Older completed packets live
under `tasks/archive/`.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-042`
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

| Category            | Path                                      |
| ------------------- | ----------------------------------------- |
| Human overview      | `README.md`                               |
| Current plan        | `PLAN.md`                                 |
| Documentation index | `docs/INDEX.md`                           |
| Startup contract    | `scripts/README.md`                       |
| Active tasks        | `tasks/TP-036-*` through `tasks/TP-041-*` |
| Completed pending archival | `tasks/TP-019-*` through `tasks/TP-035-*` |
| Archived tasks      | `tasks/archive/`                          |
| Taskplane config    | `.pi/taskplane-config.json`               |
| AppHost             | `src/ATrade.AppHost/Program.cs`           |
| API                 | `src/ATrade.Api/Program.cs`               |
| Frontend            | `frontend/`                               |

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- Durable runtime/code changes must update relevant docs in the same change.
- Do not commit secrets, IBKR credentials, account identifiers, tokens, or session cookies.
- Do not add real order placement or live-trading behavior in the current task queue.

## Technical Debt / Future Work

- [ ] Review the frontend dependency audit from TP-018 (`lightweight-charts` and `@microsoft/signalr` reported moderate npm advisories) without forcing breaking upgrades.
- [ ] Archive completed `TP-019` through `TP-035` task packets when orchestration cleanup time allows.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
- [ ] Keep local iBeam Client Portal transport on HTTPS (`https://127.0.0.1:<gateway-port>`) and restrict self-signed certificate handling to loopback iBeam development traffic.
