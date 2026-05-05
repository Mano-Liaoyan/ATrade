# TP-054: Restore stock chart visibility — Status

**Current Step:** Step 2: Make the stock chart visibly render when candle data exists
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
**Status:** ✅ Complete

> ⚠️ Hydrate: Expanded to isolate route/module intent wiring, provider-state truthfulness, chart lifecycle/sizing, and workspace layout/CSS collapse risks before implementation.

- [x] Verify `/symbols/[symbol]` route, market-monitor Chart actions, and terminal chart workflow keep the CHART module and exact identity selected
- [x] Verify market-data client and workspace states distinguish loading/error/provider-unavailable/empty from real candle payloads
- [x] Inspect `TerminalChartWorkspace` and `CandlestickChart` for render path, `lightweight-charts` lifecycle, dimensions, resize, overlays, legend, and cleanup behavior
- [x] Inspect workspace/global CSS for collapsed chart regions, hidden overflow, viewport-height, and compact-filter side effects
- [x] Record the root cause and impacted files in STATUS.md discoveries before implementation

---

### Step 2: Make the stock chart visibly render when candle data exists
**Status:** ✅ Complete

- [x] Give the `lightweight-charts` canvas reliable non-zero dimensions and resize behavior after module/layout changes
- [x] Preserve OHLC legend, volume, SMA overlays, fit-content, crosshair behavior, and cleanup
- [x] Preserve truthful loading/error/empty states with no fake candle data
- [x] Keep stock route and market-monitor Chart actions on the selected CHART module with exact identity metadata when available

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
| Route/module wiring preserves chart identity: `/symbols/[symbol]` defaults to `CHART`, parses exact identity query fields and chart ranges, market-monitor rows build exact `chartHref`/`chartIntent`, and `ATradeTerminalApp.openIntent` activates `CHART` with selected symbol/identity. | Ruled out as the visibility root cause; keep covered in validation. | `frontend/app/symbols/[symbol]/page.tsx`, `frontend/lib/instrumentIdentity.ts`, `frontend/lib/terminalMarketMonitorWorkflow.ts`, `frontend/components/terminal/ATradeTerminalApp.tsx` |
| Provider-unavailable and authentication failures stay truthful through `marketDataClient`/`symbolChartWorkflow` errors, but an empty `CandleSeriesResponse` object currently enters the chart render path because `TerminalChartWorkspace` checks `chart.candles` instead of `chart.view.hasCandleData`. | Fix during Step 2 so empty candle arrays show the explicit empty state without fake data. | `frontend/lib/marketDataClient.ts`, `frontend/lib/symbolChartWorkflow.ts`, `frontend/lib/terminalChartWorkspaceWorkflow.ts`, `frontend/components/terminal/TerminalChartWorkspace.tsx` |
| `CandlestickChart` preserves legend, crosshair, volume, SMA 20/50, fit-content, and `chart.remove()` cleanup, but relies on `autoSize: true` plus CSS-only `min-height`; it never supplies a measured width/height, never guards/deferred-resizes when the container initially reports zero dimensions, and recreates the chart on every data/indicator update. | Root-cause candidate for invisible charts after layout/module changes; fix dimensions/resize lifecycle while preserving overlays. | `frontend/components/CandlestickChart.tsx`, `frontend/app/globals.css` |
| The full-viewport shell intentionally hides page-level overflow, but the chart region itself has no explicit minimum/available height beyond the inner `.chart-container` min-height, and `.terminal-chart-workspace__chart-region` uses `overflow: auto`/`resize: vertical` inside nested grid panels. Compact market-monitor CSS is separate; the layout risk is chart-region/container sizing and internal overflow after the TP-053 viewport cleanup. | Fix CSS in Step 3 so chart workspace, chart region, shell, and container advertise non-collapsing dimensions without reintroducing page-level scrolling. | `frontend/app/globals.css`, `frontend/components/terminal/TerminalWorkspaceLayout.tsx` |
| Root cause: stock chart data can reach the CHART workspace, but the visible canvas depends on implicit CSS sizing and `lightweight-charts` autosize at effect time; after the full-viewport/nested-overflow layout cleanup the container can be measured at zero or not resized/refit when the module becomes visible. A secondary state bug renders empty candle responses as a blank chart instead of the explicit empty state. | Implement measured non-zero chart dimensions/resizing, refit after resize/data changes, explicit empty-array state, and CSS/validation coverage. | `frontend/components/CandlestickChart.tsx`, `frontend/components/terminal/TerminalChartWorkspace.tsx`, `frontend/app/globals.css`, `tests/apphost/*chart*`, `tests/apphost/frontend-simplified-workspace-layout-tests.sh` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 18:38 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 18:38 | Step 0 started | Preflight |
| 2026-05-05 18:45 | Step 1 hydrated | Expanded diagnosis outcomes before implementation |
| 2026-05-05 19:00 | Step 2 started | Implementing measured chart sizing/rendering fixes |

---

## Blockers

*None*

---

## Notes

- Step 2 sizing check: `cd frontend && npx tsc --noEmit --pretty false --ignoreDeprecations 6.0` passed after adding explicit chart measurement and ResizeObserver/window resize handling. `npm run lint -- --file components/CandlestickChart.tsx` was attempted first, but this frontend package has no lint script.
- Step 2 route/identity check: `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh` passed after preserving CHART module/exact identity behavior.

