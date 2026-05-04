# TP-042: Correct chart range presets — Status

**Current Step:** Step 5: Documentation & Delivery
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

### Step 1: Model chart ranges as lookbacks from now
**Status:** ✅ Complete

- [x] Create chart range preset helper with supported normalized values and lookback boundaries
- [x] Update market-data models/contracts to normalize requested ranges while retaining safe compatibility for legacy `timeframe` callers
- [x] Add provider-abstraction tests for day/month/six-month semantics, minute labels, and unsupported values
- [x] Targeted provider-abstraction tests passing

---

### Step 2: Wire ranges through API, provider, stream, and cache
**Status:** ✅ Complete

> ⚠️ Hydrate: Expand based on whether existing method names can remain compatibility aliases or need deeper renaming after reading the market-data contracts.
>
> Hydrated decision: existing service/provider method names can remain compatibility aliases; normalize `range`/`chartRange` and legacy `timeframe` at edges.

- [x] HTTP and SignalR chart reads use normalized chart ranges
- [x] API compatibility accepts preferred chart range query aliases while retaining legacy `timeframe`
- [x] IBKR historical-bar mapping supports all new ranges and filters returned candles to the requested lookback window
- [x] Timescale cache-aside behavior separates normalized range keys and preserves exact instrument identity filters
- [x] Targeted backend/provider/cache tests added or updated

---

### Step 3: Update frontend chart controls and workflow copy
**Status:** ✅ Complete

- [x] Frontend market-data types/clients/streaming use normalized chart range values
- [x] Chart workflow and selector present the controls as lookback ranges from now
- [x] SignalR fallback, indicators, analysis panel, and exact identity query state preserved
- [x] New frontend chart range shell test added

---

### Step 4: Testing & Verification
**Status:** ✅ Complete

- [x] FULL test suite passing
- [x] Frontend build/checks passing
- [x] Targeted integration/shell tests passing or cleanly skipped where applicable
- [x] All failures fixed
- [x] Backend build passes

---

### Step 5: Documentation & Delivery
**Status:** 🟨 In Progress

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
| 2026-05-04 01:44 | Task started | Runtime V2 lane-runner execution |
| 2026-05-04 01:44 | Step 0 started | Preflight |
| 2026-05-04 01:45 | Step 0 completed | Verified required files, TP-041 archive dependency, and local dotnet/node/npm tooling |
| 2026-05-04 02:03 | Step 1 completed | Added chart range presets, normalized market-data range contracts, and passed provider-abstraction tests |
| 2026-05-04 02:36 | Step 2 completed | Wired normalized ranges through API, SignalR, IBKR, and Timescale; provider/cache targeted tests passed |
| 2026-05-04 02:55 | Step 3 completed | Updated frontend chart range types, client/stream/workflow copy, analysis handoff, and added range shell test |
| 2026-05-04 03:10 | Step 4 completed | Full dotnet tests, frontend build, targeted shell tests, and backend build passed |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
