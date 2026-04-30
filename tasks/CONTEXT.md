# General — Context

**Last Updated:** 2026-04-30
**Status:** Active
**Next Task ID:** TP-028

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
- Provider-backed market data, symbol search, backend watchlists, and the
  provider-neutral analysis/LEAN seams are present from the completed TP-019
  through TP-025 batch.
- Active follow-up work is aligning repository contracts around `ATrade.slnx`
  and fixing the local IBKR/iBeam refresh transport contract.

## Active Task Queue

Active task packets live directly under `tasks/`:

| Task     | Summary                                                            |
| -------- | ------------------------------------------------------------------ |
| `TP-026` | Migrate active solution references from `ATrade.sln` to `ATrade.slnx` |
| `TP-027` | Fix the local IBKR/iBeam refresh transport contract                |

Completed task packets `TP-019` through `TP-025` currently remain under
`tasks/` with `.DONE` markers pending archival. Older completed packets live
under `tasks/archive/`.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-028`
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
| Active tasks        | `tasks/TP-026-*` and `tasks/TP-027-*`     |
| Completed pending archival | `tasks/TP-019-*` through `tasks/TP-025-*` |
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
- [ ] Archive completed `TP-019` through `TP-025` task packets when orchestration cleanup time allows.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
