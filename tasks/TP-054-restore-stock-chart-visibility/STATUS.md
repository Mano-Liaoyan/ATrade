# TP-054: Restore stock chart visibility — Status

**Current Step:** Step 1: Reproduce and pin down the chart visibility failure
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 2
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

### Step 1: Reproduce and pin down the chart visibility failure
**Status:** 🟨 In Progress

> ⚠️ Hydrate: Expanded to isolate route/module intent wiring, provider-state truthfulness, chart lifecycle/sizing, and workspace layout/CSS collapse risks before implementation.

- [ ] Verify `/symbols/[symbol]` route, market-monitor Chart actions, and terminal chart workflow keep the CHART module and exact identity selected
- [ ] Verify market-data client and workspace states distinguish loading/error/provider-unavailable/empty from real candle payloads
- [ ] Inspect `TerminalChartWorkspace` and `CandlestickChart` for render path, `lightweight-charts` lifecycle, dimensions, resize, overlays, legend, and cleanup behavior
- [ ] Inspect workspace/global CSS for collapsed chart regions, hidden overflow, viewport-height, and compact-filter side effects
- [ ] Record the root cause and impacted files in STATUS.md discoveries before implementation

---

### Step 2: Make the stock chart visibly render when candle data exists
**Status:** ⬜ Not Started

- [ ] Give the `lightweight-charts` canvas reliable non-zero dimensions and resize behavior after module/layout changes
- [ ] Preserve OHLC legend, volume, SMA overlays, fit-content, crosshair behavior, and cleanup
- [ ] Preserve truthful loading/error/empty states with no fake candle data
- [ ] Keep stock route and market-monitor Chart actions on the selected CHART module with exact identity metadata when available

---

### Step 3: Protect chart visibility in CSS and validation
**Status:** ⬜ Not Started

- [ ] Prevent chart region/container collapse or hidden overflow in `frontend/app/globals.css`
- [ ] Create `tests/apphost/frontend-stock-chart-visibility-tests.sh`
- [ ] Update existing chart/layout validation scripts for the fixed chart contract

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] New chart visibility validation passing
- [ ] Chart/analysis validation passing
- [ ] Chart range preset validation passing
- [ ] Final layout validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] README/PLAN verification/current-surface text updated if affected
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged, including root cause and local-provider verification availability

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
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 18:38 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 18:38 | Step 0 started | Preflight |
| 2026-05-05 18:45 | Step 1 hydrated | Expanded diagnosis outcomes before implementation |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
