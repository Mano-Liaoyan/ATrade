## Plan Review: Step 1 — Flip the default startup contract to Compose-managed infrastructure

### Verdict: APPROVE

### Summary
The five outcome checkboxes correctly cover the PROMPT Step 1 requirements:
changing `.env.template` defaults, wiring `start.run.sh` / `start.run.ps1` to invoke
Compose before AppHost, preserving Podman-first command selection, leaving Compose
running after AppHost exits, and maintaining cross-platform wrapper semantics. The
foundation from TP-069 (compose-infra helper scripts with `up -d` detached mode) and
TP-070 (ComposeInfrastructureContract with mode gating) makes this a straightforward
wiring step. I have identified two important plan gaps (mode-awareness in the shell
scripts and `.env.template` comment hygiene) and several test-awareness suggestions
the worker should address during implementation.

### Issues Found

1. **[scripts/start.run.sh / start.run.ps1] [important]** — The plan checkboxes say
   "Invoke Compose helper `up` before AppHost" but do not explicitly state that the
   shell scripts must be **mode-aware**: they should conditionally run Compose only
   when `ATRADE_INFRASTRUCTURE_MODE` is `compose`. If the worker unconditionally
   invokes `compose-infra.sh up` before AppHost, then:

   - Anyone who deliberately sets `ATRADE_INFRASTRUCTURE_MODE=apphost` (the legacy
     fallback) would get both Compose AND AppHost competing for ports 5432, 5433,
     6379, 4222.
   - The existing `assert_start_run_script_loads_dashboard_port_contract` and
     `assert_start_run_dashboard_port_smoke` tests in
     `tests/start-contract/start-wrapper-tests.sh` run the real `start.run.sh` with
     a fake `dotnet` binary. After the default flips to `compose`, these tests would
     attempt to start real Compose infrastructure containers — or fail outright if
     no Compose engine is present. (The tests are formally updated in Step 3, but
     Step 1 should produce code that is correct regardless.)

   **Fix:** Add a mode guard in both start scripts, following the pattern the C#
   `ComposeInfrastructureContract.IsEnabled` already uses:

   ```bash
   # In start.run.sh, after atrade_load_local_port_contract:
   infra_mode="${ATRADE_INFRASTRUCTURE_MODE:-apphost}"
   if [ "${infra_mode,,}" = "compose" ]; then
     "$repo_root/scripts/compose-infra.sh" up
   fi
   ```

   ```powershell
   # In start.run.ps1, after Import-ATradeLocalPortContract:
   $InfraMode = if ([string]::IsNullOrWhiteSpace($env:ATRADE_INFRASTRUCTURE_MODE)) {
       'apphost'
   } else {
       $env:ATRADE_INFRASTRUCTURE_MODE
   }
   if ($InfraMode -ieq 'compose') {
       & "$RepoRoot/scripts/compose-infra.ps1" up
   }
   ```

   This keeps the legacy `apphost` path functional and prevents premature Compose
   invocation in tests that are only interested in AppHost behavior.

2. **[.env.template] [important]** — The file contains at least three locations with
   stale commentary that will contradict the new default:

   - **Line ~3 (near `ATRADE_COMPOSE_COMMAND` block):** "The default startup path is
     still Aspire/AppHost; these values are used by scripts/compose-infra.* and
     Compose contract tests until the later cutover task." This sentence references a
     cutover that will have just occurred — it must now describe the post-cutover
     state.
   - **Lines near `ATRADE_INFRASTRUCTURE_MODE`:** "AppHost keeps managing
     infrastructure by default in this staged task. Set to compose to have AppHost
     launch only ATrade app resources while referencing Compose-published localhost
     infrastructure ports." This is the primary target: `compose` is now the default
     and `apphost` is the explicit fallback/diagnostic override.
   - **Top-level doc comment:** Contains phrasing like "The default startup path is
     still Aspire/AppHost" which must be rewritten.

   The plan checkbox "Update defaults for Compose-managed infrastructure with
   Aspire-launched app services" covers the value flip
   (`ATRADE_INFRASTRUCTURE_MODE=compose`), but rewriting the surrounding
   documentation comments is equally important — stale architecture comments are a
   durable source of confusion for developers reading the committed template. The
   worker should audit the entire file for references to AppHost-owned
   infrastructure and update them to reflect Compose ownership.

### Missing Items

- **None.** The five outcome checkboxes cover all PROMPT Step 1 requirements.

### Suggestions

- **Mode value normalization:** Consider using case-insensitive comparison in the
  shell scripts (e.g., `${ATRADE_INFRASTRUCTURE_MODE,,}` in bash or `-ieq` in
  PowerShell) rather than exact string matching, to align with the C#
  `ComposeInfrastructureContract.IsEnabled` behavior (`OrdinalIgnoreCase`). This
  prevents surprising failures when a developer writes
  `ATRADE_INFRASTRUCTURE_MODE=Compose` (capital C) or `ATRADE_INFRASTRUCTURE_MODE=COMPOSE`.

- **Progress messaging:** When the start scripts invoke Compose `up`, emitting a
  brief message like "Starting Compose infrastructure…" helps developers understand
  what's happening during the startup delay. Podman/Docker pull + container start
  can take several seconds on first run, and the existing `compose-infra.sh` does
  not produce output by default (`up -d` is quiet). The `start.run.sh` / `.ps1`
  scripts are the natural place for visibility messages.

- **`LocalRuntimeContractDefaults.InfrastructureMode` constant:** The C# default is
  still `AppHostMode = "apphost"`. While `.env.template` now provides the `compose`
  default in practice (and the C# loader reads `.env.template` first, so the
  constant is rarely reached), changing the C# constant to `ComposeMode` in Step 2
  would be a belt-and-suspenders improvement for edge cases where the template file
  isn't found. The worker should note this for Step 2 rather than expanding Step 1's
  scope.

- **Test awareness (for Steps 3-4):** The `start-wrapper-tests.sh` tests
  `assert_start_run_script_loads_dashboard_port_contract` and
  `assert_start_run_dashboard_port_smoke` run the real `start.run.sh` with a fake
  `dotnet` binary. After Step 1, these tests will need updating. The worker should
  keep a note that Step 3's test migration needs to either:
  - Set `ATRADE_COMPOSE_DRY_RUN=true` or `ATRADE_INFRASTRUCTURE_MODE=apphost` in
    the test's `.env` so Compose is not invoked during AppHost-only dashboard
    tests, or
  - Add dedicated test cases that exercise the Compose-before-AppHost path with
    dry-run or stub Compose binaries.

  This is not a Step 1 concern — it's flagged here so the worker remembers it when
  reaching Step 3.

- **`scripts/compose-infra.sh` / `.ps1` changes:** These are listed as potential
  artifacts ("modified if needed") but should remain untouched unless the worker
  discovers a concrete need. Their current behavior (Podman-first, Docker-fallback,
  `up -d` detached, profile-aware iBeam/LEAN selection) already satisfies all Step 1
  requirements. Unnecessary changes here would create review/rebase friction with
  the TP-069 baseline and risk introducing regressions in the well-tested Compose
  contract.
