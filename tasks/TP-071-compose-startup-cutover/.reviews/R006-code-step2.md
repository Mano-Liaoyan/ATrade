## Code Review: Step 2 — Make the default AppHost graph dashboard-honest

### Verdict: APPROVE

### Summary
The R005 REVISE issue (broken `assert_manifest_declares_infrastructure_graph` test) is now fully resolved: the test correctly sets `ATRADE_INFRASTRUCTURE_MODE=apphost` to explicitly validate the legacy/diagnostic path. Both AppHost C# changes (the constant-flip and the `else`-block comment) remain correct and minimal. All shell tests and all 255 .NET tests pass with zero failures. The four PROMPT Step 2 requirements are met — Compose is the default, the dashboard is honest (only app services appear), connection strings are secret-safe, and the legacy fallback is documented as diagnostic-only.

### Issues Found

*None.* All findings from R005 have been addressed.

### Pattern Violations

- **None.** The code follows existing patterns: `ComposeInfrastructureContract.IsEnabled` gating, `LocalRuntimeContractDefaults` constant management, and comment conventions.

### Test Gaps

- **None.** `assert_manifest_declares_infrastructure_graph` (apphost mode) and `assert_compose_mode_omits_infrastructure_graph` (compose mode) together provide thorough dual-mode manifest coverage.

### Suggestions

- **Discovery documentation:** Consider adding a Discovery entry in STATUS.md noting that `assert_manifest_declares_infrastructure_graph` now explicitly requires `ATRADE_INFRASTRUCTURE_MODE=apphost` to exercise the legacy path — this captures the mode-awareness design intent for future test authors.

- **Worker wiring test is fine:** The `apphost-worker-resource-wiring-tests.sh` `publish_apphost_manifest` helper already defaults `infrastructure_mode` to `apphost` via `${7:-apphost}`, so it was never affected by the default flip. No changes needed here.

### Quality Checks

- **Build:** `dotnet build ATrade.slnx` — ✅ passes (0 warnings, 0 errors)
- **.NET Tests:** `dotnet test ATrade.slnx` — ✅ all 255 tests pass (0 failures, 0 skipped)
- **Shell — manifest tests:** `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` — ✅ passes
- **Shell — worker wiring tests:** `bash tests/apphost/apphost-worker-resource-wiring-tests.sh` — ✅ passes
- **Typecheck/Lint/Format:** Not configured in `.pi/taskplane-config.json` or `package.json` — skipped.
