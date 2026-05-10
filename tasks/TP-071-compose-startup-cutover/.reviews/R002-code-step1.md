## Code Review: Step 1 — Flip the default startup contract to Compose-managed infrastructure

### Verdict: REVISE

### Summary
The implementation delivers the three core outcomes — `.env.template` defaults flipped to `ATRADE_INFRASTRUCTURE_MODE=compose`, Compose helper invoked before AppHost in both Unix and PowerShell start scripts, and Compose left running via `up -d` detached mode after AppHost exits. However, the plan reviewer (R001) flagged two important issues: **mode-awareness in the start scripts** and **`.env.template` comment hygiene**. The worker addressed the comment updates but skipped the mode guard entirely — the start scripts invoke `compose-infra.sh up` unconditionally, disregarding the `ATRADE_INFRASTRUCTURE_MODE` value. This creates a concrete port-conflict bug when a developer deliberately switches to the documented `apphost` diagnostic fallback, and causes existing start-wrapper tests to attempt real Compose container launches (or fail when no Compose engine is present). Additionally, an unrelated `next-env.d.ts` auto-generated change was committed alongside the task changes.

### Issues Found

1. **[scripts/start.run.sh:26 / scripts/start.run.ps1:28] [important]** — Mode-awareness gap: both start scripts invoke the Compose helper unconditionally without checking `ATRADE_INFRASTRUCTURE_MODE`.

   **Why this matters:**
   - `.env.template` now documents `ATRADE_INFRASTRUCTURE_MODE=compose` as the default, but explicitly states: _"Set apphost only for temporary diagnostic fallback runs where Aspire should create infrastructure containers."_ If a developer follows this instruction to switch to `apphost` mode, the start script still fires up Compose-managed postgres/timescaledb/redis/nats on ports 5432/5433/6379/4222. When Aspire then attempts to create its own copies of those containers, it will hit port conflicts and fail.
   - The existing `start-wrapper-tests.sh` tests create a fake `dotnet` binary but do NOT create a fake `compose` binary. With `ATRADE_INFRASTRUCTURE_MODE=compose` loaded from `.env.template`, calling `compose-infra.sh up` will either start real containers (unwanted/test-polluting) or fail with "ATrade Compose infrastructure requires Podman Compose or Docker Compose" when no engine is present.
   - The C# `ComposeInfrastructureContract.IsEnabled` already uses `ATRADE_INFRASTRUCTURE_MODE` to gate behavior — the shell scripts should mirror this for consistency.

   **Fix:** Add a mode guard immediately after loading the local port contract, before the Compose invocation:

   **start.run.sh** (after `atrade_load_local_port_contract "$repo_root"`, before the compose call):
   ```bash
   infra_mode="${ATRADE_INFRASTRUCTURE_MODE:-compose}"
   if [ "${infra_mode,,}" = "compose" ]; then
     "$repo_root/scripts/compose-infra.sh" up
   fi
   ```

   **start.run.ps1** (after `Import-ATradeLocalPortContract -RepoRoot $RepoRoot`, before the compose call):
   ```powershell
   $InfraMode = if ([string]::IsNullOrWhiteSpace($env:ATRADE_INFRASTRUCTURE_MODE)) {
       'compose'
   } else {
       $env:ATRADE_INFRASTRUCTURE_MODE
   }
   if ($InfraMode -ieq 'compose') {
       & (Join-Path $RepoRoot 'scripts/compose-infra.ps1') up
       if ($LASTEXITCODE -ne 0) {
           exit $LASTEXITCODE
       }
   }
   ```

   Note the `-ieq` (case-insensitive) to align with the C# `ComposeInfrastructureContract.IsEnabled` which uses `StringComparison.OrdinalIgnoreCase`.

2. **[frontend/next-env.d.ts:3] [minor]** — Spurious auto-generated file change: the import path changed from `"./.next/types/routes.d.ts"` to `"./.next/dev/types/routes.d.ts"`. This is a Next.js auto-generated file (note the "This file should not be edited" comment at line 5) that likely changed because `npm run dev` was run in the frontend directory during development. This change is unrelated to the Compose startup cutover and should be reverted to keep the commit focused.

   **Fix:** Revert the file to the baseline content:
   ```diff
   -import "./.next/dev/types/routes.d.ts";
   +import "./.next/types/routes.d.ts";
   ```

### Pattern Violations

- **None.** The implementation follows the established patterns from TP-069 (compose-infra helpers) and TP-070 (mode gating). The `.env.template` comment updates are clear and correctly describe the post-cutover state. The `set -euo pipefail` in `start.run.sh` and explicit `$LASTEXITCODE` check in `start.run.ps1` properly handle compose failure propagation.

### Test Gaps

- **Pre-existing tests now broken:** The `assert_start_run_script_loads_dashboard_port_contract` and `assert_start_run_dashboard_port_smoke` tests in `tests/start-contract/start-wrapper-tests.sh` call the real `start.run.sh` with a fake `dotnet` binary but no fake `compose` binary. After this Step 1 change, these tests will attempt to run real Compose infrastructure or fail with a missing-engine error. This is expected to be addressed in Step 3 (test migration), but the mode guard suggested above would also allow tests to set `ATRADE_INFRASTRUCTURE_MODE=apphost` to bypass Compose during AppHost-only tests.

### Suggestions

- **Progress messaging before Compose startup:** The `compose-infra.sh up -d` is silent in the common case (containers already running) but can take significant time on first launch (image pulls). Consider adding a brief user-facing message before the compose call:
  ```bash
  printf 'Starting Compose infrastructure…\n'
  ```
  This helps developers understand what's happening during the startup delay and differentiates Compose startup time from AppHost startup time.

- **Consider `ATRADE_COMPOSE_DRY_RUN=true` for tests:** The `compose-infra.sh` already supports dry-run mode. When Step 3 updates the start-wrapper tests, the test environment could set `ATRADE_COMPOSE_DRY_RUN=true` instead of needing a mode switch, allowing tests to verify the correct compose command would be invoked without actually starting containers.

- **`start.run.sh` exit-code handling asymmetry:** The PowerShell version explicitly checks `$LASTEXITCODE` after the compose call, while the bash version relies on `set -e` to catch non-zero exits from `compose-infra.sh`. Both are correct, but the bash version is marginally less explicit. If the `set -e` behavior is ever relaxed, the compose failure could be missed. Consider adding an explicit check for consistency:
  ```bash
  if ! "$repo_root/scripts/compose-infra.sh" up; then
    printf 'Compose infrastructure failed to start.\n' >&2
    exit 1
  fi
  ```

### Summary of Required Changes (for REVISE resolution)

1. Add `ATRADE_INFRASTRUCTURE_MODE` guard in `scripts/start.run.sh` (before compose invocation)
2. Add `ATRADE_INFRASTRUCTURE_MODE` guard in `scripts/start.run.ps1` (before compose invocation)
3. Revert `frontend/next-env.d.ts` to baseline state

### Quality Checks

No typecheck/lint/format-check scripts were found in `.pi/taskplane-config.json` (no `testing.commands` section) or in `frontend/package.json`. Quality checks were not exercised.
