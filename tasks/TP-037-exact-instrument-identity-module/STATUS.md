# TP-037: Deepen the Exact Instrument Identity module — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-02
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Establish Exact Instrument Identity as the backend-owned interface
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand checkboxes when entering this step based on the chosen module location and callers found during source inspection.

- [ ] Backend identity module owns normalization/defaulting/encoding/equality
- [ ] Existing `instrumentKey` / `pinKey` payload compatibility preserved
- [ ] New identity contract test file added
- [ ] Targeted identity/workspace tests passing

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
