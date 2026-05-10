## Plan Review: Step 2 — Add external-infra AppHost graph behavior

### Verdict: APPROVE

### Summary
The five checkboxes correctly map to all five PROMPT.md Step 2 requirements. The approach — conditionally skipping infra container declarations, keeping project/frontend resources, replacing implicit `.WithReference()`-generated connection strings with explicit `ConnectionStrings__*` environment variables backed by the `ComposeInfrastructureContract` built in Step 1, preserving paper-trading/LEAN environment handoff, and gating everything behind `composeInfrastructureContract.IsEnabled` — is sound. The plan stays properly scoped to graph-wiring without creeping into Step 3's test domain.

### Issues Found
*None.* All PROMPT.md Step 2 requirements have a corresponding plan outcome.

### Missing Items
*None.* The five outcomes cover the stated requirements.

### Suggestions
- **Parameter survival in Compose mode:** The plan says "omit AppHost infra container resources" but doesn't explicitly call out that the `postgres-password`, `timescaledb-password`, `ibkr-username`, `ibkr-password`, and `ibkr-paper-account-id` secret parameters must still be declared in Compose mode. The connection string builders (`ComposeInfrastructureContract.BuildPostgresConnectionString(postgresPassword)`) and IBKR environment injections both depend on these `IResourceBuilder<ParameterResource>` handles being available. Ensure these parameter declarations move outside (or before) the Compose-mode conditional block so they exist in both modes.
- **LEAN workspace directory creation:** The lean-engine container block also calls `Directory.CreateDirectory(leanRuntimeContract.WorkspaceRoot)`. In Compose mode the container declaration is skipped, but the API still receives LEAN environment variables (including `ATRADE_LEAN_WORKSPACE_ROOT`) via `leanRuntimeContract.ToApiEnvironment()`. Consider whether the workspace directory should still be created (as a standalone statement, not inside the container-declaration conditional) so the API can write analysis output at that path. Otherwise, the API may fail when it tries to use the configured workspace.
- **`.WithReference()` removal in Compose mode:** The API resource currently has `.WithReference(postgres)`, `.WithReference(timescaledb)`, `.WithReference(redis)`, `.WithReference(nats)` — and the worker has `.WithReference(postgres)`, `.WithReference(redis)`, `.WithReference(nats)`. When `composeInfrastructureContract.IsEnabled` is true, these references must be removed (the target resources won't exist) and replaced with explicit `WithEnvironment("ConnectionStrings__postgres", ...)` calls. The plan's checkbox 3 says "inject external connection strings" which covers the addition, but the removal of old references is implied — make sure both happen in the same conditional branch.
- **Granular Compose-mode gating for ibkr-gateway and lean-engine:** The ibkr-gateway and lean-engine container declarations are already doubly conditional (checking `ShouldStartIbeamContainer` / `TryGetDockerImageReference`). In Compose mode, both should be skipped unconditionally regardless of those inner checks. The cleanest implementation would be to wrap the whole container-declaration block for infra + gateway + LEAN in `if (!composeInfrastructureContract.IsEnabled)`, and then separately handle the API/worker wiring with a mode-switch on connection string injection.
