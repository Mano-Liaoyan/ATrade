---
status: active
owner: senior-engineer
updated: 2026-04-23
summary: Live plan for the Senior Engineer role.
see_also:
  - AGENT.md
  - PLAN.md
  - .pi/agents/senior-engineer.md
---

# Senior Engineer Current Plan

**Last updated:** 2026-04-23

## Current Focus

Implement the first application scaffolds on top of the bootstrapped `start run` contract and minimal Aspire AppHost.

## Active Checklist

- [x] Scaffold the first backend projects against the existing AppHost and service defaults
- [x] Replace the placeholder frontend with the first Next.js application slice when an implementation issue is ready
- [ ] Extend the AppHost graph as architect-approved services and infrastructure resources are introduced

## Blockers

- None right now

## Resume From Here

- TP-006 replaced the placeholder frontend with the first real Next.js home page and smoke coverage; the next implementation slice should extend the AppHost graph with backend feature modules or architect-approved infrastructure resources.

## Recent Progress

- Completed TP-006 by converting `frontend/` into the first real Next.js app, adding `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, updating the wrapper regression harness for the new contract, and syncing the active docs
- Completed TP-004 by adding `tests/start-contract/start-wrapper-windows.ps1`, wiring a `windows-latest` GitHub Actions workflow, syncing verification docs, and extending the Linux regression script to assert the Windows CI path
- Completed TP-003 by scaffolding `src/ATrade.Api`, wiring it into `ATrade.AppHost`, adding bootstrap smoke coverage, and updating the implementation docs
- Reviewed and completed the bootstrap branch in `.worktrees/start-run-bootstrap`
- Verified the Linux-hosted `start run` path, direct AppHost startup, and wrapper regression coverage before handoff

## Verification

- `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
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
