## Code Review: Step 1 — Extend the local runtime contract for Compose-managed infrastructure

### Verdict: REVISE

### Summary
The C# implementation is solid: all 6 new variables are properly threaded through constants,
defaults, the `KnownVariableNames` filter, `ResolvePort`/`ResolveComposeProjectName`/`ResolveString`
resolution, and the `LocalRuntimeContract` typed records. Tests are thorough — 14 dotnet tests
pass clean, covering precedence, defaults, secret classification, invalid-port rejection, invalid
project-name rejection, and lane-specific-removal assertions. Two blocking issues remain: (1) the
pre-existing "Intentionally excluded" comment in `.env.template` was flagged in the plan review as
important but was not updated, leaving a direct contradiction with the new port variables; (2) the
shell test assertions added to `local-runtime-contract-module-tests.sh` reference documentation
strings that don't yet exist in `scripts/README.md`, so the shell test will fail until Step 6.

### Issues Found

1. **[.env.template:90-92] [important]** — The "Intentionally excluded from this contract" comment
   block still lists "Service/container target ports such as 5432 (Postgres), 6379 (Redis), and
   4222 (NATS)" as excluded. This directly contradicts the newly added `ATRADE_POSTGRES_PORT=5432`
   (line 29), `ATRADE_REDIS_PORT=6379` (line 31), and `ATRADE_NATS_PORT=4222` (line 32). The plan
   review (R001-plan-step1.md, Issue #1) flagged this explicitly as **important** with the fix:
   "Remove or reword the second bullet." **Fix:** Remove the second bullet entirely or reword it to
   explain that these ports are now part of the Compose host-bind contract (they were previously
   AppHost-internal and excluded, but are now intentionally included).

2. **[tests/apphost/local-runtime-contract-module-tests.sh:140-145] [important]** — The
   `assert_docs_and_existing_tests_share_defaults` function was updated with 6 new
   `assert_file_contains` calls that assert `scripts/README.md` contains documentation for
   `ATRADE_COMPOSE_COMMAND`, `ATRADE_COMPOSE_PROJECT_NAME`, `ATRADE_POSTGRES_PORT`,
   `ATRADE_TIMESCALEDB_PORT`, `ATRADE_REDIS_PORT`, and `ATRADE_NATS_PORT`. However,
   `scripts/README.md` has not been updated yet — it contains zero mentions of any of these
   variables. This means the shell test will fail with a non-zero exit code when run, even though
   the C# code is correct. Since `scripts/README.md` is slated for update in Step 6 (Documentation
   & Delivery), the assertions are premature. **Fix:** Either (a) update `scripts/README.md` with
   the new variable documentation now so the test passes, or (b) defer these 6 `assert_file_contains`
   calls to Step 6 alongside the actual doc update. Option (a) is simpler and avoids forgetting
   them later.

### Pattern Violations
- **None.** The new code follows the existing patterns consistently: `LocalRuntimeComposeSettings`
  is a well-structured typed record, `ResolveComposeProjectName` mirrors the existing
  `ResolveVolumeName` pattern, and error messages match the existing style.

### Test Gaps
- **Minor:** No test exercises the `NormalizeComposeProjectName` edge case of a 129-character
  project name (the validation rejects lengths > 128, but this is untested). Consider adding a
  `[Theory]` with `[InlineData]` for a too-long name, an empty-trimmed-to-default name, and a
  name starting with `_` or `-`.
- **Minor:** `ATRADE_COMPOSE_COMMAND` is the only new variable not tested in the invalid-values
  path. It uses `ResolveString` which accepts any value, so validation isn't expected, but a
  regression test confirming that arbitrary values (including shell metacharacters) are accepted
  would be prudent for a variable that exec's into a child process.

### Suggestions
- **`.env.template` line ordering:** The new Compose section (lines ~23-32) sits between
  `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT` and the AppHost-managed database storage section. Consider
  grouping it after the AppHost section or adding a visual separator so it's clear these are for
  Compose-managed infra, not AppHost-managed.
- **Port zero validation for Compose ports:** All 4 new infra port variables use `allowZero: false`,
  which correctly rejects port `0` and negative values. However, the test only covers `PostgresPort`
  with value `"0"`. Coverage for the other 3 ports' zero rejection is implicitly tested by
  `Load_uses_safe_builtin_defaults` (which exercises the resolve path) but not the explicit-reject
  path. This is a minor gap; the existing coverage is adequate.
- **`scripts/README.md` doc strings:** The specific wording added to the shell test assertions
  (e.g., "optional exact Compose command override; committed default is blank so helper scripts
  auto-select Podman Compose before Docker Compose") is good. When updating `scripts/README.md`,
  reuse these exact strings verbatim to satisfy the assertions.

---

### Quality Check Results

| Command | Result |
|---------|--------|
| `dotnet build ATrade.slnx --nologo --verbosity minimal` | ✅ 0 warnings, 0 errors |
| `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal` | ✅ 14 passed, 0 failed, 0 skipped |
| Shell contract tests (`local-runtime-contract-module-tests.sh`) | ⚠️ Not runnable (no Python3 in PATH at test time), but static analysis confirms `assert_docs_and_existing_tests_share_defaults` would fail due to missing `scripts/README.md` content |
