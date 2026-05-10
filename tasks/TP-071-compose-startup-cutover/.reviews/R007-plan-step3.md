## Plan Review: Step 3 — Migrate startup and AppHost validation

### Verdict: APPROVE

### Summary
The four outcome checkboxes correctly cover the PROMPT Step 3 requirements:
updating start-wrapper tests for the Compose-before-AppHost startup order,
updating AppHost manifest/resource-wiring tests to expect no infra containers by
default, updating iBeam/LEAN tests for Compose profile ownership, and keeping
Windows wrapper validation aligned. The foundation from Steps 1–2 (mode-gated
`start.run.sh` / `.ps1`, compose-mode `if` branch in `Program.cs`, and flipped
C# default constant) sets up the test migration. I have identified three
important plan-level gaps the worker should address during implementation.

### Issues Found

1. **[tests/apphost/apphost-infrastructure-manifest-tests.sh:78] [important]** —
   **Deferred fix not acknowledged.** The R005 code review for Step 2 deferred
   fixing `assert_manifest_declares_infrastructure_graph` to Step 3, noting it
   is **broken** because it doesn't set `ATRADE_INFRASTRUCTURE_MODE` and the
   C# default has changed to `compose`. Every assertion from line 78 through
   ~105 will fail. The current plan checkbox "Update AppHost manifest/resource
   tests for no default infra resources" covers the intent but doesn't
   explicitly call out this needed one-line fix. The worker should add
   `ATRADE_INFRASTRUCTURE_MODE=apphost` before the `dotnet run` at line 74 to
   restore the legacy AppHost-managed path intent while the compose-mode
   assertions in `assert_compose_mode_omits_infrastructure_graph` (line 108,
   which already explicitly sets `ATRADE_INFRASTRUCTURE_MODE=compose`) now
   represent the **default** behavior.

   **Fix:** One-line env addition:
   ```bash
   ATRADE_INFRASTRUCTURE_MODE=apphost \
   ATRADE_POSTGRES_DATA_VOLUME="$manifest_postgres_data_volume" \
   ```

2. **[tests/apphost/ibeam-runtime-contract-tests.sh + lean-aspire-runtime-tests.sh] [important]** —
   **iBeam/LEAN tests will break** because they expect `ibkr-gateway` and
   `lean-engine` container resources in the default AppHost manifest, but
   with the compose-mode default these containers are now Compose profile
   responsibilities and are wired only in the `else` (apphost-mode) branch
   of `Program.cs`. Specifically:

   - **ibeam-runtime-contract-tests.sh** — `publish_manifest` (line ~30)
     does not set `ATRADE_INFRASTRUCTURE_MODE`. After the default flip,
     `ibkr-gateway` will never appear in the manifest, even when integration
     is enabled. `assert_apphost_ibeam_manifest_contract` (line ~130) will
     fail on its enabled-manifest assertions (lines ~158–195). The test needs
     to split into:
     - Legacy apphost-mode variant (`ATRADE_INFRASTRUCTURE_MODE=apphost`) that
       preserves the existing `ibkr-gateway` container assertions.
     - Default compose-mode variant that verifies `ibkr-gateway` is absent but
       `ATRADE_IBKR_GATEWAY_URL`, `ATRADE_IBKR_GATEWAY_PORT`, etc. are still
       correctly handed off to `api` and `ibkr-worker` env vars.

   - **lean-aspire-runtime-tests.sh** — `publish_manifest_with_lean_docker_enabled`
     (line ~96) does not set `ATRADE_INFRASTRUCTURE_MODE`. After the default
     flip, `lean-engine` will never appear. `assert_lean_docker_manifest_declares_dashboard_resource_mount_and_api_handoff`
     (line ~230) will fail. Same split strategy: preserve the legacy assertion
     under explicit `apphost` mode, add a compose-mode variant that verifies
     `lean-engine` is absent but LEAN env vars (`ATRADE_LEAN_*`) are correctly
     handed off to `api`.

   **Risk:** If the worker only adds `ATRADE_INFRASTRUCTURE_MODE=apphost`
   everywhere, the tests remain green but lose coverage of the default
   compose-mode code path. The default path MUST be tested — it's the primary
   runtime contract going forward. Each affected test function should have
   **both** an apphost-mode legacy assertion and a compose-mode default
   assertion, mirroring the pattern already established in
   `apphost-infrastructure-manifest-tests.sh` (which has paired
   `assert_manifest_declares_infrastructure_graph` and
   `assert_compose_mode_omits_infrastructure_graph` functions) and in
   `apphost-worker-resource-wiring-tests.sh` (which has paired
   `assert_manifest_wires_worker_and_application_resources` and
   `assert_compose_mode_wires_external_infrastructure_without_secret_values`).

3. **[tests/start-contract/start-wrapper-tests.sh] [important]** —
   **Existing tests will invoke real Compose.** The functions
   `assert_start_run_script_loads_dashboard_port_contract` (line ~235) and
   `assert_start_run_dashboard_port_smoke` (line ~275) call the real
   `start.run.sh` with a fake `dotnet` binary but no fake `compose` binary.
   After Steps 1–2, `start.run.sh` invokes `compose-infra.sh up` when
   `ATRADE_INFRASTRUCTURE_MODE=compose` (the default). These tests will either
   start real Compose containers (polluting the test environment) or fail with
   "ATrade Compose infrastructure requires Podman Compose or Docker Compose"
   when no engine is available.

   The worker needs to choose a strategy:
   - **Option A:** In the existing AppHost-only tests, set
     `ATRADE_INFRASTRUCTURE_MODE=apphost` in the test's `.env` to bypass
     Compose. This is the simplest approach and preserves the existing
     test intent (verifying AppHost dashboard port contract and smoke).
   - **Option B:** Set `ATRADE_COMPOSE_DRY_RUN=true` in the test environment,
     allowing `compose-infra.sh` to run its command-selection logic and print
     the resolved command without executing it. This verifies Compose
     integration without starting real containers.
   - **Complement:** Add **new** test functions that explicitly exercise the
     Compose-before-AppHost path using dry-run or stub binaries to verify
     Podman-first selection, `ATRADE_COMPOSE_COMMAND` honoring, and that
     Compose is invoked before AppHost.

   **Recommendation:** Use Option A for existing AppHost-only smoke tests
   (they test AppHost behavior, not Compose behavior), and add new dedicated
   Compose-contract test functions (possibly in a new test section or file)
   that exercise the `start run` → Compose integration using dry-run mode
   or stubs.

### Missing Items

- **None.** The four outcome checkboxes cover all PROMPT Step 3 requirements.
  The concerns above are implementation strategy gaps, not missing outcomes.

### Suggestions

- **Worker resource wiring test default-path coverage:** The
  `publish_apphost_manifest` helper in `apphost-worker-resource-wiring-tests.sh`
  defaults `infrastructure_mode` to `apphost` via parameter default
  `"${7:-apphost}"`, so `assert_manifest_wires_worker_and_application_resources`
  currently tests only the legacy path. After Step 2 flipped the default to
  `compose`, this function is no longer testing the default. Consider changing
  the parameter default to empty string (so the C# default applies organically)
  and then having `assert_manifest_wires_worker_and_application_resources`
  either accept the new compose-mode result or split into explicit
  apphost/compose variants. (This is a refinement — the existing
  `assert_compose_mode_wires_external_infrastructure_without_secret_values`
  function already covers the compose path, so the coverage gap is minimal.)

- **Windows test — Compose engine availability:** `start-wrapper-windows.ps1`
  runs `./start.ps1 run` and `./start.cmd run` which now invoke Compose.
  Windows CI (`windows-start-run.yml`) may not have Podman or Docker Compose
  available. The test should either set `ATRADE_INFRASTRUCTURE_MODE=apphost`
  to bypass Compose, or the worker should verify the CI environment has a
  compatible Compose engine. Given that the Windows CI job was originally
  designed to verify the `start run` wrapper contract (not runtime
  infrastructure), `ATRADE_INFRASTRUCTURE_MODE=apphost` is the appropriate
  choice for this test.

- **Volume test awareness (look-ahead for Step 4):**
