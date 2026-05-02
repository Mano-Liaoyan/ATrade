# TP-041: Deepen frontend workspace workflow modules — Status

**Current Step:** Step 2: Extract search and chart data workflows
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-02
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

### Step 1: Extract watchlist and exact pin workflows
**Status:** ✅ Complete

> ⚠️ Hydrate: Expanded on entry after confirming TP-040 backend watchlist intake keeps `/api/workspace/watchlist` responses authoritative with `instrumentKey`/`pinKey`, while browser storage remains symbol-only fallback/migration input.

- [x] Watchlist workflow module exposes normalized state/commands for backend load, retry, legacy fallback/migration, exact pin toggle, removal, saving key, disabled state, and stable error text
- [x] TradingWorkspace delegates watchlist orchestration to the workflow module while retaining trending market-data loading and UI markers
- [x] TrendingList, SymbolSearch, and Watchlist consume workflow-derived pinned keys/saving state/commands without importing watchlist clients or storage
- [x] Backend-owned persisted `pinKey`/`instrumentKey` values remain authoritative; provisional keys are limited to optimistic UI matching and symbol-only cache fallback
- [x] New frontend workspace workflow shell test file asserts the module seam, storage authority, and renderer boundaries

---

### Step 2: Extract search and chart data workflows
**Status:** ✅ Complete

- [x] Search/chart workflow modules own debounce, provider errors, candle/indicator loading, stream subscription, polling fallback, and source labels
- [x] `SymbolSearch` and `SymbolChartView` render workflow state without behavior regression
- [x] Frontend browser data access remains behind `ATrade.Api`
- [x] Targeted TypeScript/build and frontend shell tests passing

---

### Step 3: Preserve workspace behavior and test surface
**Status:** ✅ Complete

- [x] Home workspace and symbol page behavior verified stable
- [x] Exact pins, cached fallback, provider-unavailable messages, and SignalR-to-HTTP fallback verified
- [x] New workflow module test assertions added
- [x] Targeted frontend tests passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Frontend build/checks passing
- [ ] Integration tests passing or cleanly skipped where applicable
- [ ] All failures fixed
- [ ] Backend build passes

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
| 2026-05-02 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-02 16:01 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 16:01 | Step 0 started | Preflight |
| 2026-05-02 16:05 | Step 0 completed | Required paths verified; TP-040 complete; .NET 10.0.203, Node v24.15.0, npm 11.12.1, and frontend dependencies available |
| 2026-05-02 16:06 | Step 1 hydrated | Final watchlist API shape confirmed: backend `instrumentKey`/`pinKey` authoritative; frontend workflow owns symbol-only cache migration/fallback and provisional optimistic key matching |
| 2026-05-02 16:17 | Step 1 completed | Watchlist workflow hook added; rendering components delegate pin state/commands; new workflow shell test and frontend build passed |
| 2026-05-02 16:18 | Step 2 started | Search and chart workflow extraction begun |
| 2026-05-02 16:29 | Step 2 completed | Symbol search and chart data workflow hooks added; SymbolSearch/SymbolChartView render hook state; frontend build and workflow shell test passed |
| 2026-05-02 16:43 | Step 3 completed | Existing frontend workspace script updated for workflow seams and passed; workflow module shell assertions verify exact pins, cached fallback, provider messages, API boundary, and SignalR-to-HTTP fallback |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
