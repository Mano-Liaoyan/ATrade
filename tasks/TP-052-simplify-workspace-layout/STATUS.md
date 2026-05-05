# TP-052: Simplify workspace layout and remove extra chrome — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Remove context, monitor-strip, and footer chrome from app composition
**Status:** ⬜ Not Started

- [ ] Remove context/monitor/status-strip rendering from `ATradeTerminalApp`
- [ ] Delete unused context/monitor/status-strip components
- [ ] Remove shell-only context and monitor HTML regions
- [ ] Preserve real module content and workflow surfaces

---

### Step 2: Refactor layout and persistence to a single full-viewport workspace
**Status:** ⬜ Not Started

- [ ] Refactor `TerminalWorkspaceLayout` to one primary region with no splitters/reset/resizing
- [ ] Remove context/monitor persisted size types and storage behavior
- [ ] Remove centered max-width/outer horizontal margins from the page shell
- [ ] Prevent page-level vertical scrolling while keeping internal content scroll where needed

---

### Step 3: Remove background grid styling and add layout validation
**Status:** ⬜ Not Started

- [ ] Remove active background grid CSS
- [ ] Create `tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Update shell/cutover tests for simplified layout expectations
- [ ] Preserve workflow, provider-boundary, disabled-module, and no-order assertions

---

### Step 4: Update active documentation and verification inventory
**Status:** ⬜ Not Started

- [ ] Update design doc for simplified layout
- [ ] Update paper workspace and module docs
- [ ] Update README verification inventory
- [ ] Update PLAN follow-up direction

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Simplified layout validation passing
- [ ] No-command validation passing
- [ ] Updated shell/cutover validations passing
- [ ] Affected workflow validations passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged

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
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
