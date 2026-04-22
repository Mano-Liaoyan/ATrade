---
status: active
owner: devops
updated: 2026-04-23
summary: Live plan for the DevOps role.
see_also:
  - AGENT.md
  - PLAN.md
  - .pi/agents/devops.md
---

# DevOps Current Plan

**Last updated:** 2026-04-23

## Current Focus

Implement the next bootstrap layer now that the repository has a worktree-capable baseline.

## Active Checklist

- [x] ~~Create the first baseline commit for the repository~~
- [x] ~~Bootstrap the `start run` wrapper contract and Linux-hosted AppHost startup path~~
- [x] ~~Verify `./start.ps1 run` and `./start.cmd run` on a Windows host or in CI~~
- [ ] Add Aspire AppHost orchestration for .NET services, Next.js, and infra containers
- [ ] Establish GitHub Actions and labels for autonomous coordination

## Blockers

- None

## Resume From Here

- Windows CI now covers `./start.ps1 run` and `./start.cmd run`; next extend the bootstrap AppHost from the placeholder frontend graph to real .NET services and infrastructure resources

## Recent Progress

- Added a `windows-latest` GitHub Actions workflow plus `tests/start-contract/start-wrapper-windows.ps1` so CI exercises both Windows wrappers and tears down the launched AppHost graph cleanly.
- Added a structural Windows CMD regression test that rejects the parenthesized `if "%COMMAND%"=="run" (...)` flow and requires a label-based `:run` dispatch so `start.cmd` propagates the PowerShell exit code safely without delayed expansion.
- Added a direct AppHost bootstrap regression check that verifies `src/ATrade.AppHost/Properties/launchSettings.json` and proves `dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj` starts under `timeout` without extra shell-exported env vars.
- Removed accidental `ATrade.slnx` from the worktree so the bootstrap stays aligned to `ATrade.sln`.
- Added POSIX `start.run.sh` regression coverage for the documented missing-`dotnet` and missing-AppHost-project failure paths.

## Verification

- `bash tests/start-contract/start-wrapper-tests.sh`
- `dotnet build ATrade.sln`
- `timeout 20s ./start run`
- `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`

## Known Gaps

- None right now.

## References

- `scripts/README.md`
- `PLAN.md`

## Archive

- None yet
