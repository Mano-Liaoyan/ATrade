## Plan Review: Step 5 — Testing & Verification

### Verdict: APPROVE

### Summary
The plan faithfully translates the PROMPT.md Step 5 requirements into actionable, outcome-level checkboxes: the new Compose contract tests, the modified .NET runtime contract tests, the two affected shell contract test scripts, the full .NET regression suite, a failure-fix mandate, and a final build gate. Every test command listed in PROMPT.md is accounted for, and the ZERO-failures requirement is covered by the explicit "Fix all failures" checkbox. The plan is appropriately thin for a Testing & Verification step — its job is to execute the pre-existing test suite, not to design new tests (that was Step 4's job).

### Issues Found
*None that would block progress.*

### Missing Items
*None.* All PROMPT.md Step 5 bullet points are represented in the STATUS.md checkboxes.

### Suggestions
- **Build-first ordering:** The `dotnet build ATrade.slnx` checkbox appears at the end of the plan, but logically a build should come before test execution. While `dotnet test` performs an implicit build, an explicit `dotnet build` first gives faster feedback on compilation errors (seconds vs. minutes). Consider reordering so the build is the first verification step, or simply noting that the worker should build before testing.

- **"If affected" is already determined:** The apphost local runtime and paper-trading shell contract tests are marked "if affected" — but they are **definitely affected**. Both scripts (`local-runtime-contract-module-tests.sh`, `paper-trading-config-contract-tests.sh`) were updated in Step 1 to include Compose variable assertions (the new `ATRADE_COMPOSE_*`, `ATRADE_POSTGRES_PORT`, `ATRADE_TIMESCALEDB_PORT`, `ATRADE_REDIS_PORT`, `ATRADE_NATS_PORT` keys are in their expected-defaults dictionaries). The worker should treat these as mandatory runs, not optional.

- **Pre-existing failure triage:** The "Fix all failures" checkbox doesn't distinguish between failures introduced by TP-069 and pre-existing failures in the broader test suite. If the full `dotnet test ATrade.slnx` uncovers a failure in an unrelated test project (e.g., `ATrade.Backtesting.Tests` for a pre-existing regression), fixing it would be scope creep. The worker should:
  1. First run the TP-069-targeted tests (compose contract, runtime contract, apphost shell tests) — fix any failures here regardless.
  2. Run the full suite — if a failure appears in a test project that was not touched by TP-069, log it as a Discovery in STATUS.md rather than attempting to fix it.
  3. Only failures in TP-069-touched code paths require fixes.

- **Start-wrapper contract tests:** The `tests/start-contract/start-wrapper-tests.sh` script references `.env.template` (specifically `ATRADE_APPHOST_FRONTEND_HTTP_PORT` and `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT`) and is cross-referenced by the apphost runtime contract tests. While not listed in PROMPT.md Step 5, it would be a prudent additional verification to ensure the `.env.template` changes didn't break start-wrapper contract assertions — consider running it as a "check if affected" candidate if time permits.

- **Quality checks:** The project has no typecheck/lint/format-check commands configured (confirmed in R005, R007, R009 reviews). This is not a gap for TP-069 — it reflects the project's current state — and the plan correctly omits quality-check steps.

- **Live Compose config check:** The new `tests/compose/compose-infra-contract-tests.sh` includes `assert_optional_live_compose_config_skips_or_passes` which gates on `podman compose version` or `docker compose version`. If neither is available on the test machine, this check will print SKIP and return 0 (success). The worker should note in the execution log whether live Compose config validation was skipped or exercised.
