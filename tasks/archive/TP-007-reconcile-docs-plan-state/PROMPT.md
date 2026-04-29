# Task: TP-007 — Reconcile planning and docs with the actual repo state

**Created:** 2026-04-23
**Size:** S

## Review Level: 1 (Light)

**Assessment:** Documentation-only reconciliation of planning files and active docs
against the repository's actual current state. No product code or runtime
behavior changes.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```text
tasks/TP-007-reconcile-docs-plan-state/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Reconcile the planning and documentation surface with what already exists in the
repository today.

The recent bootstrap work landed architecture docs, GitHub coordination
artifacts, an API scaffold, and a real Next.js slice, but several planning/docs
artifacts still read as if some of that work has not happened yet. This task
should make the active docs trustworthy again before the next implementation
batch starts.

## Scope

Deliver a focused docs reconciliation pass:

1. Compare `PLAN.md`, `README.md`, `scripts/README.md`, and `tasks/CONTEXT.md`
   against the current repository contents.
2. Mark or rewrite any stale milestone/status language that no longer matches
   reality.
3. Fix stale `AGENT.md` references so active docs consistently point to
   `AGENTS.md`.
4. Update the task-area context if needed so it reflects the next planned work
   and current task inventory accurately.
5. Keep the changes documentation-only. Do not change runtime code or tests in
   this task.

## Dependencies

- **None** — safe, doc-only reconciliation.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `scripts/README.md`
- `tasks/CONTEXT.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `docs/process/github-coordination.md`
- `.github/labels.yml`
- `.github/ISSUE_TEMPLATE/`

## Environment

- **Workspace:** Project root
- **Services required:** None

## File Scope

- `README.md`
- `PLAN.md`
- `scripts/README.md`
- `tasks/CONTEXT.md`
- `docs/INDEX.md` (if needed)
- Other active docs only if they contain stale `AGENT.md` / status references

## Steps

### Step 0: Preflight

- [ ] Read the active docs and planning files listed above
- [ ] Identify stale status claims that no longer match the repository
- [ ] Identify stale `AGENT.md` references in active docs

### Step 1: Reconcile plan and status language

- [ ] Update `PLAN.md` milestone text so completed work is no longer shown as open
- [ ] Update current-status wording in `README.md` and `scripts/README.md` where needed
- [ ] Keep wording precise about what is complete versus still only scaffolded

### Step 2: Fix doc-link and read-order drift

- [ ] Replace stale `AGENT.md` references with `AGENTS.md` in active docs
- [ ] Ensure read-order and `see_also` pointers resolve to real files
- [ ] Avoid changing document authority or status classification unintentionally

### Step 3: Refresh task-area context

- [ ] Update `tasks/CONTEXT.md` so the next task ID and future-work notes reflect the newly staged work
- [ ] Keep the context aligned with the current roadmap and active docs

### Step 4: Verification

- [ ] `grep -RIn "AGENT\\.md" README.md PLAN.md docs scripts tasks || true`
- [ ] Confirm open items in `PLAN.md` correspond to work that is still actually pending
- [ ] Confirm no code or runtime files changed outside the stated file scope

### Step 5: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `PLAN.md`, `tasks/CONTEXT.md`
**Check If Affected:** `README.md`, `scripts/README.md`, `docs/INDEX.md`

## Completion Criteria

- [ ] Active docs no longer claim already-finished work is still open
- [ ] Active docs consistently reference `AGENTS.md`
- [ ] `tasks/CONTEXT.md` accurately reflects the next queued work
- [ ] The change is documentation-only

## Git Commit Convention

- **Implementation:** `docs(TP-007): description`
- **Checkpoints:** `checkpoint: TP-007 description`

## Do NOT

- Modify application code, AppHost wiring, or tests in this task
- Re-scope future milestones beyond what the current repository state justifies
- Mark aspirational implementation work as complete when only docs/scaffolding exist
- Change doc authority (`status`) classifications unless required and explicitly justified

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
