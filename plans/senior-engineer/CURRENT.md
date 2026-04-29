---
status: active
owner: senior-engineer
updated: 2026-04-24
summary: Live plan for the Senior Engineer role.
see_also:
  - ../../AGENTS.md
  - ../../PLAN.md
  - ../../.pi/agents/senior-engineer.md
---

# Senior Engineer Current Plan

**Last updated:** 2026-04-29

## Current Focus

Extend the first real backend feature behavior on top of the infrastructure-aware `start run` AppHost graph.

## Active Checklist

- [x] Scaffold the first backend projects against the existing AppHost and service defaults
- [x] Replace the placeholder frontend with the first Next.js application slice when an implementation issue is ready
- [ ] Extend the AppHost graph as architect-approved services and infrastructure resources are introduced

## Blockers

- None right now

## Resume From Here

- TP-014 landed the first real backend feature slice by turning `ATrade.Accounts` into a deterministic bootstrap overview module, exposing `GET /api/accounts/overview` from `ATrade.Api`, adding `tests/apphost/accounts-feature-bootstrap-tests.sh`, and syncing the active docs and milestone state.
- TP-012 externalized the developer-controlled local port allocation into the repo-level `.env` contract; the next implementation slice should deepen backend/worker feature behavior without regressing the runtime graph or local-port contract.

## Recent Progress

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

- `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `bash tests/apphost/accounts-feature-bootstrap-tests.sh`
- `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `bash tests/apphost/local-port-contract-tests.sh`
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
