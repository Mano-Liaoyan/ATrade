## Code Review: Step 2 — Add external-infra AppHost graph behavior

### Verdict: APPROVE

### Summary
All five Step 2 outcomes from PROMPT.md are correctly implemented. The `Program.cs` refactoring cleanly gates infra container declarations (postgres, timescaledb, redis, nats, ibkr-gateway, lean-engine) behind `composeInfrastructureContract.IsEnabled` in an `else` block, while api/ibkr-worker/frontend remain unconditionally declared. In Compose mode, explicit `ConnectionStrings__*` environment variables with Aspire parameter-reference syntax (`{paramName.value}`) are injected — matching each resource's previous `.WithReference()` set. Paper-trading and LEAN environment variables are preserved unconditionally. All four suggestions from the R003 plan review were addressed. Build passes with 0 errors and 0 warnings.

### Issues Found
*None.* No blocking issues.

### Pattern Violations
*None.* The code follows existing project conventions:
- `composeInfrastructureContract.IsEnabled` follows the same conditional-gating pattern used by `paperTradingContract.TryGetGatewayImageReference` and `leanRuntimeContract.TryGetDockerImageReference`
- Parameter declarations remain before the conditional block — consistent with existing ordering and necessary in both modes
- `ComposeInfrastructureContract.BuildPostgresConnectionString` / `BuildTimescaleConnectionString` correctly reuse `BuildPostgresProtocolConnectionString` (DRY)
- `WithEnvironment` chaining is fluent, matching the existing style throughout `Program.cs`

### Test Gaps
*N/A for this step.* Tests are scoped to Step 3 (manifest and wiring tests). The code structure is testable: switching `ATRADE_INFRASTRUCTURE_MODE=compose` will exercise the Compose-mode branch, and leaving it unset/default exercises the AppHost-managed branch.

### R003 Plan Review Follow-up
All four plan review suggestions were addressed in the implementation:

1. ✅ **Parameter survival in Compose mode** — `ibkrUsername`, `ibkrPassword`, `ibkrPaperAccountId`, `postgresPassword`, and `timescalePassword` are declared at line 20–24, before the `if/else` block. Both branches have access to all parameters.

2. ✅ **LEAN workspace directory creation** — `Directory.CreateDirectory(leanRuntimeContract.WorkspaceRoot)` is inside the `else` block (AppHost-managed path). In Compose mode, the workspace directory is owned by the Compose runtime (TP-069). The API still receives LEAN environment variables via `leanRuntimeContract.ToApiEnvironment()` in both modes (line 41–44, before the conditional).

3. ✅ **`.WithReference()` removal in Compose mode** — All `.WithReference()` calls are removed from the unconditional `api`/`ibkrWorker` declarations (lines 26–54) and moved into the `else` block (lines 87–95). Compose mode replaces them with explicit `WithEnvironment("ConnectionStrings__...", ...)` calls (lines 56–65).

4. ✅ **Granular Compose-mode gating for ibkr-gateway and lean-engine** — Both container-declaration blocks (`ibkr-gateway` at lines 97–115, `lean-engine` at lines 117–130) are inside the `else` block. In Compose mode, neither is declared, and the API/worker still receive the necessary broker/LEAN environment variables from the unconditional declarations above.

### Suggestions
- **[minor]** The `ibkrWorker`'s Compose-mode connection string set (postgres, redis, nats) correctly mirrors its original `.WithReference()` set (postgres, redis, nats — no timescaledb). A comment noting this intentional asymmetry would help future readers understand why timescaledb is omitted for the worker but included for the API.
- **[minor]** In Compose mode, the API still receives `GATEWAY_IMAGE` and `GATEWAY_PORT` environment variables (set unconditionally at lines 33–34) even though the ibkr-gateway container is not declared by Aspire. These are harmless — the API uses them for informational/diagnostic purposes — but if the Compose-mode gateway port ever diverges from the contract value, this could surface a stale port. Worth noting in STATUS.md discoveries for Step 5.

### Quality Checks
- **Build:** ✅ `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj` — 0 errors, 0 warnings
- **Typecheck/Lint/Format:** No commands configured in `taskplane-config.json` or `package.json` — quality checks limited to build
