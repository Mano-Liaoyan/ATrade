# Task: TP-040 - Deepen analysis and workspace intake modules

**Created:** 2026-05-02
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This task pulls domain ordering and validation out of the HTTP surface into Analysis and Workspaces modules while keeping HTTP payloads stable. It touches multiple modules and can change request handling, but should avoid storage schema changes.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-040-analysis-workspace-intake-modules/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen the analysis intake and workspace watchlist intake modules so `ATrade.Api` delegates complete use cases instead of owning domain ordering. This matters because the current HTTP surface builds analysis requests, fetches candles, resolves symbol identity, initializes workspace schema, normalizes pins, and maps storage/provider errors inline, making the domain modules shallow and harder to test through their intended interfaces.

## Dependencies

- **Task:** TP-038 (analysis intake must use the deepened market-data read seam)
- **Task:** TP-039 (IBKR/iBeam readiness should be stable before final intake error mapping)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/analysis-engines.md` — analysis request/result contract
- `docs/architecture/modules.md` — API, Analysis, Workspaces module responsibilities
- `docs/architecture/paper-trading-workspace.md` — watchlist and analysis workspace behavior

## Environment

- **Workspace:** `src/ATrade.Analysis`, `src/ATrade.Workspaces`, `src/ATrade.Api`
- **Services required:** None for unit tests; Postgres/AppHost scripts must skip cleanly when unavailable

## File Scope

- `src/ATrade.Api/Program.cs`
- `src/ATrade.Analysis/AnalysisContracts.cs`
- `src/ATrade.Analysis/AnalysisEngineRegistry.cs`
- `src/ATrade.Analysis/*Intake*.cs` (new if needed)
- `src/ATrade.Analysis.Lean/*`
- `src/ATrade.Workspaces/WorkspaceWatchlistRepository.cs`
- `src/ATrade.Workspaces/WorkspaceWatchlistNormalizer.cs`
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistRepository.cs`
- `src/ATrade.Workspaces/*Intake*.cs` (new if needed)
- `tests/ATrade.Analysis.Tests/AnalysisRequestIntakeTests.cs` (new)
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistIntakeTests.cs` (new)
- `tests/ATrade.Analysis.Lean.Tests/*`
- `tests/ATrade.Workspaces.Tests/*`
- `tests/apphost/analysis-engine-contract-tests.sh`
- `tests/apphost/postgres-watchlist-persistence-tests.sh`
- `docs/architecture/*`

## Steps

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Move analysis request construction into Analysis intake

- [ ] Add an Analysis intake module that accepts the HTTP-facing analysis run request shape or a provider-neutral equivalent and owns symbol/timeframe defaults, candle acquisition, symbol identity resolution, invalid-request mapping, and engine selection handoff
- [ ] Reduce `ATrade.Api` analysis route to request binding, intake invocation, and HTTP result projection only
- [ ] Add `tests/ATrade.Analysis.Tests/AnalysisRequestIntakeTests.cs` covering direct bars, symbol/timeframe candle acquisition, provider errors, invalid requests, and engine-unavailable results
- [ ] Run targeted Analysis and LEAN tests

**Artifacts:**
- `src/ATrade.Analysis/*Intake*.cs` (new/modified)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/ATrade.Analysis.Tests/AnalysisRequestIntakeTests.cs` (new)

### Step 2: Move watchlist request handling into Workspaces intake

- [ ] Add a Workspaces intake module that owns schema initialization ordering, current identity use, pin/replace/unpin normalization, exact instrument key validation, storage-unavailable mapping, and stable error shapes
- [ ] Reduce `ATrade.Api` watchlist routes to request binding, intake invocation, and HTTP result projection only
- [ ] Add `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistIntakeTests.cs` covering load, pin, replace, exact unpin, ambiguous legacy unpin, invalid input, and storage-unavailable cases
- [ ] Run targeted Workspaces tests

**Artifacts:**
- `src/ATrade.Workspaces/*Intake*.cs` (new/modified)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistIntakeTests.cs` (new)

### Step 3: Keep HTTP behavior stable and simplify route code

- [ ] Verify existing analysis and watchlist HTTP paths, status codes, and payload fields stay compatible
- [ ] Keep market-data and analysis engine error mapping stable and explicit
- [ ] Keep temporary local workspace identity seam documented and contained in Workspaces
- [ ] Run targeted AppHost analysis/watchlist contract scripts

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `tests/apphost/analysis-engine-contract-tests.sh` (modified if needed)
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run integration tests if affected: `bash tests/apphost/analysis-engine-contract-tests.sh`, `bash tests/apphost/lean-analysis-engine-tests.sh`, `bash tests/apphost/postgres-watchlist-persistence-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/modules.md` — Analysis/Workspaces/API responsibilities after intake moves
- `docs/architecture/analysis-engines.md` — analysis request intake behavior if changed
- `docs/architecture/paper-trading-workspace.md` — watchlist/analysis behavior if changed

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — market-data/analysis error mapping if changed
- `README.md` — endpoint summary if observable behavior changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Analysis request construction is testable through an Analysis module interface
- [ ] Watchlist request handling is testable through a Workspaces module interface
- [ ] `ATrade.Api` no longer owns domain ordering beyond HTTP binding/projection

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-040): complete Step N — description`
- **Bug fixes:** `fix(TP-040): description`
- **Tests:** `test(TP-040): description`
- **Hydration:** `hydrate: TP-040 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Change HTTP paths or payload fields unless backward-compatible
- Add real order placement, live-trading behavior, direct frontend database access, or production mocks
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
