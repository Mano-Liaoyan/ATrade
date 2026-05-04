# TP-049: Rebuild chart and analysis as terminal workspaces — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-04
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

### Step 1: Preserve chart workflow contracts behind terminal view models
**Status:** ⬜ Not Started

- [ ] Preserve chart range, identity, candle/indicator, SignalR, and HTTP fallback behavior
- [ ] Wire CHART and monitor chart actions with exact identity handoff
- [ ] Wire ANALYSIS actions to provider-neutral analysis behavior
- [ ] Add assertions against direct provider/database/order access

---

### Step 2: Build the terminal chart workspace
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand based on which existing low-level chart components remain useful.

- [ ] Create terminal chart workspace and instrument header
- [ ] Adapt chart/indicator regions for resizable terminal layout
- [ ] Preserve supported lookback range list and copy
- [ ] Retire old page-level chart shell components once equivalent exists

---

### Step 3: Build terminal analysis and provider diagnostics panels
**Status:** ⬜ Not Started

- [ ] Create terminal analysis workspace with explicit no-engine/unavailable states
- [ ] Create provider diagnostics without order/credential controls
- [ ] Replace or retire old AnalysisPanel/BrokerPaperStatus usage
- [ ] Keep PORTFOLIO/ORDERS disabled and no order-entry UI

---

### Step 4: Integrate symbol route and command flows
**Status:** ⬜ Not Started

- [ ] Route direct symbol URLs through the terminal frame/chart module
- [ ] Converge CHART/ANALYSIS/monitor/direct route behavior
- [ ] Update chart/range/search/analysis tests for terminal markers
- [ ] Run targeted tests and frontend build

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Terminal chart/analysis validation passing
- [ ] Chart range validation passing
- [ ] Frontend workspace validation passing
- [ ] Analysis shell validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
