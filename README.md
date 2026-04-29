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

The `run` contract is bootstrapped in this pass through the repo-local wrappers and a minimal Aspire AppHost. The current runnable slice launches `ATrade.Api`, whose stable surface now includes `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`, `POST /api/orders/simulate`, deterministic mocked market-data endpoints for trending/candles/indicators, and `/hubs/market-data`; an AppHost-managed `ATrade.Ibkr.Worker` background service that reports safe paper-session states; and the first Next.js paper-trading workspace routes; declares managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources in the AppHost graph; wires explicit managed-resource references from `api` to the backend infrastructure plus from `ibkr-worker` to its initial `Postgres` / `Redis` / `NATS` dependencies; and forwards the safe paper-only IBKR environment contract into the API/worker graph. `ATrade.Brokers.Ibkr` now provides the official paper-safe broker seam, `ATrade.Orders` now provides deterministic simulation behavior, and `ATrade.MarketData` now provides deterministic mocked market-data behavior for the frontend MVP. Developer-controlled local bind ports, frontend API base URLs, and paper-mode placeholders now come from the repo-level `.env` contract (`.env.example` defaults plus optional ignored `.env` overrides). `scripts/README.md` captures the current surface, and `PLAN.md` tracks the next extensions.

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
- The current runnable slice is Aspire AppHost + `ATrade.Api` endpoints for `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`, `POST /api/orders/simulate`, `GET /api/market-data/trending`, candle/indicator queries, and `/hubs/market-data` + an AppHost-managed `ATrade.Ibkr.Worker` background service that reports safe paper-session states + the first Next.js trading workspace UI + named Aspire-managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources.
- The first paper-trading workspace slice now implements the staged paper-trading workspace contract with Next.js watchlists persisted in browser `localStorage`, backend-driven mocked trending stocks/ETFs, symbol navigation, `lightweight-charts` candlestick charts, `1m` / `5m` / `1h` / `1D` timeframe switching, moving-average / RSI / MACD indicators, SignalR updates with HTTP fallback, and no-real-orders labeling. Durable backend preferences, provider-backed market data, paper-order storage, and future LEAN signal integration remain later work documented in `docs/architecture/paper-trading-workspace.md`.
- `ATrade.Accounts` now provides bootstrap-safe read-only overview behavior exposed through the API; `ATrade.Brokers.Ibkr` now provides the paper-only broker adapter seam; `ATrade.Orders` now provides deterministic simulation behavior; `ATrade.MarketData` now provides deterministic mocked market-data behavior; and `ATrade.Ibkr.Worker` is part of the runtime graph with safe status monitoring while still intentionally lacking broader broker, messaging, and database consumers.
- Direct API startup and endpoint verification are covered by `tests/apphost/api-bootstrap-tests.sh`, `tests/apphost/accounts-feature-bootstrap-tests.sh`, `tests/apphost/ibkr-paper-safety-tests.sh`, and `tests/apphost/market-data-feature-tests.sh`.
- Direct frontend startup, home-page marker verification, and the trading workspace smoke checks are covered by `tests/apphost/frontend-nextjs-bootstrap-tests.sh` and `tests/apphost/frontend-trading-workspace-tests.sh`.
- Windows wrapper verification is backed by GitHub Actions on `windows-latest` through `tests/start-contract/start-wrapper-windows.ps1`.
- The baseline commit establishes the first worktree-capable starting point for parallel delivery under `.worktrees/`.
- Additional worker processes and deeper backend/frontend feature modules remain future work tracked in `PLAN.md`; the AppHost-managed infrastructure layer is now declared and explicitly referenced by the current `api` and `ibkr-worker` graph resources, even though application behavior still has not started consuming those dependencies.

## License

MIT License — see `LICENSE`.
