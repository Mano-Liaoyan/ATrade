# TP-066: Chart landing watchlist default and stored-stock selector — Status

**Current Step:** Step 3: Preserve symbol-specific chart behavior
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-07
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

### Step 1: Build the chart landing selection workflow
**Status:** ✅ Complete

- [x] Reuse backend watchlist APIs/workflows to load stored stocks for `/chart`
- [x] Select the first stored/watchlist instrument as the default chart candidate with exact identity preserved
- [x] Provide selection and canonical chart/analysis/backtest route handoff state
- [x] Preserve loading, empty, cached-fallback, and unavailable states without hard-coded symbols or synthetic bars

---

### Step 2: Render `/chart` with stored stocks plus default chart
**Status:** ✅ Complete

- [x] Render a "Stored stocks" selector/list and chart region on `/chart`
- [x] Automatically render visible chart/provider state for the first stored stock when available
- [x] Show explicit empty/unavailable state with `/search` and `/watchlist` links when no stored stock can load
- [x] Preserve TP-064 internal-scroll/no-clipping guardrail

---

### Step 3: Preserve symbol-specific chart behavior
**Status:** 🟨 In Progress

- [ ] Keep `/chart/[symbol]` direct chart rendering with exact identity/range parsing
- [ ] Ensure stored-stock selection updates chart and/or route without losing identity metadata
- [ ] Ensure chart-to-analysis/backtest handoff routes remain canonical

---

### Step 4: Add chart landing validation
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-chart-watchlist-default-tests.sh`
- [ ] Update existing route/chart tests only where shared paths or strings changed
- [ ] Keep validation provider/runtime independent

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Chart landing validation passing
- [ ] Stock chart visibility validation passing
- [ ] Chart range preset validation passing
- [ ] Route architecture validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] Chart landing/default stored-stock docs updated
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
| 2026-05-07 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-07 02:00 | Task started | Runtime V2 lane-runner execution |
| 2026-05-07 02:00 | Step 0 started | Preflight |
| 2026-05-07 04:00 | Step 0 completed | Required paths verified; TP-065 canonical chart routes present and `/symbols` route absent |
| 2026-05-07 04:15 | Step 1 completed | Added chart landing workflow using backend watchlist workflow, first stored-stock default selection, canonical handoffs, explicit fallback/empty/unavailable states; `cd frontend && npm run build` passed |
| 2026-05-07 04:25 | Step 2 completed | `/chart` now renders Stored stocks selector/list plus default chart region with explicit empty/unavailable links and internal scroll CSS; `cd frontend && npm run build` passed |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
