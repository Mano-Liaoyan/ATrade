# TP-048: Rebuild search, trending, and watchlist as a terminal market monitor — Status

**Current Step:** Step 3: Integrate monitor into commands and retire old list UI
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-04
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Model market monitor state and actions
**Status:** ✅ Complete

> ⚠️ Hydrate: Decision — wrap and reuse the existing `symbolSearchWorkflow` and `watchlistWorkflow` hooks so debounce, capped search, provider/error copy, backend watchlist authority, and exact identity behavior remain centralized; add a new terminal monitor workflow above them for trending rows, unified view state, sorting/filtering, selection, and terminal action intents.

- [x] Wrap existing search/watchlist workflows with a combined terminal monitor workflow/view model
- [x] Preserve `ATrade.Api` clients, exact identity helpers, explicit capped search limits, and exact chart/analysis action payloads
- [x] Preserve backend watchlist authority, optimistic pin/unpin states, cached fallback copy, provider/authentication error copy, and debounce/minimum-query behavior
- [x] Add source assertions for bounded search and no direct provider/database/browser secrets access

---

### Step 2: Implement dense terminal monitor components
**Status:** ✅ Complete

- [x] Create terminal market monitor component set
- [x] Render dense identity/source/pin/rank rows with explicit states
- [x] Add sorting, filters, show-more/less, selection, and accessible controls
- [x] Add chart/analysis actions preserving exact identity

---

### Step 3: Integrate monitor into commands and retire old list UI
**Status:** ✅ Complete

- [x] Wire SEARCH/WATCH/HOME commands to the monitor
- [x] Replace old SymbolSearch/TrendingList/Watchlist usage
- [x] Keep SCREENER visible-disabled rather than fake
- [x] Update old search/list tests to terminal monitor markers

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Market monitor validation passing
- [ ] Search exploration validation passing
- [ ] Workflow module validation passing
- [ ] Frontend workspace validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
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
| 2026-05-04 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-04 22:30 | Task started | Runtime V2 lane-runner execution |
| 2026-05-04 22:30 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
