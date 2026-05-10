## Plan Review: Step 4 — Testing & Verification

### Verdict: APPROVE

### Summary
The plan correctly identifies all test suites touched by Steps 1–3 and maps them to the right commands. The STATUS.md outcome checkboxes capture the key verification gates: the two compose-aware manifest/wiring test scripts, the two runtime-contract tests (iBeam & LEAN, marked "if affected"), the ServiceDefaults C# tests, the full dotnet test suite, and the build. The step is an execution gate — it doesn't need an elaborate implementation plan, just a clear list of what must pass.

### Issues Found
*None.* No blocking issues.

### Coverage Assessment

| Test suite | Why it matters | Listed? |
|---|---|---|
| `apphost-infrastructure-manifest-tests.sh` | Contains new `assert_compose_mode_omits_infrastructure_graph` — the core compose-mode manifest test | ✅ PROMPT.md + STATUS.md |
| `apphost-worker-resource-wiring-tests.sh` | Contains new `assert_compose_mode_wires_external_infrastructure_without_secret_values` — compose-mode wiring + secret-safety | ✅ PROMPT.md + STATUS.md |
| `ibeam-runtime-contract-tests.sh` | Tests default-mode iBeam manifest contract; should be unaffected since compose-mode doesn't change the non-compose branch | ✅ "if affected" |
| `lean-aspire-runtime-tests.sh` | Tests default-mode LEAN manifest contract; similarly unaffected | ✅ "if affected" |
| `ATrade.ServiceDefaults.Tests` | C# unit tests for `LocalRuntimeContractLoader`, covering infrastructure mode validation and secret classification | ✅ PROMPT.md + STATUS.md |
| `dotnet test ATrade.slnx` | Full C# test suite catch-all | ✅ PROMPT.md + STATUS.md |
| `dotnet build ATrade.slnx` | Compilation gate | ✅ PROMPT.md + STATUS.md |

### Observation on "if affected" tests

The `ibeam-runtime-contract-tests.sh` and `lean-aspire-runtime-tests.sh` tests both use their own `publish_manifest` / `publish_manifest_with_lean_*` helpers that do NOT set `ATRADE_INFRASTRUCTURE_MODE`. Since `Program.cs` only alters infrastructure container behavior when `composeInfrastructureContract.IsEnabled` is true, and these tests exercise the default path, they should pass unchanged. The "if affected" qualifier in STATUS.md is appropriate — the worker should verify these pass, but if they don't, the failure is diagnostic and should be investigated rather than dismissed.

### Suggestions

- **[minor] Consider running `tests/compose/compose-infra-contract-tests.sh`** as an additional sanity check. TP-070 added infrastructure-mode and port variables to `.env.template` that overlap with the Compose contract. The compose test explicitly verifies `.env.template` values for `ATRADE_POSTGRES_PORT`, `ATRADE_TIMESCALEDB_PORT`, `ATRADE_REDIS_PORT`, and `ATRADE_NATS_PORT` (all present in the compose test's `expected` map), plus it checks that no real-looking account IDs or secret sentinels leak into committed files. Running this test would catch accidental `.env.template` corruption without adding a new outcome checkbox.

- **[minor] Consider running `tests/apphost/local-runtime-contract-module-tests.sh`** — this test verifies `.env.template` defaults (which TP-070 extended with `ATRADE_INFRASTRUCTURE_MODE=apphost` and infrastructure port values). While the test doesn't explicitly check for the new `ATRADE_INFRASTRUCTURE_MODE` key, it does enforce that no forbidden lane-specific defaults (like port `15432`) reappear in the template, and it validates documentation consistency. This is a lighter-weight guard than the compose test but covers the `.env.template` surface from a different angle.

- **[minor] Python3 dependency awareness.** The `lean-aspire-runtime-tests.sh` and `ibeam-runtime-contract-tests.sh` use `python3` for `pick_free_port()` and inline manifest-parsing scripts, unlike the manifest/wiring tests which migrated to `node`. This pre-dates TP-070 and is not a blocking issue, but if `python3` is unavailable the worker should log it as a diagnostic rather than treat it as a regression from this task.

- **[minor] STATUS.md checkbox alignment.** The STATUS.md checkboxes use descriptive names ("AppHost manifest validation passing") while PROMPT.md lists exact shell commands. Consider adding a brief mapping comment in STATUS.md Notes so the execution trace is unambiguous about which command backs each checkbox — this helps future reviewers understand what was actually run.
