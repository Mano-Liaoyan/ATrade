---
status: active
owner: maintainer
updated: 2026-04-29
summary: Human-facing overview of the current ATrade application, run contract, and active Taskplane work queue.
see_also:
  - PLAN.md
  - docs/INDEX.md
  - scripts/README.md
  - docs/architecture/overview.md
  - docs/architecture/modules.md
  - docs/architecture/paper-trading-workspace.md
---

# ATrade

ATrade is a personal swing and position trading platform built as a modular
monolith with .NET 10, Next.js, and Aspire 13.2.

The repository currently contains a runnable local stack and a Taskplane work
queue for the next provider-backed trading workspace increment.

## Current Stack

- Backend: `.NET 10`
- Frontend: `Next.js`
- Local orchestrator: `Aspire 13.2`
- Infrastructure: `Postgres`, `TimescaleDB`, `Redis`, `NATS`
- Broker/data direction: `IBKR` through local iBeam/Gateway work queued in `TP-021` and `TP-022`
- Analysis direction: provider-neutral analysis contracts plus LEAN integration queued in `TP-024` and `TP-025`

## Run Contract

The repository-wide startup contract is the repo-local `start` shim:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants delegate to the Aspire AppHost so one command can bring up the
API, worker, frontend, and local infrastructure.

## Current Runtime Surface

The current runnable slice includes:

- `src/ATrade.AppHost` — Aspire graph for the API, IBKR worker, Next.js frontend, Postgres, TimescaleDB, Redis, and NATS.
- `src/ATrade.Api` — browser-facing backend with:
  - `GET /health`
  - `GET /api/accounts/overview`
  - `GET /api/broker/ibkr/status`
  - `POST /api/orders/simulate`
  - `GET /api/market-data/trending`
  - `GET /api/market-data/{symbol}/candles`
  - `GET /api/market-data/{symbol}/indicators`
  - `/hubs/market-data`
- `workers/ATrade.Ibkr.Worker` — safe paper-session/status monitoring shell.
- `frontend/` — Next.js paper-trading workspace with trending symbols, chart pages, SignalR fallback, and an MVP watchlist.

The current market-data and watchlist behavior is still the MVP baseline:
market data is deterministic mocked data and pinned symbols are browser-local.
The active task queue replaces those pieces with provider abstractions,
Postgres persistence, real IBKR/iBeam data, IBKR search, and LEAN analysis.

## Active Task Queue

Active Taskplane packets live directly under `tasks/`:

| Task     | Purpose                                                            |
| -------- | ------------------------------------------------------------------ |
| `TP-019` | Provider-neutral broker and market-data abstractions               |
| `TP-020` | Postgres-persisted pinned stock/watchlist state                    |
| `TP-021` | `voyz/ibeam:latest` runtime and ignored `.env` IBKR login contract |
| `TP-022` | IBKR/iBeam market-data provider and production mock removal        |
| `TP-023` | IBKR stock search and pin-any-symbol workflow                      |
| `TP-024` | Provider-neutral analysis engine abstraction                       |
| `TP-025` | LEAN as the first analysis engine provider                         |

Completed Taskplane packets have been moved to `tasks/archive/`.

## Repository Map

```text
ATrade/
├── README.md             # This overview
├── PLAN.md               # Current implementation plan
├── docs/                 # Indexed active documentation
├── scripts/              # Startup and local environment contracts
├── src/                  # .NET 10 backend modules and AppHost
├── workers/              # Long-running worker processes
├── frontend/             # Next.js application
├── tasks/                # Active Taskplane packets and archive
└── .pi/                  # Taskplane/Pi runtime config, runtime agents, and skill symlinks
```

Reusable `.pi/skills/` entries are opt-in Pi skills. `.pi/agents/` files are Taskplane runtime
agents used by the orchestrator.

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- Durable code or runtime changes must update the relevant active docs in the same change.
- Secrets, IBKR credentials, account identifiers, tokens, and session cookies must stay out of git and belong only in ignored local `.env` files.
- No task may introduce real order placement or live-trading behavior unless a future task explicitly changes the safety contract and docs.

## Verification Entry Points

Common verification scripts live under `tests/`:

- `tests/start-contract/start-wrapper-tests.sh`
- `tests/apphost/api-bootstrap-tests.sh`
- `tests/apphost/accounts-feature-bootstrap-tests.sh`
- `tests/apphost/ibkr-paper-safety-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`

Task packets list their own targeted and full verification commands.

## License

MIT License — see `LICENSE`.
