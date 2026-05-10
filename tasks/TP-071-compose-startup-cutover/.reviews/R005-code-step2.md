## Code Review: Step 2 — Make the default AppHost graph dashboard-honest

### Verdict: REVISE

### Summary
The two code changes — flipping `LocalRuntimeContractDefaults.InfrastructureMode` from `AppHostMode` to `ComposeMode` in `LocalRuntimeContract.cs` and adding a diagnostic-fallback comment to the `else` branch in `Program.cs` — are correct and minimal. However, the plan review R004 explicitly flagged that `assert_manifest_declares_infrastructure_graph` in `tests/apphost/apphost-infrastructure-manifest-tests.sh` would break because it runs without `ATRADE_INFRASTRUCTURE_MODE` and relies on the now-changed default. The worker neither fixed the test (the plan review's preferred path) nor documented the expected breakage in STATUS.md (the plan review's alternative path). The test is confirmed broken: it fails on its first assertion `assert_file_contains … '"postgres"'`. This must be resolved before the step can be considered complete.

### Issues Found

1. **[tests/apphost/apphost-infrastructure-manifest-tests.sh:71-103] [critical]** — `assert_manifest_declares_infrastructure_graph` is **broken** because it does not set `ATRADE_INFRASTRUCTURE_MODE` and the C# default has changed to `ComposeMode`. The test expects infra resources (`postgres`, `timescaledb`, `redis`, `nats`) and Aspire-managed connection strings (`"{postgres.connectionString}"`) in the default manifest, but the compose-mode branch produces a manifest containing only `api`, `ibkr-worker`, and `frontend`. The first assertion (`'"postgres"'`) already fails.

   **Proof:** Running `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` outputs:
   ```
   expected /tmp/tmp.y1aUqZ6fWD.json to contain "postgres"
   ```

   **Fix (Plan Review R004 preferred option):** Add `ATRADE_INFRASTRUCTURE_MODE=apphost` before the `dotnet run` command at line 74:
   ```bash
   ATRADE_INFRASTRUCTURE_MODE=apphost \
   ATRADE_POSTGRES_DATA_VOLUME="$manifest_postgres_data_volume" \
     ATRADE_TIMESCALEDB_DATA_VOLUME="$manifest_timescale_data_volume" \
     dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
   ```
   This preserves the test's intent (validating the legacy AppHost-managed infra path), is a one-line change, and keeps the tree green.

   **Alternative:** If deferring to Step 3, at minimum add a note to STATUS.md explicitly acknowledging the expected test breakage and linking it as a Step 3 resolution item. Currently STATUS.md has all Step 2 checkboxes checked with no mention of this breakage.

2. **[tests/apphost/apphost-infrastructure-manifest-tests.sh:78-103] [important]** — The `assert_compose_mode_omits_infrastructure_graph` function at line 108 IS correctly gated (it explicitly sets `ATRADE_INFRASTRUCTURE_MODE=compose`), so the second half of the test suite still passes. Only the first function is broken. This confirms the breakage is isolated to one test function missing an explicit mode override.

### Pattern Violations

- **None.** The code changes follow existing patterns: the `ComposeInfrastructureContract` gating pattern was already established in TP-070, and the constant-flip approach mirrors how other defaults are managed in `LocalRuntimeContractDefaults`.

### Test Gaps

- The broken test (`assert_manifest_declares_infrastructure_graph`) now needs to explicitly opt into the apphost mode to exercise the legacy/diagnostic path. This is the test gap that the plan review R004 predicted and recommended fixing in Step 2.

### Suggestions

- **Comment alignment on the constant:** The plan review suggested adding an inline comment on the default constant explaining its canonical role:
  ```csharp
  // Compose-managed infrastructure is the canonical default.
  // Use ATRADE_INFRASTRUCTURE_MODE=apphost for diagnostic fallback only.
  public const string InfrastructureMode = LocalRuntimeInfrastructureSettings.ComposeMode;
  ```
  The `else` block in `Program.cs` already got a good comment. Adding a similar note on the constant itself would make the intent discoverable without tracing through Program.cs.

- **Note on STATUS.md:** When the test is fixed (either in Step 2 or Step 3), add a Discovery entry noting that `assert_manifest_declares_infrastructure_graph` now explicitly requires `ATRADE_INFRASTRUCTURE_MODE=apphost` to exercise the legacy path.

### Quality Checks

- **Build:** `dotnet build ATrade.slnx` — ✅ passes (0 warnings, 0 errors)
- **.NET Tests:** `dotnet test ATrade.slnx` — ✅ all 223 tests pass (0 failures)
- **Typecheck/Lint/Format:** Not configured in `.pi/taskplane-config.json` or `package.json` — skipped.
- **Shell Tests:** `tests/apphost/apphost-worker-resource-wiring-tests.sh` — ✅ passes. `tests/apphost/apphost-infrastructure-manifest-tests.sh` — ❌ fails on `assert_manifest_declares_infrastructure_graph` (see Issue #1).
