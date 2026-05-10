## Plan Review: Step 3 — Add reusable Compose helper scripts

### Verdict: APPROVE

### Summary
The four outcome-level checkboxes in STATUS.md cover all five PROMPT.md Step 3 requirements: Unix and Windows helpers with the `.env.template` → `.env` → process-env loading contract, three-stage command selection (`ATRADE_COMPOSE_COMMAND` → Podman → Docker → fail), and conditional ibkr/lean profile auto-selection that doesn't leak secrets. The existing `scripts/local-env.sh` already implements the env-loading contract that these new scripts need, so the implementation can build on proven patterns. The scope is appropriately constrained to two new files with no integration into `start run`.

### Issues Found
*None at the outcome level that would block progress.*

### Missing Items
*None.* All five PROMPT.md Step 3 requirements are represented across the four checkboxes. The "helper `up` does not run `down` on exit" guardrail is a natural default for `docker compose up` / `podman compose up` (no `--abort-on-container-exit` or `--exit-code-from` flags) and doesn't need a separate outcome checkbox — it's a standard compose behavior the worker just needs to preserve by not adding destructive flags.

### Suggestions
- **Bash 3.2 compatibility:** `scripts/README.md` states: "The Unix loader must stay compatible with Bash 3.2 because `/usr/bin/env bash` can resolve to that version on macOS developer machines." The new `compose-infra.sh` should follow the same constraint. The existing `local-env.sh` already targets Bash 3.2 (arrays, `[[ ]]`, `read -r`, `${!var+x}` indirect expansion all work in 3.2). Keeping `compose-infra.sh` compatible means avoiding Bash 4+ features like associative arrays (`declare -A`) and `mapfile`/`readarray`. This is an implementation guardrail, not a new outcome.

- **Profile-detection expansion:** The `ibkr` profile auto-selection could benefit from checking `ATRADE_IBKR_GATEWAY_IMAGE` is non-empty in addition to integration-enabled + non-placeholder username/password. This prevents enabling the ibkr profile when a developer has valid creds but hasn't configured a gateway image. This is a defensive edge case the worker can handle in implementation.

- **Consider sourcing `local-env.sh`:** The `compose-infra.sh` script's env-loading contract is identical to what `scripts/local-env.sh` already implements (`.env.template` → `.env` → process-env precedence, with all `ATRADE_*` variables already present in `.env.template` from Step 1). Sourcing `local-env.sh` rather than reimplementing the parsing would reduce duplication and ensure behavioral consistency between `start run` and `compose-infra.sh`. The PowerShell equivalent would similarly reuse `local-env.ps1`.

- **`--project-name` flag:** The `compose.yaml` uses `${ATRADE_COMPOSE_PROJECT_NAME:-atrade}` in the `name:` field. Depending on the compose implementation, this field may or may not be respected. To be safe, the helper should also pass `--project-name "${ATRADE_COMPOSE_PROJECT_NAME:-atrade}"` explicitly. This is an implementation detail but a common gotcha with Compose interop.

- **Help/subcommand surface:** The PROMPT calls these "reusable" helpers. Beyond `up`, consider documenting what subcommands are supported (at minimum `up`, `down`, `ps`, `logs`) and forwarding unknown subcommands directly to the compose implementation. A `--help` flag that lists the supported surface would improve discoverability. This is a UX suggestion, not required for correctness.

- **Leak safety beyond printing:** The "does not print secret values" guardrail applies not just to explicit `echo`/`printf` but also to Compose's own output. In verbose/error modes, Compose may echo environment variable values. Consider running Compose without `--verbose` and using `2>&1` with a grep filter if `set -x` tracing is used. This is a subtlety the worker should handle during implementation.
