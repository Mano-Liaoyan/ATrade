# TP-057: Make market monitor table scrollbars visible — Status

**Current Step:** Step 1: Audit current table scroll ownership and overflow paths
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

### Step 1: Audit current table scroll ownership and overflow paths
**Status:** 🟨 In Progress

- [ ] Inspect table, parent monitor, scroll-area primitive, and CSS overflow behavior
- [ ] Verify wide table columns/identity/actions remain required
- [ ] Identify final Radix/native/CSS scrollbar strategy
- [ ] Record chosen strategy and tradeoffs in discoveries

---

### Step 2: Implement visible vertical and horizontal table scrolling
**Status:** ⬜ Not Started

- [ ] Constrain vertical overflow to an internal table viewport
- [ ] Enable horizontal scrolling for the wide table while preserving sticky headers and row actions
- [ ] Make scrollbar tracks/thumbs visible when overflow exists
- [ ] Preserve full-viewport and responsive behavior without page-level scrolling

---

### Step 3: Add scrollbar validation coverage
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-market-monitor-scrollbar-tests.sh`
- [ ] Update existing market-monitor/top-chrome/layout validation scripts only if affected
- [ ] Ensure validation is deterministic and provider-independent

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] New scrollbar validation passing
- [ ] Market monitor validation passing
- [ ] Top chrome/filter density validation passing
- [ ] Simplified layout validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] README/PLAN verification/current-surface text updated if affected
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
| 2026-05-05 23:32 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 23:32 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
