# TP-064: Frontend layout and browser visibility guardrails — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-07
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Store the desktop browser visibility rule in project memory
**Status:** ⬜ Not Started

- [ ] Add durable desktop browser/no-clipping/visible-scrollbar guardrail to `AGENTS.md` and `tasks/CONTEXT.md`
- [ ] Update `docs/design/atrade-terminal-ui.md` with Safari/Firefox/Chrome/Edge visibility and scroll ownership contract
- [ ] Check README/PLAN/paper workspace docs for stale wording and update only if affected

---

### Step 2: Fix terminal shell, rail, and workspace scroll ownership
**Status:** ⬜ Not Started

- [ ] Make the module rail fully reachable without clipping enabled or visible-disabled module buttons
- [ ] Make the primary workspace own visible internal scrolling while preserving page-level `overflow: hidden`
- [ ] Add reusable visible/custom scrollbar styling for desktop Safari, Firefox, Chrome, and Edge
- [ ] Preserve no-command/no-top-chrome/no-layout-persistence guardrails

---

### Step 3: Fix module-owned panel visibility
**Status:** ⬜ Not Started

- [ ] Make `MarketMonitorDetailPanel` content fully reachable without viewport-edge clipping
- [ ] Ensure Analysis, Backtest, Status, Help, Chart, and disabled-module surfaces remain reachable through module-owned overflow/reflow
- [ ] Preserve visible market-monitor table vertical/horizontal scrollbars, sticky headers, identity columns, and action columns
- [ ] Avoid mobile-specific optimization beyond existing responsive fallbacks

---

### Step 4: Add layout/browser visibility validation
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-terminal-layout-visibility-tests.sh`
- [ ] Update existing shell/scrollbar/rail tests only where shared layout changes require it
- [ ] Keep validation source/static or lightweight Next.js dev without real provider credentials

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
