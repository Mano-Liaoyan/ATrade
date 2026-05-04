# Task: TP-036 - Deepen the local runtime contract module

**Created:** 2026-05-02
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This change touches startup shims, AppHost contract readers, direct API startup, committed defaults, docs, and runtime-contract tests. It changes a safety-critical seam around local ports, broker/iBeam enablement, LEAN runtime settings, and non-secret storage defaults.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-036-local-runtime-contract-module/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen the local runtime contract module so one implementation owns `.env` / `.env.template` parsing, environment overlay, defaults, validation, secret/non-secret classification, and process environment projection for local development. This matters because the current implementation duplicates shallow parsing modules and has drift between committed template values, docs, and tests for paper-only safety defaults.

## Dependencies

- **None**

## Context to Read First

> Only list docs the worker actually needs. Less is better.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `scripts/README.md` — startup/runtime contract authority
- `docs/architecture/overview.md` — AppHost/runtime overview
- `docs/architecture/paper-trading-workspace.md` — paper-only and iBeam safety contract
- `docs/architecture/analysis-engines.md` — LEAN runtime configuration contract

## Environment

- **Workspace:** repo root, `src/ATrade.AppHost`, `src/ATrade.ServiceDefaults`
- **Services required:** None for unit/shell contract tests; Docker/Podman-dependent integration scripts must skip cleanly when unavailable

## File Scope

> The orchestrator uses this to avoid merge conflicts: tasks with overlapping
> file scope run on the same lane (serial), not in parallel.

- `.env.template`
- `scripts/start.run.sh`
- `scripts/start.run.ps1`
- `scripts/start.run.cmd`
- `scripts/README.md`
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs`
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs`
- `src/ATrade.AppHost/AppHostStorageContract.cs`
- `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs`
- `tests/apphost/local-runtime-contract-module-tests.sh` (new)
- `tests/start-contract/*`
- `tests/apphost/*contract-tests.sh`
- `README.md`
- `PLAN.md`
- `docs/architecture/*`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Inventory and fix committed contract drift

- [ ] Compare `.env.template`, startup shims, tests, `README.md`, `PLAN.md`, `scripts/README.md`, and active architecture docs for local runtime defaults
- [ ] Restore committed paper-only safety defaults: no real secrets, no live-trading path, dashboard UI default `0`, broker/iBeam disabled unless intentionally documented otherwise, cache freshness docs matching template
- [ ] Add `tests/apphost/local-runtime-contract-module-tests.sh` or equivalent new contract test file that fails on future default drift
- [ ] Run targeted tests: `bash tests/apphost/paper-trading-config-contract-tests.sh` and `bash tests/start-contract/start-wrapper-tests.sh`

**Artifacts:**
- `.env.template` (modified)
- `tests/apphost/local-runtime-contract-module-tests.sh` (new)
- `scripts/README.md` (modified)

### Step 2: Deepen shared env parsing and resolved contract interface

- [ ] Create or consolidate one runtime-contract implementation that parses environment files, overlays process env, validates required/optional values, and exposes resolved local contract values
- [ ] Replace duplicate parsing in AppHost storage, paper trading, LEAN, and local port contract modules with calls through the shared module while preserving existing public behavior
- [ ] Preserve secret handling: credential-bearing values remain redacted/secret parameters and never appear in committed docs/tests
- [ ] Run targeted tests for the changed .NET contract modules

**Artifacts:**
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` (modified or seam adapter)
- `src/ATrade.AppHost/*Contract.cs` (modified)
- New or moved runtime-contract module files under `src/` (new/modified)

### Step 3: Project resolved contract values into startup shims and AppHost

- [ ] Ensure Unix, PowerShell, and cmd `start run` shims apply the same dashboard and OTLP defaults as the .NET contract module
- [ ] Ensure AppHost uses resolved contract values for Postgres, TimescaleDB, iBeam, LEAN, frontend, and API environment handoff without duplicating defaults
- [ ] Preserve the `start run` contract across Unix and Windows shims
- [ ] Run targeted AppHost manifest/start-contract tests

**Artifacts:**
- `scripts/start.run.*` (modified if needed)
- `src/ATrade.AppHost/Program.cs` (modified if needed)
- `tests/start-contract/*` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run integration/contract tests: `bash tests/start-contract/start-wrapper-tests.sh`, `bash tests/apphost/paper-trading-config-contract-tests.sh`, `bash tests/apphost/local-port-contract-tests.sh`, and the new runtime-contract test
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — resolved runtime contract interface, defaults, and secret/non-secret rules
- `README.md` — startup/default summary if defaults or runtime behavior change
- `docs/architecture/overview.md` — AppHost runtime contract if changed
- `docs/architecture/paper-trading-workspace.md` — paper-only/iBeam defaults if changed

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — LEAN env handoff if shared contract changes its shape
- `docs/architecture/modules.md` — module map if a new runtime-contract module is introduced
- `PLAN.md` — task queue status if wording changes materially

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Committed defaults, docs, and tests agree on safe local runtime defaults
- [ ] Duplicate env-file parsing is removed or isolated behind a single local runtime contract seam

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-036): complete Step N — description`
- **Bug fixes:** `fix(TP-036): description`
- **Tests:** `test(TP-036): description`
- **Hydration:** `hydrate: TP-036 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Commit secrets, IBKR credentials, account identifiers, tokens, session cookies, or live-trading defaults
- Break `./start run`, `./start.ps1 run`, or `./start.cmd run`

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
