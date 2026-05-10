## Plan Review: Step 4 — Add contract validation

### Verdict: APPROVE

### Summary
The 3 outcome-level checkboxes in STATUS.md cover all three PROMPT.md Step 4 requirements: (1) a new `tests/compose/compose-infra-contract-tests.sh` validating command selection, profiles, ports, volumes, and safety; (2) live-Compose checks kept optional/skippable when no engine is installed; (3) existing contract tests updated for the new variables. The existing `local-runtime-contract-module-tests.sh` and `paper-trading-config-contract-tests.sh` already include the Compose variables in their expected-defaults dictionaries (from Step 1), so the update work for checkbox 3 is likely a verification pass or minimal adjustment. The worker has access to the full `compose.yaml`, `scripts/compose-infra.sh`, `.env.template`, and prior review insights from Steps 1-3, and is well-positioned to author correct contract tests.

### Issues Found
*None at the outcome level that would block progress.*

### Missing Items
*None.* All three PROMPT.md Step 4 bullet points are represented.

### Suggestions
- **PROMPT-specific validations:** PROMPT.md calls out 10 distinct validation surface areas under checkbox 1: Podman-first command selection, Docker fallback, exact `ATRADE_COMPOSE_COMMAND` override, stable project name `atrade`, profile auto-selection rules, localhost port mappings, named volumes, `pids_limit: 2048`, `TS_TUNE_MEMORY=512MB` / `TS_TUNE_NUM_CPUS=2`, and absence of real secret values in committed files. The STATUS.md checkbox groups these under five headings ("command selection, profiles, ports, volumes, and safety") which is appropriate for an outcome-level plan, but the worker should cross-reference with PROMPT.md during implementation to ensure the pids-limit and Timescale-tune checks aren't accidentally omitted from the "safety" category.

- **Existing tests already cover Compose variables:** Both `local-runtime-contract-module-tests.sh` and `paper-trading-config-contract-tests.sh` already validate the Compose defaults in their Python inline assertions (including `ATRADE_COMPOSE_COMMAND`, `ATRADE_COMPOSE_PROJECT_NAME`, `ATRADE_POSTGRES_PORT`, `ATRADE_TIMESCALEDB_PORT`, `ATRADE_REDIS_PORT`, `ATRADE_NATS_PORT`, and lane-specific exclusion checks). Checkbox 3 may therefore be a confirmation/verification pass rather than requiring new test code. The worker should run these tests first to confirm they pass before deciding whether modifications are needed.

- **Static-first design:** The new contract test script should follow the existing pattern from `local-runtime-contract-module-tests.sh` — use `grep`/`python3` inline assertions against committed files (`compose.yaml`, `.env.template`, `scripts/compose-infra.sh`) for the bulk of validation, and gate any live `compose config` calls behind a feature check (`command -v podman || command -v docker`). This keeps the tests fast, deterministic, and CI-safe.

- **Helper script command-selection testing:** The command-selection logic in `scripts/compose-infra.sh` (`atrade_select_compose_command`) uses `command -v podman` / `command -v docker` for detection and `ATRADE_COMPOSE_COMMAND` for explicit override. The contract tests should validate this logic by sourcing the helper script (or replicating the detection pattern) with controlled environment variables. The `atrade_has_real_ibkr_credentials` and profile-auto-selection functions are similarly testable through environment-variable manipulation.

- **Safety: secret-in-committed-files check:** The PROMPT requires validating "absence of real secret values in committed files." The existing tests check `.env.template` for secret-looking patterns (TOKEN, SECRET, COOKIE, SESSION in key names, real-looking account IDs). The new contract tests should extend this to `compose.yaml` — verifying no hardcoded credentials, tokens, or real account identifiers appear in the committed Compose file. The current `compose.yaml` uses variable interpolation (`${ATRADE_POSTGRES_PASSWORD:-ATRADE_POSTGRES_PASSWORD}`) which is safe, and the test should confirm this pattern is preserved.

- **Review R004 callback:** The Step 2 plan review noted that `127.0.0.1` loopback binding (not `0.0.0.0`) is a security guardrail. The contract tests should explicitly verify this in `compose.yaml` — each service's port mapping starts with `127.0.0.1:` — as a safety assertion beyond general "ports" validation.
