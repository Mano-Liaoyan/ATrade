# TP-048: Rebuild search, trending, and watchlist as a terminal market monitor — Status

**Current Step:** Step 0: Preflight
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
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand after deciding whether to wrap, reuse, or retire existing search/watchlist workflow modules.

- [ ] Create combined monitor workflow/view model
- [ ] Preserve API clients, exact identity, and capped search behavior
- [ ] Preserve backend watchlist authority and provider/error copy
- [ ] Add source assertions for no unbounded/direct access paths

---

### Step 2: Implement dense terminal monitor components
**Status:** ⬜ Not Started

- [ ] Create terminal market monitor component set
- [ ] Render dense identity/source/pin/rank rows with explicit states
- [ ] Add sorting, filters, show-more/less, selection, and accessible controls
- [ ] Add chart/analysis actions preserving exact identity

---

### Step 3: Integrate monitor into commands and retire old list UI
**Status:** ⬜ Not Started

- [ ] Wire SEARCH/WATCH/HOME commands to the monitor
- [ ] Replace old SymbolSearch/TrendingList/Watchlist usage
- [ ] Keep SCREENER visible-disabled rather than fake
- [ ] Update old search/list tests to terminal monitor markers

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
