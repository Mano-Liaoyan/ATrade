# TP-063: Terminal backtest comparison and equity overlay — Status

**Current Step:** Step 3: Add comparison validation coverage
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-06
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

### Step 1: Add comparison selection state and view-model helpers
**Status:** ✅ Complete

- [x] Comparison selection state and eligibility helpers added
- [x] Only completed runs with persisted result/equity data are selectable
- [x] Deterministic curve color/label helpers added
- [x] Selection/normalization checks added as appropriate

---

### Step 2: Render comparison table and equity overlay
**Status:** ✅ Complete

- [x] Comparison metrics table/cards rendered
- [x] Accessible equity overlay rendered without unnecessary new dependencies
- [x] Strategy and benchmark curves/legends shown with honest empty states
- [x] Module layout remains responsive and shell guardrails preserved

---

### Step 3: Add comparison validation coverage
**Status:** ✅ Complete

- [x] `tests/apphost/frontend-terminal-backtest-comparison-tests.sh` created
- [x] Backtest workspace validation updated only if affected
- [x] Validation remains provider/runtime independent

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Comparison validation passing
- [ ] Backtest workspace validation passing
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
| 2026-05-06 01:20 | Task started | Runtime V2 lane-runner execution |
| 2026-05-06 01:20 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
