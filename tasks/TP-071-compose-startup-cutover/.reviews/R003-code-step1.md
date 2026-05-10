## Code Review: Step 1 — Flip the default startup contract to Compose-managed infrastructure

### Verdict: APPROVE

### Summary
The R002 REVISE items are all addressed: both `start.run.sh` and `start.run.ps1` now gate Compose invocation on `ATRADE_INFRASTRUCTURE_MODE=compose` (with case-insensitive comparison and sensible `compose`-as-default fallback), and the spurious `frontend/next-env.d.ts` change has been reverted. The implementation correctly delivers all five Step 1 outcomes — `.env.template` defaults flipped, Compose helper invoked before AppHost in both cross-platform scripts, Podman-first command selection preserved, Compose left running (via `up -d` detached mode) after AppHost exits, and wrapper semantics unchanged. Exit code propagation is correct in both scripts (`set -e` in bash, explicit `$LASTEXITCODE` check in PowerShell). One minor empty-string handling inconsistency exists between the bash and PowerShell mode guards, flagged below as a suggestion.

### Issues Found

*None at important or critical severity.*

### Pattern Violations

- **None.** The additions follow the existing patterns: the bash script uses the same `set -euo pipefail` + sourced `local-env.sh` pattern as the baseline; the PowerShell script mirrors the same `$ErrorActionPreference = 'Stop'` + dot-sourced `local-env.ps1` pattern. Mode gating follows the `ComposeInfrastructureContract.IsEnabled` convention from TP-070. Commit messages follow the `feat(TP-071):` / `hydrate:` / `fix(TP-071):` convention.

### Test Gaps

- **Pre-existing (expected in Step 3):** The `start-wrapper-tests.sh` tests (`assert_start_run_script_loads_dashboard_port_contract`, `assert_start_run_dashboard_port_smoke`) call the real `start.run.sh` with a fake `dotnet` but no fake `compose`. With `ATRADE_INFRASTRUCTURE_MODE=compose` default, these tests will either start real Compose containers or fail with a missing-engine error. This is a Step 3 concern (test migration) — the mode guard now allows tests to set `ATRADE_INFRASTRUCTURE_MODE=apphost` in the test `.env` to bypass Compose during AppHost-only tests, or to use `ATRADE_COMPOSE_DRY_RUN=true` for compose-path verification.

### Suggestions

- **Empty-string `ATRADE_INFRASTRUCTURE_MODE` inconsistency (minor):** The bash guard uses `${ATRADE_INFRASTRUCTURE_MODE:-compose}` which replaces only *unset* (not empty) with `compose`, so `ATRADE_INFRASTRUCTURE_MODE=` would skip Compose. The PowerShell guard uses `[string]::IsNullOrWhiteSpace` which treats empty strings as null and falls back to `compose`. This means `export ATRADE_INFRASTRUCTURE_MODE=` followed by `./start run` would:
  - On Unix: skip Compose (correct — user explicitly set empty)
  - On Windows: start Compose (unexpected — user explicitly set empty, but PowerShell treats it as absent)

  In practice this is extremely unlikely — developers set the mode to `compose` or `apphost`, not empty. But for consistency, consider aligning the PowerShell fallback to match bash:
  ```powershell
  $InfraMode = if ($null -eq $env:ATRADE_INFRASTRUCTURE_MODE) { 'compose' } else { $env:ATRADE_INFRASTRUCTURE_MODE }
  ```
  This uses `$null`-only check rather than `IsNullOrWhiteSpace`.

- **Progress messaging before Compose startup:** As noted in R002, the `compose-infra.sh up -d` is silent in the common case but can take significant time on first launch. A brief `printf 'Starting Compose infrastructure…\n'` before the compose call would help developers understand the startup delay. This is low priority but improves DX.

- **Bash exit-code explicit check:** As noted in R002, the bash version relies on `set -e` while PowerShell uses explicit `$LASTEXITCODE` check. Both are correct, but an explicit check would be more robust if `set -e` behavior is ever relaxed:
  ```bash
  if ! "$repo_root/scripts/compose-infra.sh" up; then
    printf 'Compose infrastructure failed to start.\n' >&2
    exit 1
  fi
  ```

### Quality Checks

No typecheck/lint/format-check scripts were found in `.pi/taskplane-config.json` (no `testing.commands` section) or in `frontend/package.json`. Quality checks were not exercised.
