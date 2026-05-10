## Code Review: Step 3 — Add opt-in manifest and wiring tests

### Verdict: APPROVE

### Summary
Both test files are correctly updated to validate Compose-mode manifest generation. `apphost-infrastructure-manifest-tests.sh` adds `assert_compose_mode_omits_infrastructure_graph`, which generates a compose-mode manifest and asserts all six infra container resources (postgres, timescaledb, redis, nats, ibkr-gateway, lean-engine) are absent, app resources (api, ibkr-worker, frontend) are present with correct types, and connection strings use the direct `Host=127.0.0.1;Port=…;Password={paramName.value}` form. `apphost-worker-resource-wiring-tests.sh` adds `assert_compose_mode_wires_external_infrastructure_without_secret_values`, which extends coverage to secret-safety assertions — passing real-looking password values through env vars and confirming they never appear in the manifest JSON. The `publish_apphost_manifest` helper is cleanly extended with an optional `infrastructure_mode` parameter, and existing AppHost-managed test assertions are preserved unchanged. Build passes with 0 errors / 0 warnings. All four STATUS.md outcomes for Step 3 are satisfied.

### Issues Found
*None.* No blocking issues.

### Pattern Violations
*None.* The test code follows existing project conventions:
- Inline Node.js scripts use `process.argv[2]` or `process.argv.slice(2)` consistently
- Error messages include the resource/env key name and both expected/found values
- `set -euo pipefail` is preserved; cleanup uses trap EXIT
- The `publish_apphost_manifest` parameter extension uses the same default-value pattern as the existing `gateway_url`/`gateway_port` defaults

### Port-Contract Consistency
The compose-mode test values are consistent with the actual `ComposeInfrastructureContract`:

| Env Var | Test Value | `BuildXxxConnectionString` Output |
|---|---|---|
| `ATRADE_POSTGRES_PORT=15432` | `Host=127.0.0.1;Port=15432;…;Password={postgres-password.value};…` | ✅ |
| `ATRADE_TIMESCALEDB_PORT=15433` | `Host=127.0.0.1;Port=15433;…;Password={timescaledb-password.value};…` | ✅ |
| `ATRADE_REDIS_PORT=16379` | `127.0.0.1:16379` | ✅ |
| `ATRADE_NATS_PORT=14222` | `nats://127.0.0.1:14222` | ✅ |

### Plan Review Follow-up

The R005 plan review made four suggestions and carried forward two from R004. Here is the disposition of each:

1. **[plan suggestion, not addressed] — Assert POSTGRES_HOST / TIMESCALEDB_HOST / REDIS_HOST / NATS_HOST are absent from compose-mode manifest.** Neither test file includes this negative assertion. In Compose mode, Program.cs removes all `.WithReference()` calls, so Aspire should not auto-generate these host-binding variables — but there is no test enforcing it. This is a minor hardening gap: if a future change accidentally adds `.WithReference(postgres)` into the compose-mode path, the absence of HOST variables won't be caught. *Left as a suggestion below.*

2. **[plan suggestion, addressed] — Verify all six container resources are absent.** Both tests check all six: `postgres`, `timescaledb`, `redis`, `nats`, `ibkr-gateway`, `lean-engine`. ✅

3. **[plan suggestion, addressed] — Verify direct-connection-string form.** Both tests verify the `Host=127.0.0.1;Port=…;Password={paramName.value}` form (not `{resource.connectionString}`). ✅

4. **[plan suggestion, addressed] — TimescaleDB asymmetry for worker.** Both compose-mode tests check the worker does NOT receive `ConnectionStrings__timescaledb` or any `TIMESCALEDB_`-prefixed key. ✅

5. **[R004 context, addressed] — Affirmatively assert TimescaleDB absence from worker.** Done in both tests via the `if (workerEnv.ConnectionStrings__timescaledb || …)` check. ✅

6. **[R004 context, not addressed] — GATEWAY_IMAGE and GATEWAY_PORT present in compose mode.** The compose-mode API env assertions in `apphost-worker-resource-wiring-tests.sh` check `ATRADE_BROKER_INTEGRATION_ENABLED`, `ATRADE_IBKR_USERNAME`, `ATRADE_IBKR_PASSWORD`, and `ATRADE_IBKR_PAPER_ACCOUNT_ID` but omit `ATRADE_IBKR_GATEWAY_URL`, `ATRADE_IBKR_GATEWAY_PORT`, and `ATRADE_IBKR_GATEWAY_IMAGE`. Since Program.cs sets these unconditionally (lines 33–34 for API, 49–51 for worker), they will be present in the compose-mode manifest — the test just doesn't verify it. *Left as a suggestion below.*

### Test Gaps
*None blocking.* The four PROMPT.md Step 3 requirements are fully covered. Two non-blocking gaps noted in Suggestions below.

### Suggestions

- **[minor] Add negative HOST-variable assertions (from R005 plan review).** In the compose-mode Node.js blocks, add a check like:
  ```javascript
  for (const hostVar of ['POSTGRES_HOST', 'TIMESCALEDB_HOST', 'REDIS_HOST', 'NATS_HOST']) {
    if (hostVar in apiEnv) throw new Error(`Compose mode should not set ${hostVar} on api`);
    if (hostVar in workerEnv) throw new Error(`Compose mode should not set ${hostVar} on ibkr-worker`);
  }
  ```
  This guards against accidental `.WithReference()` drift into the compose-mode path.

- **[minor] Assert GATEWAY_URL / GATEWAY_PORT / GATEWAY_IMAGE in compose-mode API/worker env (from R004 context).** These are set unconditionally in Program.cs and are expected to remain present. Adding them to the `expectedApi`/`expectedWorker` objects in the compose-mode assertions would document this intent and catch accidental removal.

- **[minor] Python→Node.js migration.** Both test files migrated all inline scripts from `python3` to `node`. This was not mentioned in the plan review and adds a runtime dependency on Node.js. If the test environment historically relied on Python, verify Node.js is available. The migration itself is clean — the Node.js scripts are functionally equivalent and use the same error-reporting style.

- **[minor] Secret-checking asymmetry between test files.** `apphost-infrastructure-manifest-tests.sh` checks that the env var *names* `ATRADE_POSTGRES_PASSWORD` and `ATRADE_TIMESCALEDB_PASSWORD` don't appear in the manifest text. `apphost-worker-resource-wiring-tests.sh` checks that actual *values* (`REAL_POSTGRES_PASSWORD_SHOULD_NOT_SURFACE`, etc.) don't appear. The value-based check in the worker wiring test is the stronger and more meaningful assertion. Consider aligning the infrastructure test to use the value-based approach (pass known placeholder passwords and assert they're absent), which directly verifies Aspire's secret parameter plumbing rather than checking for incidental env-var-name mentions.

### Quality Checks
- **Build:** ✅ `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj` — 0 errors, 0 warnings
- **Typecheck/Lint/Format:** No commands configured in `taskplane-config.json` (no `taskRunner.testing.commands`) and no root `package.json` — quality checks limited to build
- **Test execution:** Not run in this review (tests are bash scripts that invoke `dotnet run` — full execution belongs to Step 4)
