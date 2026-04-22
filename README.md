---
status: active
owner: architect
updated: 2026-04-23
summary: Human-facing overview of the rebooted ATrade repository and its core operating contracts.
see_also:
  - AGENT.md
  - PLAN.md
  - docs/INDEX.md
---

# ATrade

ATrade is a documentation-first reboot of a personal swing and position trading platform.

The target system is a modular monolith with .NET 10 backends, a Next.js frontend, and Aspire 13.2 as the single local orchestrator for apps, workers, and infrastructure.

## What This Repository Defines

This repository currently defines the operating model for the next implementation:

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

The `run` contract is bootstrapped in this pass through the repo-local wrappers and a minimal Aspire AppHost. The current runnable slice launches the first scaffolded backend service, `ATrade.Api`, alongside the placeholder frontend. `scripts/README.md` captures the current surface, and `PLAN.md` tracks the next extensions.

## Repository Map

The intended structure is:

```text
ATrade/
├── AGENT.md              # Repo-wide autonomous workforce contract
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

Some of those directories are still aspirational. `PLAN.md` is the source of truth for what has been bootstrapped already.

## Read Order

For humans:

1. `README.md`
2. `PLAN.md`
3. `docs/INDEX.md`
4. `scripts/README.md`

For agents:

1. `AGENT.md`
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

The operating contract for those roles lives in `AGENT.md`, with per-role details in `.pi/agents/`.

## Current Status

This repository is in governance-first bootstrap mode.

- The old Blazor- and script-oriented docs have been replaced at the top level
- No legacy implementation docs are carried in this baseline snapshot; if any are restored later, they must be indexed as `legacy-review-pending` before agents may consult them
- The current runnable slice is Aspire AppHost + the minimal `ATrade.Api` health endpoint + the placeholder frontend
- Windows wrapper verification is backed by GitHub Actions on `windows-latest` through `tests/start-contract/start-wrapper-windows.ps1`.
- The baseline commit establishes the first worktree-capable starting point for parallel delivery under `.worktrees/`

## License

MIT License — see `LICENSE`.
