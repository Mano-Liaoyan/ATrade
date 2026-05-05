# TP-053: Remove top chrome and compact market filters — Status

**Current Step:** Step 1: Remove the visible app header and safety strip
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 1
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

### Step 1: Remove the visible app header and safety strip
**Status:** 🟨 In Progress

- [ ] Remove the rendered app header/brand and visible safety strip from `ATradeTerminalApp`
- [ ] Preserve navigation status, module rail, workspace layout, module content, and module-level safety messaging
- [ ] Remove unused header/brand/safety-strip CSS and grid row allocation
- [ ] Verify the workspace still fills the viewport without page-level vertical scrolling

---

### Step 2: Compact market-monitor filters without losing behavior
**Status:** ⬜ Not Started

- [ ] Refactor `MarketMonitorFilters` into a denser filter bar/section without the long explanatory paragraph
- [ ] Preserve filter accessibility, test IDs/data attributes, selected state, counts, and Clear-all behavior
- [ ] Reduce filter padding/gaps/chip wrapping footprint in CSS across breakpoints
- [ ] Keep filtering local to existing capped payloads without changing workflow semantics

---

### Step 3: Add focused validation for removed chrome and filter density
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-top-chrome-filter-density-tests.sh`
- [ ] Assert removed header/safety-strip source/rendered markup stays absent
- [ ] Assert preserved module rail/workspace/market-monitor/safety/API-boundary surfaces stay present
- [ ] Update affected existing apphost frontend validation scripts

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] New chrome/filter validation passing
- [ ] Affected layout and market-monitor validations passing
- [ ] No-command/shell/cutover validations passing if touched
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
| 2026-05-05 18:01 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 18:01 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
