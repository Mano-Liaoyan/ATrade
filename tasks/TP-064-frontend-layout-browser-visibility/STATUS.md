# TP-064: Frontend layout and browser visibility guardrails — Status

**Current Step:** Step 5: Testing & Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-07
**Review Level:** 1
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

### Step 1: Store the desktop browser visibility rule in project memory
**Status:** ✅ Complete

- [x] Add durable desktop browser/no-clipping/visible-scrollbar guardrail to `AGENTS.md` and `tasks/CONTEXT.md`
- [x] Update `docs/design/atrade-terminal-ui.md` with Safari/Firefox/Chrome/Edge visibility and scroll ownership contract
- [x] Check README/PLAN/paper workspace docs for stale wording and update only if affected

---

### Step 2: Fix terminal shell, rail, and workspace scroll ownership
**Status:** ✅ Complete

- [x] Make the module rail fully reachable without clipping enabled or visible-disabled module buttons
- [x] Make the primary workspace own visible internal scrolling while preserving page-level `overflow: hidden`
- [x] Add reusable visible/custom scrollbar styling for desktop Safari, Firefox, Chrome, and Edge
- [x] Preserve no-command/no-top-chrome/no-layout-persistence guardrails

---

### Step 3: Fix module-owned panel visibility
**Status:** ✅ Complete

- [x] Make `MarketMonitorDetailPanel` content fully reachable without viewport-edge clipping
- [x] Ensure Analysis, Backtest, Status, Help, Chart, and disabled-module surfaces remain reachable through module-owned overflow/reflow
- [x] Preserve visible market-monitor table vertical/horizontal scrollbars, sticky headers, identity columns, and action columns
- [x] Avoid mobile-specific optimization beyond existing responsive fallbacks

---

### Step 4: Add layout/browser visibility validation
**Status:** ✅ Complete

- [x] Create `tests/apphost/frontend-terminal-layout-visibility-tests.sh`
- [x] Update existing shell/scrollbar/rail tests only where shared layout changes require it
- [x] Keep validation source/static or lightweight Next.js dev without real provider credentials

---

### Step 5: Testing & Verification
**Status:** 🟨 In Progress

- [ ] Layout visibility validation passing
- [ ] Market-monitor scrollbar validation passing
- [ ] Simplified workspace validation passing
- [ ] Rail icon/collapse validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Verification inventory updated if needed
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
| 2026-05-07 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-07 01:10 | Task started | Runtime V2 lane-runner execution |
| 2026-05-07 01:10 | Step 0 started | Preflight |
| 2026-05-07 01:11 | Step 0 completed | Required files verified; frontend dependencies installed with npm ci; toolchain available |
| 2026-05-07 01:11 | Step 1 started | Project memory and UI documentation guardrail |
| 2026-05-07 01:13 | Step 1 completed | Browser visibility guardrail stored in agent/context/design/current docs |
| 2026-05-07 01:13 | Step 2 started | Terminal shell, rail, and primary workspace scroll ownership |
| 2026-05-07 01:20 | Step 2 completed | Rail and primary workspace own native/custom styled scrolling; no-command guardrail tests pass |
| 2026-05-07 01:20 | Step 3 started | Module-owned panel visibility and overflow reachability |
| 2026-05-07 01:28 | Step 3 completed | Detail, chart, analysis, backtest, status, help, and disabled module surfaces expose reachable module-owned overflow/reflow |
| 2026-05-07 01:28 | Step 4 started | Layout/browser visibility validation script and impacted test updates |
| 2026-05-07 01:36 | Step 4 completed | Added static layout visibility validation and refreshed rail/scrollbar/simplified shell assertions |
| 2026-05-07 01:36 | Step 5 started | Required verification commands |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
