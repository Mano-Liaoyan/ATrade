# TP-042: Correct chart range presets — Status

**Current Step:** Step 1: Model chart ranges as lookbacks from now
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
**Status:** 🟨 In Progress

- [ ] Create chart range preset helper with supported normalized values and lookback boundaries
- [ ] Update market-data models/contracts to normalize requested ranges while retaining safe compatibility for legacy `timeframe` callers
- [ ] Add provider-abstraction tests for day/month/six-month semantics, minute labels, and unsupported values
- [ ] Targeted provider-abstraction tests passing

---

### Step 2: Wire ranges through API, provider, stream, and cache
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand based on whether existing method names can remain compatibility aliases or need deeper renaming after reading the market-data contracts.

- [ ] HTTP and SignalR chart reads use normalized chart ranges
- [ ] IBKR historical-bar mapping supports all new ranges and filters returned candles to the requested lookback window
- [ ] Timescale cache-aside behavior separates normalized range keys and preserves exact instrument identity filters
- [ ] Targeted backend/provider/cache tests added or updated

---

### Step 3: Update frontend chart controls and workflow copy
**Status:** ⬜ Not Started

- [ ] Frontend market-data types/clients/streaming use normalized chart range values
- [ ] Chart workflow and selector present the controls as lookback ranges from now
- [ ] SignalR fallback, indicators, analysis panel, and exact identity query state preserved
- [ ] New frontend chart range shell test added

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Frontend build/checks passing
- [ ] Targeted integration/shell tests passing or cleanly skipped where applicable
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
| 2026-05-04 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-04 01:44 | Task started | Runtime V2 lane-runner execution |
| 2026-05-04 01:44 | Step 0 started | Preflight |
| 2026-05-04 01:45 | Step 0 completed | Verified required files, TP-041 archive dependency, and local dotnet/node/npm tooling |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
