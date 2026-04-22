# TP-005: Establish GitHub coordination primitives — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-23
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 0
**Size:** M

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Read `AGENTS.md`, the GitHub coordination skill, and the Scrum Master plan
- [ ] Confirm `.github/` does not yet contain coordination templates or a label manifest
- [ ] Extract the recommended workflow and role labels from the active docs

---

### Step 1: Define the label manifest
**Status:** ⬜ Not Started

- [ ] Create `.github/labels.yml`
- [ ] Include workflow labels
- [ ] Include role labels
- [ ] Record name, description, and color for each label

---

### Step 2: Add GitHub templates
**Status:** ⬜ Not Started

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

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Goal: codify label/state/sizing/resume rules in durable repo artifacts so autonomous work can be coordinated through GitHub instead of chat history alone.*
