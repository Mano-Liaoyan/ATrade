# General — Context

**Last Updated:** 2026-04-29
**Status:** Active
**Next Task ID:** TP-026

---

## Project Overview

ATrade is a personal swing and position trading platform implemented as a
.NET 10 / Next.js modular monolith and orchestrated locally by Aspire 13.2.

Use `README.md` for the human-facing overview and `PLAN.md` for the current
implementation queue.

## Current Repository State

- `src/ATrade.AppHost` launches the local Aspire graph.
- `src/ATrade.Api` exposes health, accounts overview, safe IBKR status,
  simulated orders, market-data HTTP endpoints, and a market-data SignalR hub.
- `workers/ATrade.Ibkr.Worker` provides the current safe IBKR worker shell.
- `frontend/` contains the Next.js paper-trading workspace.
- AppHost-managed local infrastructure includes Postgres, TimescaleDB, Redis,
  and NATS.
- The MVP workspace still uses deterministic mocked market data and a
  browser-local watchlist; active tasks replace these with real provider-backed
  behavior.

## Active Task Queue

Active task packets live directly under `tasks/`:

| Task | Summary |
|------|---------|
| `TP-019` | Provider-neutral broker and market-data abstractions |
| `TP-020` | Postgres-persisted pinned stock/watchlist state |
| `TP-021` | `voyz/ibeam:latest` runtime and ignored `.env` IBKR login contract |
| `TP-022` | IBKR/iBeam market-data provider and production mock removal |
| `TP-023` | IBKR stock search and pin-any-symbol workflow |
| `TP-024` | Provider-neutral analysis engine abstraction |
| `TP-025` | LEAN as the first analysis engine provider |

Completed task packets have been moved to `tasks/archive/`.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-026`
- Task packets must include `PROMPT.md` and `STATUS.md`
- Finished task directories should be moved to `tasks/archive/`

## Runtime Contract

The repo-local `start` shim is the single startup contract across platforms:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants delegate to the Aspire AppHost.

## Key Files

| Category | Path |
|----------|------|
| Human overview | `README.md` |
| Current plan | `PLAN.md` |
| Documentation index | `docs/INDEX.md` |
| Startup contract | `scripts/README.md` |
| Active tasks | `tasks/TP-019-*` through `tasks/TP-025-*` |
| Archived tasks | `tasks/archive/` |
| Taskplane config | `.pi/taskplane-config.json` |
| AppHost | `src/ATrade.AppHost/Program.cs` |
| API | `src/ATrade.Api/Program.cs` |
| Frontend | `frontend/` |

## Cleanup State

The old role-based planning and workforce files have been removed:

- `plans/` no longer exists.
- Repo-local workforce agent role files were removed from `.pi/agents/`.
- Repo-local workforce skills were removed from `.pi/skills/`.
- Remaining `.pi/agents/` files are Taskplane runtime agents used by the orchestrator.

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- Durable runtime/code changes must update relevant docs in the same change.
- Do not commit secrets, IBKR credentials, account identifiers, tokens, or session cookies.
- Do not add real order placement or live-trading behavior in the current task queue.

## Technical Debt / Future Work

- [ ] Review the frontend dependency audit from TP-018 (`lightweight-charts` and `@microsoft/signalr` reported moderate npm advisories) without forcing breaking upgrades.
- [ ] Execute `TP-019` through `TP-025` in dependency order.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
