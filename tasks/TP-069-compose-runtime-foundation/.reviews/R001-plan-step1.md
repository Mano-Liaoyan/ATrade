## Plan Review: Step 1 — Extend the local runtime contract for Compose-managed infrastructure

### Verdict: APPROVE

### Summary
The four outcome-level checkboxes correctly capture the PROMPT requirements: six new
`.env.template` variables, preserved precedence semantics, C# contract extensions
(constants/defaults/known-vars/tests), and secret-safety guardrails. The existing
`LocalRuntimeContractLoader` already implements `.env.template` → `.env` → process-env
precedence, so this step is primarily additive. I have identified one concrete issue
(the "Intentionally excluded" comment) and several important test-gap/awareness items
the worker should address during implementation.

### Issues Found

1. **[.env.template: ~L110-112] [important]** — The existing "Intentionally excluded
   from this contract" comment block explicitly lists "Service/container target ports
   such as 5432 (Postgres), 6379 (Redis), and 4222 (NATS)" as excluded. Adding
   `ATRADE_POSTGRES_PORT=5432`, `ATRADE_REDIS_PORT=6379`, and `ATRADE_NATS_PORT=4222`
   to `.env.template` would directly contradict this comment. **Fix:** Remove or
   reword the second bullet to say these ports were previously AppHost-internal but
   are now part of the Compose host-bind contract. Keep the first bullet (Aspire
   OTLP ephemeral) and third bullet (real broker credentials) unchanged.

2. **[src/ATrade.ServiceDefaults/LocalRuntimeContract.cs: ~L175-204] [important]** —
   The `KnownVariableNames` array filters which variables are accepted from the
   process environment in `NormalizeEnvironmentValues`. Unless the six new
   `ATRADE_COMPOSE_*`, `ATRADE_POSTGRES_PORT`, `ATRADE_TIMESCALEDB_PORT`,
   `ATRADE_REDIS_PORT`, and `ATRADE_NATS_PORT` names are added to this array, process
   environment overrides for those variables will be silently dropped — breaking the
   `.env.template` → `.env` → process-env precedence contract for Compose variables.
   The plan checkbox "Extend `LocalRuntimeContract` defaults/known variables/tests"
   covers this, but it is the highest-risk implementer footgun in this step.

### Missing Items

- **None.** The four checkboxes cover all PROMPT Step 1 requirements. The worker's
  checklist captures the right outcomes.

### Suggestions

- **`.env.template` defaults for the new ports:** Consider `ATRADE_TIMESCALEDB_PORT=5433`
  rather than `5432` to avoid a default port collision with `ATRADE_POSTGRES_PORT=5432`
  when both services run on the same host. The current AppHost avoids this via Aspire's
  internal bridge network; Compose on `127.0.0.1` does not.

- **`ATRADE_COMPOSE_COMMAND` default:** Use an empty string (not `podman` or `docker`)
  as the committed default so the helper scripts' auto-detection logic (Step 3) kicks
  in naturally. An empty string also passes cleanly through `ResolveString` without
  needing special sentinel handling.

- **Port validation parity:** The existing four port variables (`ATRADE_API_HTTP_PORT`,
  etc.) are validated as TCP ports (`ResolvePort`) while `ATRADE_IBKR_GATEWAY_PORT` is
  a raw string (`ResolveString`). The new infra port variables could follow either
  pattern. Treating them as strings is acceptable since they feed Compose files, not
  .NET bindings, but consider adding a `ResolvePort` call for at least
  `ATRADE_POSTGRES_PORT` and `ATRADE_REDIS_PORT` (the two most likely to be
  hand-edited) to catch accidental non-numeric values early.

- **Shell contract test coverage:** Both `local-runtime-contract-module-tests.sh` and
  `paper-trading-config-contract-tests.sh` use hardcoded expected-variable
  dictionaries. They won't *fail* from adding new variables (their checks are
  directional), but they will lose coverage — the new variables' defaults won't be
  asserted. The worker should add the six new variables to the expected dicts in both
  tests, and add a non-secret classification assertion in
  `LocalRuntimeContractLoaderTests.Load_classifies_secret_and_non_secret_values`.

- **Typed record (optional):** A `LocalRuntimeComposeInfraSettings` record mirroring
  the existing `LocalRuntimePortSettings` / `LocalRuntimeStorageSettings` pattern
  would make the new variables first-class in the contract. This is a nice-to-have;
  `contract.GetValue("ATRADE_POSTGRES_PORT")` is sufficient for Step 1.
