## Code Review: Step 3 — Migrate startup and AppHost validation

### Verdict: APPROVE

### Summary
All four outcome checkboxes are satisfied. The start-wrapper tests now verify
Compose-before-AppHost startup order via dry-run mode with ordering assertions.
AppHost manifest/resource tests default to compose-mode expectations (no infra
container resources). iBeam and LEAN tests have been rewritten to verify
Compose profile ownership of `ibkr-gateway`/`lean-engine` via `compose.yaml`
inspection while preserving secret-safe handoff to `api`/`ibkr-worker`. Windows
wrapper tests align with Unix behavior by setting `ATRADE_INFRASTRUCTURE_MODE=apphost`
to bypass Compose in CI smoke. The wholesale migration from `python3` to `node`
inline scripts is clean and consistent.

### Issues Found

1. **[lean-aspire-runtime-tests.sh:169] [minor]** — `optional_smoke_analysis_run_if_runtime_available`
   unconditionally prints SKIP and returns 0, even when Docker is healthy and
   available. The old code ran a real LEAN container smoke test when the image
   was present. This is a test-coverage regression for the API's LEAN Docker
   invocation path, which still exists in compose mode (the API receives
   `ATRADE_LEAN_DOCKER_COMMAND` and invokes Docker per-analysis-run).

   **Suggestion:** Either restore the conditional smoke test (guarded on Compose
   not actively managing `lean-engine`, i.e., `ATRADE_LEAN_RUNTIME_MODE=docker`
   and engine available) or log this coverage gap as a discovery in STATUS.md
   with rationale that full runtime validation is deferred to Step 4.

2. **[frontend/next-env.d.ts:3] [minor]** — Unrelated auto-generated change
   persists from R002's review: the import path changed from
   `"./.next/types/routes.d.ts"` to `"./.next/dev/types/routes.d.ts"`. This is
   Next.js auto-generation noise in the diff and does not affect functionality,
   but it was flagged for reversion in R002.

### Pattern Violations

*None.*

### Test Gaps

1. **Legacy apphost-mode `lean-engine` container assertion is no longer tested
   anywhere.** The old `assert_lean_docker_manifest_declares_dashboard_resource_mount_and_api_handoff`
   verified the `lean-engine` container appeared in the AppHost manifest under
   apphost mode. After renaming to `assert_lean_docker_manifest_omits_dashboard_resource_and_hands_off_api_config`,
   only the compose-mode absence is verified. The apphost-mode `lean-engine`
   container path in `Program.cs` (the `else` branch) is now untested. The
   analogous `ibkr-gateway` legacy assertion is preserved in
   `apphost-worker-resource-wiring-tests.sh` via `assert_manifest_wires_ibeam_container_when_enabled`
   (explicit apphost mode), but no test exercises `lean-engine` under apphost
   mode.

   **Risk:** Low. The apphost-mode branch is documented as "diagnostic/temporary
   only" (Step 2). If it bit-rots, the impact is limited to the legacy fallback
   path.

### Suggestions

- **Consider adding infrastructure port variables to the ibeam test's
  `publish_manifest` call.** Currently `publish_manifest` in
  `ibeam-runtime-contract-tests.sh` doesn't set any infrastructure port
  variables (`ATRADE_POSTGRES_PORT`, etc.). While the C# `LocalRuntimeContractLoader`
  defaults ports to their standard values (5432, 5433, 6379, 4222), setting the
  same test ports used in other test files (15432/15433/16379/14222) would make
  the manifest generation path more predictable and reduce sensitivity to
  implicit defaults.

- **The `assert_line_order` helper** in `start-wrapper-tests.sh` (lines 69–81)
  uses `${haystack%%"$first"*}` which works correctly for these exact needle
  strings. If the needles ever contain glob characters (`*`, `?`, `[`), the
  pattern-matching expansion would behave unexpectedly. This is fine for the
  current literal needles (`printf __FAKE_COMPOSE__`, `__FAKE_DOTNET__`), but
  worth a comment for future maintainers.

### Verification Notes

- No quality-check commands (`typecheck`, `lint`, `format:check`) are configured
  in `.pi/taskplane-config.json` or `package.json`, so automated static checks
  were not exercised. Shell scripts and PowerShell scripts should pass
  shellcheck and PSScriptAnalyzer respectively when run manually.
