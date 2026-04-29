---
status: active
owner: architect
updated: 2026-04-29
summary: Human-facing overview of the rebooted ATrade repository and its core operating contracts.
see_also:
  - AGENTS.md
  - PLAN.md
  - docs/INDEX.md
---

# ATrade

ATrade is a documentation-first reboot of a personal swing and position trading platform.

The target system is a modular monolith with .NET 10 backends, a Next.js frontend, and Aspire 13.2 as the single local orchestrator for apps, workers, and infrastructure.

## What This Repository Defines

This repository currently defines the operating model and the first runnable bootstrap slice for the next implementation:

- One semantic command to start the full stack: `start run`
- Aspire 13.2 as the orchestration layer for backend services, Next.js, and infrastructure
- An autonomous multi-agent development system that can plan, implement, review, document, and evolve itself
- A documentation contract where only tracked, current docs may guide agents

This README is intentionally conceptual. It describes the target repo contract, not a finished implementation.

## Stack Contract

The target stack is:

- Backend: `.NET 10`
- Orchestrator: `Aspire 13.2`
- Frontend: `Next.js`
- Infrastructure: `Postgres`, `TimescaleDB`, `Redis`, `NATS`
- Broker/data focus: `IBKR` and `Polygon` for the first delivery phase
- Agent workflow: GitHub issues, draft PRs, reusable skills, and parallel worktrees

## Run Contract

The repository-wide startup contract is the repo-local `start` shim.

The canonical invocations are:

- On Unix-like systems, the repo will expose `./start run`
- On Windows, the repo will expose the same contract through `./start.cmd run` and `./start.ps1 run`
- All variants delegate to Aspire AppHost so one command brings up the API, workers, Next.js, and required infrastructure

In this repository, the phrase `start run` refers to that repo-local shim contract, not the Windows shell built-in.

The `run` contract is bootstrapped in this pass through the repo-local wrappers and a minimal Aspire AppHost. The current runnable slice launches `ATrade.Api`, whose stable surface now includes `GET /health` plus the first read-only `GET /api/accounts/overview` endpoint backed by `ATrade.Accounts`, alongside an AppHost-managed `ATrade.Ibkr.Worker` shell and the first real Next.js home page; declares managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources in the AppHost graph; and wires explicit managed-resource references from `api` to the backend infrastructure plus from `ibkr-worker` to its initial `Postgres` / `Redis` / `NATS` dependencies. `ATrade.Orders` and `ATrade.MarketData` remain compileable shells only. Developer-controlled local bind ports now come from the repo-level `.env` contract (`.env.example` defaults plus optional ignored `.env` overrides). `scripts/README.md` captures the current surface, and `PLAN.md` tracks the next extensions.

## Repository Map

The intended structure is:

```text
ATrade/
├── AGENTS.md              # Repo-wide autonomous workforce contract
├── README.md             # Human-facing overview
├── PLAN.md               # Root bootstrap plan
├── .pi/agents/       # Role charters for the workforce
├── .pi/skills/       # Repo-local workflow skills
├── plans/                # Per-role current plans and archives
├── docs/                 # Indexed documentation with lifecycle status
├── scripts/              # Script contracts and later implementations
├── src/                  # .NET 10 services and AppHost
├── workers/              # Long-running workers
└── frontend/             # Next.js application
```

Some of those directories are only partially realized today. `src/` and `frontend/` already host the current runnable bootstrap slice, `workers/` now contains the first inert `ATrade.Ibkr.Worker` shell, and most feature behavior remains aspirational. `PLAN.md` is the source of truth for what has been bootstrapped already versus what is still queued.

## Read Order

For humans:

1. `README.md`
2. `PLAN.md`
3. `docs/INDEX.md`
4. `scripts/README.md`

For agents:

1. `AGENTS.md`
2. `.pi/agents/<role>.md`
3. `.pi/skills/retrieve-plan/SKILL.md`
4. `plans/<role>/CURRENT.md`
5. `PLAN.md`
6. `docs/INDEX.md` and only documents with `status: active`

## Documentation Rules

Documentation is part of the product, not an afterthought.

- Every durable repository addition must have a corresponding document or indexed reference
- `docs/INDEX.md` is the discovery layer for agents
- Only documents marked `active` are authoritative
- Documents marked `legacy-review-pending` or `obsolete` must not drive implementation decisions
- When a document becomes stale, it is marked and retained for history rather than silently reused

## Autonomous Workforce

The repository is designed for an agent workforce made up of:

- Architect
- Senior Engineer
- Senior Test Engineer
- DevOps Engineer
- Scrum Master
- Code Reviewer instances
- Handyman
- Onboarder

The operating contract for those roles lives in `AGENTS.md`, with per-role details in `.pi/agents/`.

## Current Status

This repository is still in governance-first bootstrap mode, but the bootstrap is now materially underway.

- The old Blazor- and script-oriented docs have been replaced at the top level.
- The first implementation-facing architecture docs and GitHub coordination artifacts are present under `docs/architecture/`, `docs/process/`, and `.github/`.
- No legacy implementation docs are carried in this baseline snapshot; if any are restored later, they must be indexed as `legacy-review-pending` before agents may consult them.
- The current runnable slice is Aspire AppHost + `ATrade.Api` endpoints for `GET /health` and `GET /api/accounts/overview` + an inert AppHost-managed `ATrade.Ibkr.Worker` shell + the first Next.js frontend home page + named Aspire-managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources.
- `ATrade.Accounts` now provides bootstrap-safe read-only overview behavior exposed through the API; `ATrade.Orders` and `ATrade.MarketData` remain compileable scaffolding only, and `ATrade.Ibkr.Worker` is part of the runtime graph but still intentionally lacks broker, messaging, and database behavior beyond AppHost wiring.
- Direct API startup and endpoint verification are covered by `tests/apphost/api-bootstrap-tests.sh` and `tests/apphost/accounts-feature-bootstrap-tests.sh`.
- Direct frontend startup and home-page marker verification are covered by `tests/apphost/frontend-nextjs-bootstrap-tests.sh`.
- Windows wrapper verification is backed by GitHub Actions on `windows-latest` through `tests/start-contract/start-wrapper-windows.ps1`.
- The baseline commit establishes the first worktree-capable starting point for parallel delivery under `.worktrees/`.
- Additional worker processes and deeper backend/frontend feature modules remain future work tracked in `PLAN.md`; the AppHost-managed infrastructure layer is now declared and explicitly referenced by the current `api` and `ibkr-worker` graph resources, even though application behavior still has not started consuming those dependencies.

## License

MIT License — see `LICENSE`.
