## Plan Review: Step 3 — Add opt-in manifest and wiring tests

### Verdict: APPROVE

### Summary
The four outcome checkboxes in STATUS.md map directly to the four requirements from PROMPT.md Step 3. The existing AppHost code from Steps 1–2 is cleanly gated — Compose mode is a simple `ATRADE_INFRASTRUCTURE_MODE=compose` env-var switch that produces a distinct manifest shape (no infra containers, direct connection strings with parameter-reference passwords). The plan correctly scopes modifications to the two primary test files (`apphost-infrastructure-manifest-tests.sh` and `apphost-worker-resource-wiring-tests.sh`) while leaving `lean-aspire-runtime-tests.sh` and `ibeam-runtime-contract-tests.sh` as "only if affected" touch points. No missing outcomes were identified.

### Issues Found
*None.* No blocking issues.

### Missing Items
*None.* The plan covers all four PROMPT.md Step 3 requirements.

### Suggestions

- **[minor]** Consider asserting that `POSTGRES_HOST`, `TIMESCALEDB_HOST`, `REDIS_HOST`, and `NATS_HOST` environment variables are **absent** from the compose-mode manifest. In Compose mode, Aspire has no resource references to auto-generate these host-binding variables — only the explicit `ConnectionStrings__*` values should appear. Adding a negative assertion would guard against accidental drift if someone later adds a `.WithReference()` back into the compose-mode path.

- **[minor]** When checking "infra resources are absent" from the compose-mode manifest, verify all six container resources listed in PROMPT.md Step 2: `postgres`, `timescaledb`, `redis`, `nats`, `ibkr-gateway`, and `lean-engine`. The existing Step 2 code correctly omits all six, but the test assertion is the enforcement layer — missing any one of them in the assert would leave a gap.

- **[minor]** The `apphost-worker-resource-wiring-tests.sh` function `assert_manifest_wires_worker_and_application_resources` currently verifies `"ConnectionStrings__postgres": "{postgres.connectionString}"` (the Aspire reference-expression form). The compose-mode counterpart should verify the direct-connection-string form: `"Host=127.0.0.1;Port=5432;Username=postgres;Password={postgres-password.value};Database=postgres"`. The password portion uses `{postgres-password.value}` — a parameter-reference expression, not a raw value — which satisfies the secret-safety requirement while still being directly verifiable as a string in the manifest JSON.

- **[minor]** TimescaleDB wiring asymmetry: in both modes, `ibkr-worker` does not receive a TimescaleDB connection string (only the API does). The compose-mode worker assertions should mirror this same exclusion. This is consistent with existing behavior but easy to accidentally "fix" when adding compose-mode test expectations.

### Context from Prior Reviews

The R004 code review for Step 2 surfaced two minor suggestions that remain relevant for Step 3 testing:
1. The `ibkrWorker`'s Compose-mode connection string set is intentionally postgres/redis/nats (no timescaledb) — the compose-mode tests should affirmatively assert TimescaleDB is absent from the worker, not just omit checking it.
2. In Compose mode, the API still receives `GATEWAY_IMAGE` and `GATEWAY_PORT` as informational env vars — the compose-mode manifest assertions should account for these (they're expected to remain present, not a bug).

### Quality Pre-check

No quality commands are run for plan reviews — this is a plan evaluation, not a code review.
