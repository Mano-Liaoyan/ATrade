# TP-033: Fix LEAN Aspire runtime wiring and dashboard resource — Status

**Current Step:** Step 6: Documentation & Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Diagnose current LEAN startup gap
**Status:** ✅ Complete

- [x] Current AppHost/API LEAN config flow inspected
- [x] LEAN-disabled and temporary LEAN-enabled AppHost manifests inspected
- [x] Final Aspire resource name and runtime execution strategy recorded
- [x] Disabled-by-default behavior confirmed

---

### Step 1: Wire LEAN configuration into the AppHost graph
**Status:** ✅ Complete

- [x] AppHost LEAN runtime contract reader added or equivalent local-contract parsing implemented
- [x] Safe LEAN settings explicitly passed to the API project resource
- [x] Committed defaults remain disabled and credential-free
- [x] Disabled-default manifest/config tests added
- [x] Targeted AppHost/API build or tests run

---

### Step 2: Add an Aspire-visible LEAN Docker runtime resource
**Status:** ✅ Complete

- [x] LEAN Docker-mode AppHost resource declared when selected
- [x] Resource is visible under stable dashboard name such as `lean-engine`
- [x] Safe shared workspace mount/volume strategy implemented
- [x] Container safeguards applied without requiring IBKR/iBeam credentials
- [x] Manifest assertions cover resource name, image, mount, and API env handoff

---

### Step 3: Make the LEAN executor use the managed runtime safely
**Status:** ✅ Complete

- [x] Managed-runtime options/environment bindings added if needed
- [x] Docker-mode executor uses managed runtime or fails with explicit unavailable state
- [x] CLI/current fallback behavior preserved only when documented and tested
- [x] No-order guardrails preserved
- [x] LEAN provider unit tests cover option binding, execution strategy, unavailable runtime, timeout, and guardrails
- [x] Targeted LEAN provider tests run

---

### Step 4: Verify API behavior and optional runtime smoke
**Status:** ✅ Complete

- [x] New AppHost LEAN runtime script proves LEAN engine discovery when selected
- [x] Optional bounded analysis run smoke passes or cleanly skips when runtime unavailable
- [x] Unavailable runtime responses verified as explicit failures, not fake success
- [x] Existing LEAN apphost contract script updated for managed runtime
- [x] Targeted AppHost/LEAN scripts run

---

### Step 5: Testing & Verification
**Status:** ✅ Complete

- [x] `dotnet test tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj --nologo --verbosity minimal` passing
- [x] `bash tests/apphost/lean-analysis-engine-tests.sh` passing
- [x] `bash tests/apphost/lean-aspire-runtime-tests.sh` passing
- [x] `bash tests/apphost/analysis-engine-contract-tests.sh` passing
- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [x] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [x] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [x] All failures fixed or unrelated pre-existing failures documented

---

### Step 6: Documentation & Delivery
**Status:** ✅ Complete

- [x] "Must Update" docs modified
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged with root cause, resource name, runtime strategy, and setup caveats

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| `start run` loads `.env`/`.env.template` into the AppHost process via `scripts/local-env.sh`, but `src/ATrade.AppHost/Program.cs` currently loads only the port + paper-trading/iBeam contract and only passes IBKR settings into the `api` project. `src/ATrade.Api/Program.cs` calls `AddLeanAnalysisEngine(builder.Configuration)`, so direct API startup can read LEAN env values, but the AppHost graph has no explicit LEAN handoff or resource wiring today. | Step 1 must add an AppHost LEAN contract reader and safe `api.WithEnvironment(...)` handoff. | `scripts/start.run.sh`; `scripts/local-env.sh`; `src/ATrade.AppHost/Program.cs`; `src/ATrade.Api/Program.cs`; `.env.template` |
| AppHost manifest publishing with committed defaults and with temporary `ATRADE_ANALYSIS_ENGINE=Lean`/`ATRADE_LEAN_RUNTIME_MODE=docker` environment produced the same resource set: `api`, `frontend`, `ibkr-worker`, `postgres`, `timescaledb`, `redis`, `nats`, and generated parameter resources. No resource name containing `lean` appears, and the `api` project manifest contains no `ATRADE_ANALYSIS_ENGINE` or `ATRADE_LEAN_*` environment entries. | Root cause confirmed: LEAN settings are not represented in the AppHost graph, so the Aspire dashboard cannot show a LEAN runtime and the API project cannot discover the selected LEAN provider through AppHost-managed configuration. | Step 0 manifest probes using `dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj -- --publisher manifest` |
| Final runtime strategy chosen: use Aspire resource name `lean-engine` for Docker mode, backed by the configured `ATRADE_LEAN_DOCKER_IMAGE`. AppHost will mount a safe host workspace root (prefer a non-secret ignored/generated directory such as `artifacts/lean-workspaces` when no local override is supplied) at a container workspace root (for example `/workspace`) and pass both roots plus a stable managed container name to `ATrade.Api`. Docker-mode execution should use the managed container with `docker exec` and shared path mapping; if the managed container name/root is absent or unreachable, return `analysis-engine-unavailable` instead of silently falling back or fake succeeding. CLI mode remains process-based and unchanged. | Implement in Steps 1-3; document resource/container setup and any multi-worktree container-name caveat. | Planned `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs`; `src/ATrade.AppHost/Program.cs`; `src/ATrade.Analysis.Lean/*`; docs |
| Disabled default confirmed: committed `.env.template` keeps `ATRADE_ANALYSIS_ENGINE=none` and the default AppHost manifest has no LEAN API environment variables and no LEAN container/resource. Temporary Docker-mode environment values did not change the existing manifest before this task, confirming the current behavior is disabled-by-default but also unwired when enabled. | Preserve disabled default while adding explicit opt-in AppHost wiring. | `.env.template`; Step 0 manifest probe |
| Step 3 keeps CLI mode as the direct process fallback and intentionally requires Docker mode to use AppHost-managed container metadata (`ATRADE_LEAN_MANAGED_CONTAINER_NAME` plus shared workspace roots). The old implicit `docker run` path is not used when Docker mode lacks managed metadata; the executor returns `analysis-engine-unavailable` instead. | Covered by new LEAN runtime executor tests and reflected in final docs. | `src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs`; `tests/ATrade.Analysis.Lean.Tests/LeanAnalysisEngineTests.cs` |
| Final delivery caveats: the Aspire dashboard resource name is `lean-engine`; the default managed container name is `atrade-lean-engine` and can be overridden in ignored `.env` for simultaneous worktrees; the default shared workspace is `artifacts/lean-workspaces` mounted at `/workspace`; Docker-mode analysis requires a local Docker-compatible engine plus the configured official LEAN image and returns `analysis-engine-unavailable` when those are absent. Optional smoke skipped locally because `quantconnect/lean:foundation` is not present. | Documented in active docs and scripts; no secrets or live-trading behavior introduced. | `.env.template`; docs; `tests/apphost/lean-aspire-runtime-tests.sh` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 21:45 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 21:45 | Step 0 started | Diagnose current LEAN startup gap |
| 2026-04-30 | Step 1 started | Wire LEAN configuration into the AppHost graph |
| 2026-04-30 | Step 1 targeted verification | `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal` and `bash tests/apphost/lean-aspire-runtime-tests.sh` passed after fixing a `StartsWith` compile error. |
| 2026-04-30 | Step 2 started | Add an Aspire-visible LEAN Docker runtime resource. |
| 2026-04-30 | Step 2 targeted verification | `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal` and `bash tests/apphost/lean-aspire-runtime-tests.sh` passed with Docker-mode manifest assertions. |
| 2026-04-30 | Step 3 started | Make LEAN executor use the managed Docker runtime safely. |
| 2026-04-30 | Step 3 targeted verification | `dotnet test tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj --nologo --verbosity minimal` passed (12 tests). |
| 2026-04-30 | Step 4 started | Verify API behavior and optional LEAN runtime smoke. |
| 2026-04-30 | Step 4 targeted verification | `bash tests/apphost/lean-aspire-runtime-tests.sh` passed with optional smoke skipped because `quantconnect/lean:foundation` is not present locally; `bash tests/apphost/lean-analysis-engine-tests.sh` passed with LEAN CLI runtime skip. |
| 2026-04-30 | Step 5 started | Full testing and verification. |
| 2026-04-30 | Step 5 verification complete | All listed Step 5 commands passed. Optional LEAN runtime smoke skipped cleanly because the configured image is not present locally; no failures required pre-existing-failure documentation. |
| 2026-04-30 | Step 6 started | Documentation and delivery. |
| 2026-04-30 | Step 6 complete | Must-update docs and affected docs updated; final discoveries/caveats recorded. |

---

## Blockers

*None*

---

## Notes

- Step 6 Check If Affected review: `.env.template` was updated for non-secret managed LEAN settings; `docs/architecture/paper-trading-workspace.md`, `docs/architecture/overview.md`, and `README.md` were updated because the AppHost graph/runtime surface changed; `docs/INDEX.md` needed no change because no new active docs were introduced.
