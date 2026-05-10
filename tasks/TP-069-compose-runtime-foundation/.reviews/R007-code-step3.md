## Code Review: Step 3 — Add reusable Compose helper scripts

### Verdict: APPROVE

### Summary
Both `scripts/compose-infra.sh` and `scripts/compose-infra.ps1` satisfy all five PROMPT.md Step 3 requirements: the `.env.template` → `.env` → process-env loading contract (via reuse of existing `local-env.sh`/`local-env.ps1`), three-stage command selection (`ATRADE_COMPOSE_COMMAND` → Podman → Docker → fail), automatic ibkr/lean profile selection with credential-guard checks, detached `up` that won't `down` on exit, and no secret values printed in any output path. The scripts are well-structured, handle edge cases (missing compose file, no action, help flags, dry-run mode), and maintain cross-platform behavioral equivalence. Bash 3.2 compatibility is preserved.

### Issues Found
*None that would block progress.*

### Pattern Violations
*None.*

### Test Gaps
*No tests exist yet for these scripts — that belongs to Step 4 (Add contract validation), which explicitly covers `tests/compose/compose-infra-contract-tests.sh`. The helper scripts themselves are test-ready: they support dry-run mode (`ATRADE_COMPOSE_DRY_RUN=true`) that prints the assembled command line without executing, providing a clean surface for contract tests to validate command selection, profile flags, and project name without a running container engine.*

### Suggestions

1. **PowerShell action case-sensitivity** — The bash version does a case-sensitive comparison `[[ "$action" == 'up' ]]` and the PowerShell version uses `$Action -eq 'up'` (also case-sensitive). This is consistent across platforms, but a developer typing `Up` or `UP` would hit the usage help. Consider accepting case-insensitive actions on both platforms for robustness (e.g., `atrade_lower` in bash, `-ieq` or `.ToLowerInvariant()` in PowerShell). This is purely a UX polish suggestion.

2. **`$ErrorActionPreference = 'Stop'` in PowerShell** — Currently set at the top of the script. If a child compose command fails, `$LASTEXITCODE` captures the non-zero exit code and the script exits with it. However, if the compose command throws a terminating error (e.g., binary not found after selection succeeded), the script terminates before reaching `exit $LASTEXITCODE`. Consider adding a `try/catch` around the `& $Executable @Arguments` invocation to ensure a clear error message is printed before exit:
   ```powershell
   try {
       & $Executable @Arguments
       exit $LASTEXITCODE
   } catch {
       [Console]::Error.WriteLine("Failed to execute compose command: $_")
       exit 1
   }
   ```
   This is a defensive improvement; the current behavior is not broken.

3. **Bash: `atrade_select_compose_command` uses a global variable** — The function writes to `selected_compose_command` as a side effect rather than returning it. This is idiomatic bash but can be surprising. The `local -n` nameref (bash 4.3+) isn't available in bash 3.2, so the current approach is the correct Bash 3.2-compatible pattern. No change needed, but worth noting for future maintainers.

4. **`exec` in bash vs `&` in PowerShell** — The bash version uses `exec` (replaces the shell process), while the PowerShell version uses `&` with explicit `exit $LASTEXITCODE` (PowerShell has no `exec` equivalent). Both approaches are correct for their platforms. The bash `exec` means that if the compose command fails, the parent shell won't see any post-error cleanup messages — but compose's own stderr output still reaches the terminal, which is sufficient.

5. **Dry-run token spacing** — `atrade_print_tokens` in bash produces clean space-separated output but doesn't quote tokens that contain spaces (e.g., from a multi-word `ATRADE_COMPOSE_COMMAND`). The dry-run output for `docker compose` would show `docker compose -f compose.yaml ...` which is unambiguous. This is fine as-is.

6. **`Test-ATradeTruthy` switch statement** — The PowerShell version accepts `1`, `true`, `yes`, `y`, `on`. The bash version (`atrade_is_truthy`) accepts the same set. This is a reasonable and consistent truthy set. Consider adding `enabled` if the project ever uses that convention, but the current set matches existing `.env.template` conventions (`false` / `true`).

### Cross-Reference to R006 Plan Review

The R006 plan review (APPROVE) made six implementation suggestions. Here's how this code addresses them:

| R006 Suggestion | Status |
|---|---|
| Bash 3.2 compatibility | ✅ No Bash 4+ features used |
| Check `ATRADE_IBKR_GATEWAY_IMAGE` for ibkr profile | ⚠️ Not implemented — the PROMPT only requires credential checks, so this was optional |
| Source `local-env.sh`/`local-env.ps1` | ✅ Both scripts source the existing loader |
| Explicit `--project-name` flag | ✅ Both scripts pass `--project-name` |
| Document subcommand surface and `--help` | ✅ Usage message lists `up\|down\|config\|ps\|logs\|pull\|restart` |
| Leak safety beyond printing | ✅ `exec` in bash prevents any post-exec traces; PowerShell captures no env in output |

### Quality Checks

No typecheck/lint/format-check commands are configured in `.pi/taskplane-config.json` or `package.json` for this project. Shell syntax validation (`bash -n` and PowerShell AST parse) both passed:

```
$ bash -n scripts/compose-infra.sh
SYNTAX OK

$ pwsh -NoProfile -Command "...Parser::ParseFile..."
SYNTAX OK
```
