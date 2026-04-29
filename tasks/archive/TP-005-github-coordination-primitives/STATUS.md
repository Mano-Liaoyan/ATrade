# TP-005: Establish GitHub coordination primitives — Status

**Current Step:** Step 6: Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-04-23
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read `AGENTS.md`, the GitHub coordination skill, and the Scrum Master plan
- [x] Confirm `.github/` does not yet contain coordination templates or a label manifest
- [x] Extract the recommended workflow and role labels from the active docs

---

### Step 1: Define the label manifest
**Status:** ✅ Complete

- [x] Create `.github/labels.yml`
- [x] Include workflow labels
- [x] Include role labels
- [x] Record name, description, and color for each label

---

### Step 2: Add GitHub templates
**Status:** ✅ Complete

- [x] Create `.github/ISSUE_TEMPLATE/config.yml`
- [x] Create `.github/ISSUE_TEMPLATE/implementation.yml`
- [x] Create `.github/ISSUE_TEMPLATE/coordination.yml`
- [x] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] Capture size, role, docs impact, verification, and unblock context where relevant

---

### Step 3: Add the coordination doc
**Status:** ✅ Complete

- [x] Create `docs/process/github-coordination.md` with frontmatter
- [x] Document workflow-state and role labels
- [x] Define sizing rules aligned to `S`, `M`, `L`, `XL`
- [x] Define blocked-work and resume flow
- [x] Cross-link the active coordination sources

---

### Step 4: Update the doc index and pointers
**Status:** ✅ Complete

- [x] Update `docs/INDEX.md`
- [x] Update `README.md` only if a pointer is needed

---

### Step 5: Verification
**Status:** ✅ Complete

- [x] `rg -n "agent:ready|agent:blocked|agent:resume-ready|role:architect|role:senior-engineer" .github/labels.yml docs/process/github-coordination.md .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md`
- [x] Confirm every referenced label exists in `.github/labels.yml`
- [x] Confirm `docs/INDEX.md` lists the coordination doc

---

### Step 6: Delivery
**Status:** ✅ Complete

- [x] Commit with conventions

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Workflow labels extracted from `AGENTS.md`/`.pi/skills/github-coordination/SKILL.md`: `agent:ready`, `agent:claimed`, `agent:in-progress`, `agent:needs-human`, `agent:blocked`, `agent:resume-ready`, `agent:review`, `agent:merged`, `agent:docs-required`, `agent:trivial` | Use in `.github/labels.yml` and templates | `AGENTS.md`; `.pi/skills/github-coordination/SKILL.md` |
| Role labels extracted from `AGENTS.md`/`.pi/skills/github-coordination/SKILL.md`: `role:architect`, `role:senior-engineer`, `role:senior-test-engineer`, `role:devops`, `role:scrum-master`, `role:code-reviewer`, `role:handyman`, `role:onboarder` | Use in `.github/labels.yml` and templates | `AGENTS.md`; `.pi/skills/github-coordination/SKILL.md` |
| README pointer was not added because the existing read order already sends humans to `docs/INDEX.md`, which now lists the coordination doc | Leave README unchanged in this slice | `README.md`; `docs/INDEX.md` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-22 23:44 | Task started | Runtime V2 lane-runner execution |
| 2026-04-22 23:44 | Step 0 started | Preflight |
| 2026-04-23 | Step 0 completed | Preflight findings captured in STATUS discoveries |
| 2026-04-23 | Step 1 started | Define the label manifest |
| 2026-04-23 | Step 1 completed | Added `.github/labels.yml` with workflow and role labels |
| 2026-04-23 | Step 2 started | Add GitHub templates |
| 2026-04-23 | Step 2 completed | Added issue and PR templates for implementation and coordination work |
| 2026-04-23 | Step 3 started | Add the coordination doc |
| 2026-04-23 | Step 3 completed | Added `docs/process/github-coordination.md` with labels, sizing, and resume flow |
| 2026-04-23 | Step 4 started | Update the doc index and pointers |
| 2026-04-23 | Step 4 completed | Added coordination doc to `docs/INDEX.md`; README pointer not needed |
| 2026-04-23 | Step 5 started | Verification |
| 2026-04-23 | Step 5 completed | Verified label references and docs index coverage |
| 2026-04-23 | Step 6 started | Delivery |
| 2026-04-23 | Step 6 completed | Final docs(TP-005) delivery commit created |
| 2026-04-22 23:52 | Worker iter 1 | done in 467s, tools: 114 |
| 2026-04-22 23:52 | Task complete | .DONE created |

---

## Blockers

*None*

---

## Notes

*Goal: codify label/state/sizing/resume rules in durable repo artifacts so autonomous work can be coordinated through GitHub instead of chat history alone.*
