# General — Context

**Last Updated:** 2026-04-23
**Status:** Active
**Next Task ID:** TP-010

---

## Project Overview

ATrade is a documentation-first reboot of a personal swing and position
trading platform. The target system is a **modular monolith** orchestrated
locally by Aspire 13.2 through a single semantic command: `start run`.

See `README.md` for the human-facing overview and `PLAN.md` for the
bootstrap plan and current milestones.

## Target Stack

| Layer                   | Choice                                                        |
| ----------------------- | ------------------------------------------------------------- |
| Backend                 | .NET 10                                                       |
| Orchestrator            | Aspire 13.2 (manages apps, workers, infra)                    |
| Frontend                | Next.js                                                       |
| Infrastructure          | Postgres, TimescaleDB, Redis, NATS                            |
| Broker / Data (phase 1) | IBKR, Polygon                                                 |
| Agent workflow          | GitHub issues, draft PRs, reusable skills, parallel worktrees |

## Run Contract

The repo-local `start` shim is the single startup contract across platforms:

- Unix-like: `./start run`
- Windows: `./start.cmd run` or `./start.ps1 run`

All variants delegate to the Aspire AppHost. In this repo, `start run`
always refers to this shim, not the Windows shell built-in.

## Current Repository State

This repository is in **governance-first bootstrap mode**, but the first
runnable slice is now in place:

- Top-level identity (README, PLAN, AGENTS) is rewritten around Aspire 13.2,
  Next.js, and the autonomous agent workforce.
- The first implementation-facing architecture docs and GitHub coordination
  primitives now exist under `docs/architecture/`, `docs/process/`, and
  `.github/`.
- The baseline commit exists, so `.worktrees/` is available for isolated
  parallel delivery.
- `src/` now contains `ATrade.AppHost`, `ATrade.ServiceDefaults`, and the
  minimal `ATrade.Api` scaffold; `frontend/` now contains the first real
  Next.js home page slice.
- `workers/`, AppHost-managed infrastructure resources, and deeper backend
  feature modules remain future work tracked in `PLAN.md` and queued task
  inventory.
- Only documents marked `status: active` in `docs/INDEX.md` are
  authoritative. Legacy docs must be reintroduced as
  `legacy-review-pending` before use.

## Taskplane Usage

This is the default task area for ATrade. Tasks that don't belong to a
specific domain area are created here.

- Parallel batch: `/orch all`
- Single task: `/orch <path/to/PROMPT.md>`
- Tasks must follow the `EXAMPLE-001` / `EXAMPLE-002` PROMPT.md + STATUS.md
  shape under `tasks/<TASK-ID>-<slug>/`.

## Autonomous Workforce

Agent roles operating in this repo (charters in `.pi/agents/`):

- Architect
- Senior Engineer
- Senior Test Engineer
- DevOps Engineer
- Scrum Master
- Code Reviewer
- Handyman
- Onboarder

The repo-wide operating contract is `AGENTS.md`.

## Documentation Rules

- Every durable repository addition must add or update an indexed document.
- `docs/INDEX.md` is the discovery layer.
- Only `active` docs drive implementation decisions.
- `legacy-review-pending` and `obsolete` docs must not be used as authority.

## Key Files

| Category            | Path                        |
| ------------------- | --------------------------- |
| Repo identity       | `README.md`                 |
| Bootstrap plan      | `PLAN.md`                   |
| Agent contract      | `AGENTS.md`                 |
| Doc index           | `docs/INDEX.md`             |
| Run contract design | `scripts/README.md`         |
| Tasks               | `tasks/`                    |
| Taskplane config    | `.pi/taskplane-config.json` |
| Parallel worktrees  | `.worktrees/`               |

## Technical Debt / Future Work

_Items discovered during task execution are logged here by agents._

- [ ] `TP-007` — Reconcile planning and docs with the actual repo state
- [ ] `TP-008` — Extend AppHost with managed infrastructure resources
- [ ] `TP-009` — Scaffold first feature-module shells and the IBKR worker shell
- Open milestones tracked in `PLAN.md` should stay aligned with the task packets
  above and with the active docs.
