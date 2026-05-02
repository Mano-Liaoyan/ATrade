# TP-040: Deepen analysis and workspace intake modules — Status

**Current Step:** Step 2: Move watchlist request handling into Workspaces intake
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-02
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

### Step 1: Move analysis request construction into Analysis intake
**Status:** ✅ Complete

> ⚠️ Hydrate: Expand checkboxes when entering this step based on final intake interface shape and updated market-data read seam.

- [x] Analysis module exposes an `IAnalysisRequestIntake` seam and provider-neutral `AnalysisRunRequest`/`AnalysisRunIntakeResult` types that delegate to `IMarketDataService` and `IAnalysisEngineRegistry`
- [x] Analysis intake owns direct-bar validation, symbol/timeframe defaults, candle acquisition via the async market-data read seam, symbol identity resolution/fallback, provider-error propagation, and engine handoff
- [x] `ATrade.Api` analysis route simplified to HTTP binding, intake invocation, and HTTP result projection without request construction helpers
- [x] `tests/ATrade.Analysis.Tests/AnalysisRequestIntakeTests.cs` covers direct bars, candle acquisition, provider errors, invalid requests, and engine-unavailable results
- [x] Targeted Analysis and LEAN tests passing

---

### Step 2: Move watchlist request handling into Workspaces intake
**Status:** ✅ Complete

- [x] Workspaces intake owns schema initialization ordering, identity use, normalization, exact unpin validation, and stable errors
- [x] `ATrade.Api` watchlist routes simplified to HTTP binding/projection
- [x] New Workspaces watchlist intake test file added
- [x] Targeted Workspaces tests passing

---

### Step 3: Keep HTTP behavior stable and simplify route code
**Status:** ⬜ Not Started

- [ ] Existing analysis/watchlist paths, status codes, and payload fields verified compatible
- [ ] Provider/analysis/storage error mapping remains stable and explicit
- [ ] Temporary local workspace identity seam remains contained and documented
- [ ] Targeted AppHost analysis/watchlist scripts passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Integration tests passing or cleanly skipped where applicable
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
| 2026-05-02 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-02 15:44 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 15:44 | Step 0 started | Preflight |
| 2026-05-02 15:46 | Step 0 completed | Required paths verified; .NET 10.0.203 available; TP-038 and TP-039 marked complete |
| 2026-05-02 15:47 | Step 1 hydrated | Analysis intake seam planned around provider-neutral run request/result and async market-data read seam |
| 2026-05-02 15:58 | Step 1 completed | Analysis intake seam implemented; API analysis route delegated; targeted Analysis/LEAN tests passed |
| 2026-05-02 16:00 | Step 2 started | Workspaces watchlist intake implementation begun |
| 2026-05-02 16:12 | Step 2 completed | Workspaces watchlist intake seam implemented; API watchlist routes delegated; targeted Workspaces tests passed |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
