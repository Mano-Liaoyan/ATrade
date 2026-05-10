## Code Review: Step 1 — Extend the local runtime contract for Compose-managed infrastructure

### Verdict: APPROVE

### Summary
The two R002 blocking issues have been addressed: the `.env.template` "Intentionally excluded" comment now correctly explains that Compose host-bind ports are included (not excluded), and `scripts/README.md` has the new Compose variable documentation matching the shell test assertions verbatim. All 14 dotnet tests pass with 0 failures, the build produces 0 warnings/0 errors, and the implementation correctly threads all 6 new variables through the full contract pipeline (constants → defaults → KnownVariableNames → resolution → typed records → tests). Precedence semantics, secret classification, port validation, and project-name validation are all correct.

### Issues Found

*None blocking.* Both R002 issues have been resolved:

1. **[Fixed — R002 #1]** `.env.template:90-95` — The "Intentionally excluded" comment now reads:
   > AppHost-internal service target ports that Aspire continues to manage outside this Compose host-bind foundation. Compose-managed localhost bind ports for Postgres, TimescaleDB, Redis, and NATS are intentionally included above.
   
   This correctly distinguishes Aspire-internal ports (still excluded) from the new Compose host-bind ports (intentionally included). ✅

2. **[Fixed — R002 #2]** `scripts/README.md:130-142` — The "Compose-managed infrastructure foundation variables" section has been added with all 6 variables documented. The doc strings match the shell test assertions in `tests/apphost/local-runtime-contract-module-tests.sh` (verified by line-by-line comparison). ✅

### Pattern Violations

- **None.** The new code follows the existing patterns consistently: `LocalRuntimeComposeSettings` is a well-structured typed record, `ResolveComposeProjectName` mirrors the existing `ResolveVolumeName` pattern, and error messages match the existing style.

### Test Gaps

- **Minor (carried from R002):** No `[Theory]` coverage for `NormalizeComposeProjectName` edge cases: 129-character name (length > 128), name starting with `_` or `-`, empty string trimmed to default. The current test covers `"Bad.Project"` (capital letter + period) which validates the core validation logic, but coverage of the boundary conditions would strengthen the suite.
- **Minor (carried from R002):** `ATRADE_COMPOSE_COMMAND` uses `ResolveString` (accepts any value including shell metacharacters). No test verifies that the empty-string default passes through correctly when the variable is omitted from all layers. The `Load_uses_safe_builtin_defaults` test covers this implicitly via `Assert.Equal(LocalRuntimeContractDefaults.ComposeCommand, contract.Compose.Command)`, so the gap is minor and unlikely to surface a regression.

### Suggestions

- **Project-name validation edge cases:** Add `[Theory]` with `[InlineData]` for: a 129-character project name (should reject), an empty/whitespace name (should fall back to default), and a name starting with `_` or `-` (should reject). This would be a fast, low-risk addition.
- **`.env.template` section grouping:** The new Compose variables (lines 23-32) sit between Aspire dashboard and AppHost database storage. A visual comment separator (e.g., `# --- Compose infrastructure (not used by Aspire) ---`) would clarify the ownership boundary for future readers. Not blocking.
- **Shell tests could not be run:** Python3 is not available in the review environment (Windows Store stub only). Static analysis confirms the `assert_docs_and_existing_tests_share_defaults` assertions in `local-runtime-contract-module-tests.sh` would pass against the current `scripts/README.md` content, but a live run in an environment with Python3 should be done in Step 5 (Testing & Verification).

---

### Quality Check Results

| Command | Result |
|---------|--------|
| `dotnet build ATrade.slnx --nologo --verbosity minimal` | ✅ 0 warnings, 0 errors |
| `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal` | ✅ 14 passed, 0 failed, 0 skipped |
| Shell contract tests (`local-runtime-contract-module-tests.sh`) | ⚠️ Not runnable (Python3 not available), static analysis confirms assertions match current file contents |
| Shell contract tests (`paper-trading-config-contract-tests.sh`) | ⚠️ Not runnable (Python3 not available), static analysis confirms required dict includes all 6 new variables |
