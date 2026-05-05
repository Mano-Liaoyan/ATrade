# TP-052: Simplify workspace layout and remove extra chrome — Status

**Current Step:** Step 2: Refactor layout and persistence to a single full-viewport workspace
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Remove context, monitor-strip, and footer chrome from app composition
**Status:** ✅ Complete

- [x] Remove context/monitor/status-strip rendering from `ATradeTerminalApp`
- [x] Delete unused context/monitor/status-strip components
- [x] Remove shell-only context and monitor HTML regions
- [x] Preserve real module content and workflow surfaces

---

### Step 2: Refactor layout and persistence to a single full-viewport workspace
**Status:** ✅ Complete

- [x] Refactor `TerminalWorkspaceLayout` to one primary region with no splitters/reset/resizing
- [x] Remove context/monitor persisted size types and storage behavior
- [x] Remove centered max-width/outer horizontal margins from the page shell
- [x] Prevent page-level vertical scrolling while keeping internal content scroll where needed

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
| 2026-05-05 14:12 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 14:12 | Step 0 started | Preflight |
| 2026-05-05 14:13 | Step 1 started | Removing shell-only context, monitor, and footer chrome |
| 2026-05-05 14:18 | Step 1 targeted check | Market monitor validation passed after app composition changes |
| 2026-05-05 14:19 | Step 2 started | Refactoring layout persistence and viewport shell behavior |
| 2026-05-05 14:25 | Step 2 targeted check | Frontend build passed after single-workspace layout/persistence changes |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
