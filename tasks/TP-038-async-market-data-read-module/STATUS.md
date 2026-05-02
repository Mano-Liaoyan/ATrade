# TP-038: Deepen the async market-data read module — Status

**Current Step:** Step 3: Update HTTP, SignalR, and analysis callers
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

### Step 1: Define one async read-result interface
**Status:** ✅ Complete

> ⚠️ Hydrate: Expanded after inspecting the current synchronous `IMarketDataService`, `IMarketDataProvider`, HTTP handlers, SignalR hub, and provider-abstraction tests.

- [x] `MarketDataReadResult<T>` and async read methods for trending, search, symbol lookup, candles, indicators, and latest updates are defined with cancellation-token parameters
- [x] `MarketDataService` maps provider status, provider errors, validation errors, and successful payloads into the new read-result shape without async caller status checks
- [x] Existing HTTP payload/status behavior preserved
- [x] New async read module test file added
- [x] Async read module tests cover success, unavailable, invalid request, and cancellation behavior
- [x] Targeted provider-abstraction tests passing

---

### Step 2: Convert Timescale cache-aside and IBKR provider adapters
**Status:** ✅ Complete

- [x] Sync-over-async removed from market-data provider/cache read paths
- [x] Timescale-first cache-aside semantics preserved
- [x] IBKR/iBeam reads remain cancellable and safely redacted
- [x] Targeted IBKR and Timescale tests passing

---

### Step 3: Update HTTP, SignalR, and analysis callers
**Status:** ✅ Complete

- [x] HTTP route handlers await the deepened read interface and keep payloads stable
- [x] SignalR snapshot path uses async read/streaming seam without duplicate provider status logic
- [x] Analysis candle acquisition uses the new seam
- [x] Targeted AppHost/analysis/market-data scripts passing

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
| 2026-05-02 14:52 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 14:52 | Step 0 started | Preflight |
| 2026-05-02 14:52 | Step 0 completed | Required files, TP-037 dependency, .NET SDK, and solution projects verified |
| 2026-05-02 14:53 | Step 1 hydrated | Planned async read-result shape, service mapping, payload stability, and targeted tests |
| 2026-05-02 14:56 | Step 1 completed | Async read-result contract added; provider-abstraction tests passed (12/12) |
| 2026-05-02 14:57 | Step 2 started | Converting Timescale cache-aside and IBKR adapter read paths to async end-to-end |
| 2026-05-02 15:08 | Step 2 completed | Removed sync-over-async, converted Timescale and IBKR adapters, targeted IBKR/Timescale tests passed (46/46) |
| 2026-05-02 15:09 | Step 3 started | Updating API, SignalR, and analysis callers to await async market-data reads |
| 2026-05-02 15:24 | Step 3 completed | API, SignalR, and analysis callers await async read seam; targeted apphost scripts passed |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
