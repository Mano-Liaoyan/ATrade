# TP-043: Redesign workspace navigation with a terminal-style shell — Status

**Current Step:** Step 1: Create reusable workspace shell primitives
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

### Step 1: Create reusable workspace shell primitives
**Status:** 🟨 In Progress

> ⚠️ Hydrate: Expand component-level details after inspecting current home/chart component structure and CSS constraints.

- [ ] Shared shell primitives expose semantic header, command, navigation, main, and context landmarks without new UI dependencies
- [ ] Shell primitives accept home/chart metadata, actions, anchors, and context cards while keeping workflow/client orchestration outside them
- [ ] Terminal-style CSS system added with dense panels, responsive collapse, keyboard focus states, and no proprietary terminal assets
- [ ] Paper-only/provider/exact-identity messaging remains explicit in shell affordances with no broker order actions or fake market data
- [ ] New terminal shell UI test covers component source markers, SSR-visible landmarks, focusable navigation controls, and no Bloomberg/proprietary assets

---

### Step 2: Refactor the home workspace into navigable panels
**Status:** ⬜ Not Started

- [ ] Home route and trading workspace use the new shell and clear navigation landmarks
- [ ] Workflow/client boundaries preserved in rendering components
- [ ] Search, trending, and watchlist panels fit the shell without behavior regression
- [ ] Targeted home workspace checks passing

---

### Step 3: Refactor the chart workspace into the same shell
**Status:** ⬜ Not Started

- [ ] Chart workspace uses the shared terminal-style shell/navigation model
- [ ] Chart range controls, stream state, source metadata, and fallback notes remain visible on desktop and mobile
- [ ] Broker status, analysis, candlestick, indicator, and SignalR fallback behavior preserved
- [ ] Existing frontend integration assertions updated only for intentional marker moves

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Frontend build/checks passing
- [ ] Integration/shell tests passing or cleanly skipped where applicable
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
| 2026-05-04 06:27 | Task started | Runtime V2 lane-runner execution |
| 2026-05-04 06:27 | Step 0 started | Preflight |
| 2026-05-04 06:28 | Step 0 completed | Required paths verified; TP-042 .DONE and local toolchain present |
| 2026-05-04 06:28 | Step 1 started | Reusable workspace shell primitives |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
