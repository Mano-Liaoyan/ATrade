# Task: TP-010 — Fix the Aspire-managed Next.js runtime contract

**Created:** 2026-04-24
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** This task fixes the way the AppHost launches the Next.js app so
local frontend behavior matches Next.js expectations. It changes startup
configuration, frontend runtime metadata, and AppHost verification, but it does
not add business logic.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-010-fix-aspire-nextjs-runtime-contract/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Fix the frontend startup contract when the Next.js app is launched through
`src/ATrade.AppHost`.

The Aspire console output shows the frontend starting with incorrect runtime
assumptions:

- Next.js warns about a non-standard `NODE_ENV`
- Next.js warns that it inferred the wrong workspace root because it sees
  multiple lockfiles and may choose the repo root instead of `frontend/`

Direct startup from `frontend/` is clean, so the defect is in the AppHost-managed
launch contract rather than in the Next.js app itself.

This task must fix the root causes, not merely suppress warnings.

## Scope

Deliver a durable AppHost/frontend runtime fix:

1. Ensure the AppHost launches the frontend with a valid Next.js environment for
   `next dev` (`NODE_ENV=development`, not a custom environment name and not an
   accidental production/default value).
2. Preserve any richer app/environment identity through separate variables if
   needed; do not overload `NODE_ENV` with non-Next values.
3. Add explicit Next.js config so Turbopack/workspace-root detection resolves to
   `frontend/` instead of heuristics based on lockfiles higher in the repo.
4. Keep direct frontend startup (`cd frontend && npm run dev`) working.
5. Add verification that the AppHost-managed frontend starts without the
   `NODE_ENV` and workspace-root warnings seen in the Aspire console.

## Dependencies

- **None** for implementation, but this task should land before any later task
  that further edits the AppHost frontend resource contract.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `tasks/CONTEXT.md`
- `src/ATrade.AppHost/Program.cs`
- `frontend/package.json`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- Any existing `frontend/next.config.*` file (none currently exists unless added by another task)

## Observed Evidence

The operator reported Aspire console output containing these frontend warnings:

- `You are using a non-standard "NODE_ENV" value in your environment.`
- `Warning: Next.js inferred your workspace root, but it may not be correct.`
- `Detected multiple lockfiles ... /ATrade/package-lock.json ... /ATrade/frontend/package-lock.json`

Local reproduction/inspection in this repo showed:

- `cd frontend && npm run dev` starts cleanly
- The AppHost-managed frontend launch path does not currently enforce the
  correct Next.js runtime contract

The implementation should solve the runtime contract itself, not rely on manual
operator cleanup of incidental local files.

## Environment

- **Workspace:** Project root
- **Services required:** None for implementation; AppHost runtime verification is allowed

## File Scope

- `src/ATrade.AppHost/Program.cs`
- `frontend/next.config.ts` (new) or `frontend/next.config.mjs` if that is the best fit
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/` additional runtime-focused test file if needed
- `scripts/README.md`
- `README.md` and `PLAN.md` only if current-state wording needs correction

## Steps

### Step 0: Preflight

- [ ] Re-read the current AppHost frontend resource configuration
- [ ] Confirm direct `frontend/` startup is clean and the defect is specific to the AppHost-managed path
- [ ] Confirm there is currently no explicit Next.js config pinning Turbopack root

### Step 1: Fix frontend environment semantics

- [ ] Update the AppHost frontend resource so `next dev` runs with a valid Next.js `NODE_ENV`
- [ ] Do not use custom environment names in `NODE_ENV`
- [ ] If the repo still needs a richer environment identity, pass it through a separate variable rather than abusing `NODE_ENV`

### Step 2: Fix workspace-root detection

- [ ] Add explicit Next.js config for the frontend so Turbopack root/workspace resolution points at the intended directory
- [ ] Make the fix durable even if an extra lockfile appears at the repo root later
- [ ] Do not rely only on deleting a stray file from one machine

### Step 3: Preserve the startup contract

- [ ] Keep `frontend/package.json` scripts semantically unchanged unless a minimal adjustment is truly required
- [ ] Keep the AppHost-managed `frontend` resource on port 3000 with external exposure
- [ ] Keep direct `npm run dev` inside `frontend/` working

### Step 4: Add verification

- [ ] Extend the existing frontend bootstrap test or add a dedicated runtime test
- [ ] Verify direct startup still serves the home page markers
- [ ] Verify the AppHost-managed frontend path no longer emits the non-standard `NODE_ENV` warning
- [ ] Verify the AppHost-managed frontend path no longer emits the workspace-root / multiple-lockfiles warning
- [ ] Prefer deterministic assertions over ad-hoc manual dashboard inspection

### Step 5: Update docs

- [ ] Update `scripts/README.md` if the frontend/AppHost startup contract is now more explicit
- [ ] Update `README.md` or `PLAN.md` only if current-state wording would otherwise remain misleading

### Step 6: Verification

- [ ] `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Run any new AppHost runtime verification added by this task
- [ ] Confirm the AppHost-managed frontend startup is warning-free for these two issues

### Step 7: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md` if runtime semantics become explicit there
**Check If Affected:** `README.md`, `PLAN.md`

## Completion Criteria

- [ ] AppHost launches Next.js with a correct `NODE_ENV` for `next dev`
- [ ] Next.js no longer warns about inferred workspace root when launched through the AppHost path
- [ ] Direct frontend startup still works
- [ ] Verification covers the AppHost-managed frontend startup path, not just direct `npm run dev`

## Git Commit Convention

- **Implementation:** `fix(TP-010): description`
- **Checkpoints:** `checkpoint: TP-010 description`

## Do NOT

- Silence the warning without correcting the underlying runtime contract
- Solve the issue by requiring operators to manually delete files every time
- Replace the AppHost-managed frontend with a separate ad-hoc script flow
- Change unrelated frontend behavior or add feature work

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
