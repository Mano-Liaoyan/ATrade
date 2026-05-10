## Plan Review: Step 2 — Make the default AppHost graph dashboard-honest

### Verdict: APPROVE

### Summary
The four outcome checkboxes correctly cover the PROMPT Step 2 requirements:
flipping the AppHost default from `apphost` to `compose` infrastructure mode,
ensuring the resulting dashboard/manifest is honest (infra containers absent,
app services present), preserving secret-safe connection string handoff, and
documenting the legacy fallback path. The foundation from TP-070 (the compose-mode
`if` branch already in Program.cs) means no new graph-wiring code is needed —
this step is effectively a one-constant change plus documentation. One important
test-awareness gap exists: the `assert_manifest_declares_infrastructure_graph`
test will break on the default flip because it doesn't explicitly set the
infrastructure mode. The worker should either fix it inline in Step 2 or
explicitly accept the breakage for Step 3 resolution.

### Issues Found

1. **[tests/apphost/apphost-infrastructure-manifest-tests.sh:78-80] [important]** —
   `assert_manifest_declares_infrastructure_graph` does **not** set
   `ATRADE_INFRASTRUCTURE_MODE` — it runs `dotnet run --project … --publisher
   manifest` relying on the built-in default. After the C# constant changes
   from `AppHostMode` to `ComposeMode`, this test will fail because the default
   manifest will no longer contain `"postgres"`, `"timescaledb"`, `"redis"`,
   `"nats"`, image references, or `"{postgres.connectionString}"` references.
   Every assertion from line 78 through ~105 will fail.

   **Fix:** The plan should acknowledge this breakage and choose a strategy:
   - **Preferred:** Fix in Step 2 — add `ATRADE_INFRASTRUCTURE_MODE=apphost`
     before the `dotnet run` command in `assert_manifest_declares_infrastructure_graph`,
     keeping Step 2 self-contained and green. This is a one-line change that
     restores the intent of the test (explicitly validating the AppHost-managed
     legacy path).
   - **Alternative:** Note in the Step 2 STATUS checkboxes that this test is
     expected to break and will be addressed in Step 3's test migration. Less
     clean because it leaves the tree with a known test failure between steps.

   (Note: `assert_manifest_wires_worker_and_application_resources` in
   `apphost-worker-resource-wiring-tests.sh` is **not** affected — it uses the
   `publish_apphost_manifest` helper which defaults `infrastructure_mode`
   to `apphost` via parameter default `"${7:-apphost}"`.)

2. **[src/ATrade.ServiceDefaults/LocalRuntimeContract.cs:163] [minor]** —
   The core code change (changing `LocalRuntimeContractDefaults.InfrastructureMode`
   from `AppHostMode` to `ComposeMode`) lives in
   `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs`, which is listed in the
   task's Context to Read but not explicitly in Step 2's artifact list. The
   "AppHost helper files (modified if needed)" catch-all covers it, but the
   worker should note this file as the primary change target to avoid starting
   implementation in the wrong file.

### Missing Items

- **None.** The four outcome checkboxes cover all PROMPT Step 2 requirements.
  The C# constant flip, documentation of the else branch, and verification of
  secret-safe handoff are all addressed or implied.

### Suggestions

- **Comment the else block in Program.cs:** Add a documentation comment above
  the `else` block (line ~81 in current Program.cs) clearly marking it as the
  legacy/diagnostic fallback path:

  ```csharp
  // Legacy AppHost-managed infrastructure fallback.
  // Only active when ATRADE_INFRASTRUCTURE_MODE=apphost (not the default).
  // Retained for temporary diagnostic runs where Aspire should create
  // infrastructure containers. Not part of the normal ./start run path.
  ```

  This satisfies the "document it as diagnostic/temporary only" requirement.

- **Comment the default constant:** When changing
  `LocalRuntimeContractDefaults.InfrastructureMode` to `ComposeMode`, add an
  inline comment explaining the role:

  ```csharp
  // Compose-managed infrastructure is the canonical default.
  // Use ATRADE_INFRASTRUCTURE_MODE=apphost for diagnostic fallback only.
  public const string InfrastructureMode = LocalRuntimeInfrastructureSettings.ComposeMode;
  ```

- **.env.template already documents `ATRADE_INFRASTRUCTURE_MODE` well** (updated
  in Step 1). No additional `.env.template` changes are needed for Step 2.

- **`IsComposeManaged` on `LocalRuntimeInfrastructureSettings`:** The property
  exists but is unused in production code (only `ComposeInfrastructureContract.IsEnabled`
  gates the Program.cs branch). No action needed — it's a downstream convenience
  if callers want to query the mode without a secondary contract load.

- **Consider explicit apphost-mode AppHost test in Step 2 instead of deferring:**
  Adding `ATRADE_INFRASTRUCTURE_MODE=apphost` to
  `assert_manifest_declares_infrastructure_graph` is trivial and keeps the tree
  green. Deferring to Step 3 adds unnecessary risk of the worker forgetting to
  fix it and discovering the failure only at Step 6's full-suite run.
