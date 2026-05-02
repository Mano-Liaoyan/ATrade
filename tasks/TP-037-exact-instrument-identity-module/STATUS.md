# TP-037: Deepen the Exact Instrument Identity module — Status

**Current Step:** Step 1: Establish Exact Instrument Identity as the backend-owned interface
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

### Step 1: Establish Exact Instrument Identity as the backend-owned interface
**Status:** ✅ Complete

> ⚠️ Hydrate: Expand checkboxes when entering this step based on the chosen module location and callers found during source inspection.

- [x] `ATrade.MarketData` exact identity module owns normalization/defaulting/encoding/equality and provider/market projection
- [x] `ATrade.Workspaces` delegates instrument key construction to the backend identity module while preserving existing `instrumentKey` / `pinKey` payloads
- [x] New identity contract tests cover same-symbol/different-market identities, manual legacy identities, and projected market-data identities
- [x] Targeted identity/workspace tests passing

---

### Step 2: Preserve identity through market-data and Timescale flows
**Status:** ⬜ Not Started

- [ ] Provider-backed identity carried where available for search, trending, candles, indicators, and latest updates
- [ ] Timescale models/queries preserve provider/market metadata where available
- [ ] Bare-symbol legacy reads remain compatible
- [ ] Targeted market-data/provider/Timescale tests passing

---

### Step 3: Make frontend provisional identity use one adapter
**Status:** ⬜ Not Started

- [ ] TypeScript provisional identity/key adapter centralized
- [ ] Backend-owned persisted keys remain authoritative after watchlist responses
- [ ] Legacy `/symbols/{symbol}` behavior preserved while exact handoff is documented if added
- [ ] Targeted frontend checks passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Integration tests passing or cleanly skipped where applicable
- [ ] All failures fixed
- [ ] Backend and frontend builds pass

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
| 2026-05-02 14:17 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 14:17 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
