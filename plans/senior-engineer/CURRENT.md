---
status: active
owner: senior-engineer
updated: 2026-04-29
summary: Live plan for the Senior Engineer role.
see_also:
  - ../../AGENTS.md
  - ../../PLAN.md
  - ../../.pi/agents/senior-engineer.md
---

# Senior Engineer Current Plan

**Last updated:** 2026-04-29

## Current Focus

Build on the completed first paper-trading workspace MVP while preserving the infrastructure-aware `start run` AppHost graph.

## Active Checklist

- [x] Scaffold the first backend projects against the existing AppHost and service defaults
- [x] Replace the placeholder frontend with the first Next.js application slice when an implementation issue is ready
- [x] ~~Add the first paper-only IBKR backend status and order-simulation slice~~
- [ ] Extend the AppHost graph as architect-approved services and infrastructure resources are introduced

## Blockers

- None right now.

## Resume From Here

- TP-018 is complete in `tasks/TP-018-nextjs-trading-workspace-ui/`: it recovered the missing mocked market-data prerequisite locally, added deterministic `/api/market-data/*` endpoints plus `/hubs/market-data`, built the Next.js trending/watchlist/chart workspace, documented the behavior, and passed the full suite. Next work should reconcile `tasks/TP-017-mocked-market-data-trending-signalr/STATUS.md` (still `Not Started` despite the recovered contract), then move toward backend-owned preferences, provider-backed market data, durable paper-order storage, or strategy/LEAN seams as architect-approved.
- TP-016 landed the backend half of the paper-trading workspace: `ATrade.Brokers.Ibkr` provides the paper-only Gateway/status seam, `ATrade.Orders` provides deterministic simulated orders, `ATrade.Api` exposes safe status/simulation endpoints, `ATrade.Ibkr.Worker` reports safe broker status, AppHost forwards the safe paper-mode contract, and `tests/apphost/ibkr-paper-safety-tests.sh` verifies redaction/live-mode rejection.
- TP-015 landed the paper-trading workspace architecture/config contract by adding `docs/architecture/paper-trading-workspace.md`, extending `.env.example` with paper-only IBKR placeholders, adding `tests/apphost/paper-trading-config-contract-tests.sh`, and syncing `README.md`, `PLAN.md`, `scripts/README.md`, and the active architecture docs. Future workspace slices should stay paper-only, route browser streaming through SignalR, prefer `lightweight-charts` for the open-source MVP, and keep LEAN as a future seam.
- TP-014 landed the first real backend feature slice by turning `ATrade.Accounts` into a deterministic bootstrap overview module, exposing `GET /api/accounts/overview` from `ATrade.Api`, adding `tests/apphost/accounts-feature-bootstrap-tests.sh`, and syncing the active docs and milestone state.
- TP-012 externalized the developer-controlled local port allocation into the repo-level `.env` contract; the next implementation slice should deepen backend/worker feature behavior without regressing the runtime graph or local-port contract.

## Recent Progress

- Completed TP-018 by recovering deterministic mocked market-data backend contracts, adding `lightweight-charts` / SignalR frontend clients, building trending/watchlist/chart routes with localStorage persistence and no-real-orders guardrails, adding `tests/apphost/frontend-trading-workspace-tests.sh`, and syncing active docs/startup status
- Completed TP-016 by adding the paper-only `ATrade.Brokers.Ibkr` adapter, safe API broker-status and order-simulation endpoints, worker/AppHost paper-mode wiring, `tests/apphost/ibkr-paper-safety-tests.sh`, and synced architecture/startup/status docs
- Completed TP-015 by adding `docs/architecture/paper-trading-workspace.md`, extending the paper-only `.env` contract, adding `tests/apphost/paper-trading-config-contract-tests.sh`, and syncing `README.md`, `PLAN.md`, `scripts/README.md`, and the active architecture docs around the staged paper-trading workspace direction
- Completed TP-014 by turning `ATrade.Accounts` from a marker-only shell into the first read-only backend slice, wiring `ATrade.Api` to expose `GET /api/accounts/overview`, adding `tests/apphost/accounts-feature-bootstrap-tests.sh`, and syncing `README.md`, `PLAN.md`, and the active architecture/startup docs
- Completed TP-012 by adding the repo-level `.env.example` port contract, wiring AppHost/API startup plus shell tests to the shared `ATRADE_*` variables, adding `tests/apphost/local-port-contract-tests.sh`, and syncing the startup docs
- Completed TP-011 by adding explicit AppHost infra `--pids-limit 2048` runtime args, deterministic `timescaledb` tuning inputs, `tests/apphost/apphost-infrastructure-runtime-tests.sh`, and truthful runtime docs for the Podman-backed Docker API startup path
- Completed TP-010 by pinning the AppHost-managed frontend `NODE_ENV` to `development`, adding `frontend/next.config.ts` to pin `turbopack.root`, extending `tests/apphost/frontend-nextjs-bootstrap-tests.sh` to verify AppHost-managed warning-free startup, and syncing `scripts/README.md`
- Completed TP-009 by scaffolding `ATrade.Accounts`, `ATrade.Orders`, `ATrade.MarketData`, and `ATrade.Ibkr.Worker`, extending shared defaults to generic-host workers, adding `tests/scaffolding/project-shells-tests.sh`, and syncing the architecture/current-state docs
- Completed TP-006 by converting `frontend/` into the first real Next.js app, adding `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, updating the wrapper regression harness for the new contract, and syncing the active docs
- Completed TP-004 by adding `tests/start-contract/start-wrapper-windows.ps1`, wiring a `windows-latest` GitHub Actions workflow, syncing verification docs, and extending the Linux regression script to assert the Windows CI path
- Completed TP-003 by scaffolding `src/ATrade.Api`, wiring it into `ATrade.AppHost`, adding bootstrap smoke coverage, and updating the implementation docs
- Reviewed and completed the bootstrap branch in `.worktrees/start-run-bootstrap`
- Verified the Linux-hosted `start run` path, direct AppHost startup, and wrapper regression coverage before handoff

## Verification

- `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `bash tests/apphost/accounts-feature-bootstrap-tests.sh`
- `bash tests/apphost/ibkr-paper-safety-tests.sh`
- `bash tests/apphost/market-data-feature-tests.sh`
- `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `bash tests/apphost/frontend-trading-workspace-tests.sh`
- `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `bash tests/apphost/local-port-contract-tests.sh`
- `bash tests/apphost/paper-trading-config-contract-tests.sh`
- `DCP_PRESERVE_EXECUTABLE_LOGS=true dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj` with a temporary repo-root `package-lock.json` fixture while asserting warning-free AppHost-managed frontend logs
- `bash tests/scaffolding/project-shells-tests.sh`
- `dotnet build ATrade.sln`
- `bash tests/start-contract/start-wrapper-tests.sh`
- `grep -n "windows-latest\|start.ps1 run\|start.cmd run" .github/workflows/windows-start-run.yml tests/start-contract/start-wrapper-windows.ps1`
- `bash tests/apphost/api-bootstrap-tests.sh`
- `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- `timeout 20s ./start run`

## References

- `scripts/README.md`
- `PLAN.md`

## Archive

- None yet
