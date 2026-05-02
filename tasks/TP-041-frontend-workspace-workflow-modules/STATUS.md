# TP-041: Deepen frontend workspace workflow modules — Status

**Current Step:** Step 0: Preflight
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
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand checkboxes when entering this step based on final backend identity/intake interfaces.

- [ ] Watchlist workflow module owns backend load, legacy fallback, migration, pin/unpin, and error state
- [ ] Workspace/list/search rendering modules consume workflow state/commands
- [ ] Backend-owned persisted keys remain authoritative
- [ ] New frontend workflow shell test file added

---

### Step 2: Extract search and chart data workflows
**Status:** ⬜ Not Started

- [ ] Search/chart workflow modules own debounce, provider errors, candle/indicator loading, stream subscription, polling fallback, and source labels
- [ ] `SymbolSearch` and `SymbolChartView` render workflow state without behavior regression
- [ ] Frontend browser data access remains behind `ATrade.Api`
- [ ] Targeted TypeScript/build and frontend shell tests passing

---

### Step 3: Preserve workspace behavior and test surface
**Status:** ⬜ Not Started

- [ ] Home workspace and symbol page behavior verified stable
- [ ] Exact pins, cached fallback, provider-unavailable messages, and SignalR-to-HTTP fallback verified
- [ ] New workflow module test assertions added
- [ ] Targeted frontend tests passing

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
