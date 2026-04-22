# TP-005: Establish GitHub coordination primitives — Status

**Current Step:** Step 2: Add GitHub templates
**Status:** 🟡 In Progress
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
**Status:** 🟨 In Progress

- [ ] Create `.github/ISSUE_TEMPLATE/config.yml`
- [ ] Create `.github/ISSUE_TEMPLATE/implementation.yml`
- [ ] Create `.github/ISSUE_TEMPLATE/coordination.yml`
- [ ] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Capture size, role, docs impact, verification, and unblock context where relevant

---

### Step 3: Add the coordination doc
**Status:** ⬜ Not Started

- [ ] Create `docs/process/github-coordination.md` with frontmatter
- [ ] Document workflow-state and role labels
- [ ] Define sizing rules aligned to `S`, `M`, `L`, `XL`
- [ ] Define blocked-work and resume flow
- [ ] Cross-link the active coordination sources

---

### Step 4: Update the doc index and pointers
**Status:** ⬜ Not Started

- [ ] Update `docs/INDEX.md`
- [ ] Update `README.md` only if a pointer is needed

---

### Step 5: Verification
**Status:** ⬜ Not Started

- [ ] `rg -n "agent:ready|agent:blocked|agent:resume-ready|role:architect|role:senior-engineer" .github/labels.yml docs/process/github-coordination.md .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md`
- [ ] Confirm every referenced label exists in `.github/labels.yml`
- [ ] Confirm `docs/INDEX.md` lists the coordination doc

---

### Step 6: Delivery
**Status:** ⬜ Not Started

- [ ] Commit with conventions

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

---

## Blockers

*None*

---

## Notes

*Goal: codify label/state/sizing/resume rules in durable repo artifacts so autonomous work can be coordinated through GitHub instead of chat history alone.*
