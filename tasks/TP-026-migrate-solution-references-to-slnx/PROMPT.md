# Task: TP-026 - Migrate solution references from ATrade.sln to ATrade.slnx

**Created:** 2026-04-30
**Size:** M

## Review Level: 2 (Standard)

**Assessment:** This is a cleanup/migration task touching scripts, tests, docs, and task-packet references. It is low product risk but broad enough to require careful review because build/test entrypoints and Taskplane instructions may change.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-026-migrate-solution-references-to-slnx/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make `ATrade.slnx` the authoritative solution file referenced by active repository scripts, verification commands, active docs, and future-facing Taskplane prompt material. `ATrade.sln` may remain temporarily as a compatibility artifact only if needed, but active build/test/documentation guidance should prefer `ATrade.slnx`.

This cleanup follows the integration of batch `20260429T221511`, where `main` introduced `ATrade.slnx` while the completed orch branch updated `ATrade.sln`. The integration kept both solution files and updated `ATrade.slnx` to include all 20 projects. This task finishes the migration by removing stale active references to `ATrade.sln`.

## Dependencies

- **Task:** TP-025 (completed provider-backed workspace batch must be integrated first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 1 (authoritative active docs):**
- `README.md`
- `PLAN.md`
- `docs/INDEX.md`
- `tasks/CONTEXT.md`
- `scripts/README.md`

**Tier 2 (solution/build surface):**
- `ATrade.slnx`
- `ATrade.sln`
- `tests/scaffolding/project-shells-tests.sh`
- `tests/apphost/*.sh`
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs`

**Tier 3 (Taskplane references):**
- Active/pending task packets under `tasks/`
- Task packet templates or examples, if any are discovered
- Completed or archived task packets only for reference-classification; do not rewrite historical contracts unless explicitly justified in `STATUS.md`

## Environment

- **Workspace:** Repository root
- **Services required:** None for the migration itself. Verification should not require live IBKR credentials, iBeam, Docker, or LEAN; runtime-dependent scripts must continue to pass or cleanly skip under the repository's existing contracts.

## File Scope

> This task owns the migration of active solution references, not new product functionality.

- `ATrade.slnx`
- `ATrade.sln` (retain, update, or remove only after preflight classification)
- `README.md`
- `PLAN.md`
- `tasks/CONTEXT.md`
- `scripts/README.md`
- `docs/**/*.md`
- `tests/**/*.sh`
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` (only if solution-root detection needs `.slnx` support)
- Active/future task prompts or task templates that reference `ATrade.sln`
- `tasks/TP-026-migrate-solution-references-to-slnx/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight and reference classification

- [ ] Confirm `ATrade.slnx` exists, is parseable by `dotnet sln ATrade.slnx list`, and contains all currently expected projects
- [ ] Confirm `dotnet build ATrade.slnx --nologo --verbosity minimal` passes before migration changes
- [ ] Inventory every `ATrade.sln` reference with `rg -n "ATrade\.sln\b"` and classify each as active guidance/script/test, current task prompt material, or historical completed-task record
- [ ] Decide and record in `STATUS.md` whether `ATrade.sln` will be retained as a compatibility artifact or removed after migration

### Step 1: Migrate active scripts and verification commands

- [ ] Update active shell scripts and verification commands to use `ATrade.slnx` where they build/test/list the solution
- [ ] Update script assertions that inspect solution membership so they validate `ATrade.slnx`
- [ ] Update solution-root detection to recognize `ATrade.slnx` if any code/test currently keys only on `ATrade.sln`
- [ ] Preserve all existing runtime skip behavior for Docker/iBeam/LEAN-dependent checks
- [ ] Run targeted script checks that were modified

**Artifacts:**
- `tests/**/*.sh` (modified as needed)
- `scripts/README.md` (modified if script docs change)
- `src/ATrade.ServiceDefaults/LocalDevelopmentPortContract.cs` (modified only if needed)

### Step 2: Migrate active docs and future-facing prompt material

- [ ] Update active docs so build/test examples reference `ATrade.slnx`
- [ ] Update Taskplane area context and future-facing task guidance so new tasks use `ATrade.slnx`
- [ ] Update any pending task packets or task templates that are not historical records
- [ ] For completed task packets, either move them to `tasks/archive/` according to repository convention or leave historical `ATrade.sln` references untouched with an explicit exception recorded in `STATUS.md`
- [ ] Ensure docs still explain any temporary `ATrade.sln` compatibility file if it remains

**Artifacts:**
- `README.md` (modified if build/test examples mention solution files)
- `PLAN.md` (modified if active queue/current plan mentions solution files)
- `tasks/CONTEXT.md` (modified to update future task guidance and next ID if appropriate)
- `docs/**/*.md` (modified where active docs mention solution files)
- Active/future `tasks/**/PROMPT.md` references (modified only when not historical immutable task contracts)

### Step 3: Finalize solution-file contract

- [ ] Ensure `ATrade.slnx` includes every project required by the active repository build/test surface
- [ ] If `ATrade.sln` remains, document why it remains and verify no active scripts/docs prefer it over `ATrade.slnx`
- [ ] If `ATrade.sln` is removed, verify all root detection, tests, and docs still pass without it
- [ ] Add or update tests that prevent new active `ATrade.sln` references from creeping back in, if a suitable script-level check exists

**Artifacts:**
- `ATrade.slnx` (modified only if needed)
- `ATrade.sln` (modified or removed only if justified)
- Relevant tests/docs from prior steps

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to their existing contracts.

- [ ] Run `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Run targeted modified scripts, including at minimum `bash tests/scaffolding/project-shells-tests.sh` and any changed `tests/apphost/*.sh`
- [ ] Run the repository start-contract check: `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] Run a reference audit and confirm no active non-historical references prefer `ATrade.sln` over `ATrade.slnx`
- [ ] Fix all failures

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Reference audit results and historical exceptions logged in `STATUS.md`
- [ ] Delivery notes explain whether `ATrade.sln` was retained or removed

## Documentation Requirements

**Must Update:**
- `tasks/CONTEXT.md` — future task guidance should use `ATrade.slnx`; update next task ID if this task is accepted into the queue
- `scripts/README.md` — update build/test solution references
- Active docs or scripts discovered by the Step 0 reference audit that mention `ATrade.sln`

**Check If Affected:**
- `README.md` — update if verification examples mention solution files
- `PLAN.md` — update if current plan/task queue wording is stale after adding this cleanup task
- `docs/INDEX.md` — update only if new active docs are introduced
- `docs/architecture/*.md` — update only if they include active solution-file guidance
- Completed task packets — treat as historical records unless explicitly reclassified in `STATUS.md`

## Completion Criteria

- [ ] `ATrade.slnx` is the authoritative solution file in active scripts, tests, docs, and future task guidance
- [ ] `dotnet test ATrade.slnx --nologo --verbosity minimal` passes
- [ ] `dotnet build ATrade.slnx --nologo --verbosity minimal` passes
- [ ] Modified script tests pass or cleanly skip according to existing contracts
- [ ] Active reference audit has no unexplained `ATrade.sln` guidance outside documented historical/compatibility exceptions
- [ ] The repository's no-secrets and no-live-trading guardrails remain unchanged

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `chore(TP-026): complete Step N — description`
- **Bug fixes:** `fix(TP-026): description`
- **Tests:** `test(TP-026): description`
- **Docs:** `docs(TP-026): description`
- **Hydration:** `hydrate: TP-026 expand Step N checkboxes`

## Do NOT

- Reintroduce live trading, real order placement, or IBKR credential requirements
- Store secrets, account identifiers, tokens, cookies, or local `.env` values in git
- Remove `ATrade.sln` until every active dependency on it has been classified and addressed
- Rewrite completed task-packet history casually; if completed `PROMPT.md`/`STATUS.md` files are changed, record why they were treated as active docs rather than immutable historical records
- Break the repo-local startup contract (`./start run`, `./start.ps1 run`, `./start.cmd run`)
- Leave active build/test docs pointing at `ATrade.sln` without an explicit compatibility rationale

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
