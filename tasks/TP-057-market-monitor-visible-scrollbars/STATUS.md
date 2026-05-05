# TP-057: Make market monitor table scrollbars visible — Status

**Current Step:** Step 5: Documentation & Delivery
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

### Step 1: Audit current table scroll ownership and overflow paths
**Status:** ✅ Complete

- [x] Inspect table, parent monitor, scroll-area primitive, and CSS overflow behavior
- [x] Verify wide table columns/identity/actions remain required
- [x] Identify final Radix/native/CSS scrollbar strategy
- [x] Record chosen strategy and tradeoffs in discoveries

---

### Step 2: Implement visible vertical and horizontal table scrolling
**Status:** ✅ Complete

- [x] Constrain vertical overflow to an internal table viewport
- [x] Enable horizontal scrolling for the wide table while preserving sticky headers and row actions
- [x] Make scrollbar tracks/thumbs visible when overflow exists
- [x] Preserve full-viewport and responsive behavior without page-level scrolling

---

### Step 3: Add scrollbar validation coverage
**Status:** ✅ Complete

- [x] Create `tests/apphost/frontend-market-monitor-scrollbar-tests.sh`
- [x] Update existing market-monitor/top-chrome/layout validation scripts only if affected
- [x] Ensure validation is deterministic and provider-independent

---

### Step 4: Testing & Verification
**Status:** ✅ Complete

- [x] New scrollbar validation passing
- [x] Market monitor validation passing
- [x] Top chrome/filter density validation passing
- [x] Simplified layout validation passing
- [x] Frontend build passes
- [x] FULL test suite passing
- [x] All failures fixed
- [x] Build passes

---

### Step 5: Documentation & Delivery
**Status:** 🟨 In Progress

- [ ] "Must Update" docs modified
- [ ] README/PLAN verification/current-surface text updated if affected
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
| Wide market-monitor columns remain required: provider, provider symbol id/IBKR conid, market/exchange, currency, asset class, source, score/rank, pin state, and chart/analysis/pin actions preserve exact provider-market identity across search/watchlist/trending handoffs. | Keep wide minimum table width and add horizontal scrolling instead of removing columns or actions. | Step 1 audit: `MarketMonitorTable.tsx`, `MarketMonitorDetailPanel.tsx`, `terminalMarketMonitorWorkflow.ts`, `docs/design/atrade-terminal-ui.md`, `docs/architecture/provider-abstractions.md` |
| Scrollbar strategy chosen: use the shared Radix `ScrollArea` with `type="always"`, render both vertical and horizontal `ScrollBar`s, constrain the market-monitor table root/viewport, and add market-monitor CSS/native fallback styling for visible tracks/thumbs and stable scroll gutters. | Implement in Step 2 without enabling page-level scrolling or removing dense table columns/actions. | Step 1 audit: `scroll-area.tsx`, `MarketMonitorTable.tsx`, `globals.css`, Radix `@radix-ui/react-scroll-area` 1.2.10 types |
| Radix tradeoff: the existing primitive only renders a vertical scrollbar and `type="auto"` can make visibility depend on overflow/interaction; horizontal support must be explicitly mounted and native scrollbar CSS is needed as a scoped browser fallback. | Keep the primitive generally reusable but allow horizontal scrollbar rendering; scope native scrollbar styling to the market-monitor viewport to avoid broad UI changes. | Step 1 audit: `frontend/components/ui/scroll-area.tsx`, `frontend/app/globals.css` |
| Existing market-monitor validation now asserts the new scroll owner/type/slot contract; top-chrome and simplified layout scripts already cover page-level overflow and compact filters and did not need weakening. | Updated only `frontend-terminal-market-monitor-tests.sh`; full validation remains in the new scrollbar script. | Step 3 validation coverage |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 23:32 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 23:32 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
