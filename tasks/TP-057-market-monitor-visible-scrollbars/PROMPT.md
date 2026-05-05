# Task: TP-057 - Make market monitor table scrollbars visible

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task changes the dense market monitor table container, shared scroll-area primitive/CSS, validation, and docs. It is frontend-only and reversible, but it affects a core data table used by HOME/SEARCH/WATCHLIST and must preserve layout, accessibility, and exact identity actions.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-057-market-monitor-visible-scrollbars/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make the market monitor table explicitly scrollable both vertically and horizontally with visible scrollbars. The table must own its scroll region inside the fixed full-viewport app frame, keep sticky headers and dense row/action behavior, show horizontal overflow for wide provider/identity/action columns, and expose visible scrollbar tracks/thumbs instead of relying on hidden page-level overflow or hover-only affordances.

## Dependencies

- **Task:** TP-056 (rail icon/collapse changes should land before final shared CSS/layout validation for the table)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active UI authority for table scroll ownership, full-viewport layout, and visual system
- `docs/architecture/paper-trading-workspace.md` — market monitor workflow/API-boundary and safety contract
- `docs/architecture/provider-abstractions.md` — exact identity/source/provider-unavailable semantics if row behavior changes
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and follow-up direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks. Automated validation must not require live IBKR/iBeam credentials or provider data.

## File Scope

- `frontend/components/terminal/MarketMonitorTable.tsx`
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (check if table region sizing needs parent changes)
- `frontend/components/ui/scroll-area.tsx`
- `frontend/app/globals.css`
- `tests/apphost/frontend-market-monitor-scrollbar-tests.sh` (new)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (check/update if affected)
- `tests/apphost/frontend-top-chrome-filter-density-tests.sh` (check/update if affected)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md` (check if affected)
- `docs/architecture/provider-abstractions.md` (check if affected)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Audit current table scroll ownership and overflow paths

- [ ] Inspect `MarketMonitorTable`, `TerminalMarketMonitor`, `ScrollArea`, and relevant CSS to determine why vertical/horizontal scrollbars are not sufficiently visible or reliable
- [ ] Verify the table still needs a wide minimum width for provider, provider ID, market, currency, asset class, source, score, pin, and actions columns
- [ ] Identify whether fixes belong in the shared `ScrollArea` primitive, the market-monitor-specific shell, native CSS scrollbar styling, or a combination
- [ ] Record the chosen scroll strategy and any browser/Radix tradeoffs in STATUS.md discoveries before implementation

**Artifacts:**
- `STATUS.md` (modified discoveries)
- `frontend/components/terminal/MarketMonitorTable.tsx` (read/planned)
- `frontend/components/ui/scroll-area.tsx` (read/planned)
- `frontend/app/globals.css` (read/planned)

### Step 2: Implement visible vertical and horizontal table scrolling

- [ ] Update the market monitor table region so vertical overflow is constrained to an internal table viewport and lower rows are reachable without page-level scrolling
- [ ] Update horizontal overflow so the wide table scrolls left/right with a visible horizontal scrollbar while preserving sticky headers, row selection, sorting, pin/chart/analysis actions, and exact identity columns
- [ ] Ensure scrollbar tracks/thumbs are visible when overflow exists (for example Radix `type="always"`, stable scrollbar gutter, explicit `ScrollBar` styling, native fallback CSS, or equivalent)
- [ ] Preserve responsive behavior: the full app remains `overflow: hidden`, the primary workspace/module-owned regions scroll internally, and mobile/laptop breakpoints do not hide the table controls

**Artifacts:**
- `frontend/components/terminal/MarketMonitorTable.tsx` (modified)
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (modified if parent sizing is needed)
- `frontend/components/ui/scroll-area.tsx` (modified if shared scrollbar visibility/styling is needed)
- `frontend/app/globals.css` (modified)

### Step 3: Add scrollbar validation coverage

- [ ] Create `tests/apphost/frontend-market-monitor-scrollbar-tests.sh` to validate the scroll contract: table uses an internal scroll viewport, vertical and horizontal scrollbars are rendered/visible by source contract, table keeps a wide min-width, sticky headers remain, no page-level scroll is introduced, and exact identity/action columns remain present
- [ ] Update existing market-monitor/top-chrome/layout validation scripts only where needed so they enforce visible scrollbars without weakening compact filters, dense rows, no-detail-panel, no-top-chrome, no-command, or no-order assertions
- [ ] Ensure validation is deterministic and does not require live provider data

**Artifacts:**
- `tests/apphost/frontend-market-monitor-scrollbar-tests.sh` (new)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (modified if needed)
- `tests/apphost/frontend-top-chrome-filter-density-tests.sh` (modified if needed)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run new scrollbar validation: `bash tests/apphost/frontend-market-monitor-scrollbar-tests.sh`
- [ ] Run market monitor validation: `bash tests/apphost/frontend-terminal-market-monitor-tests.sh`
- [ ] Run top chrome/filter density validation: `bash tests/apphost/frontend-top-chrome-filter-density-tests.sh`
- [ ] Run simplified layout validation: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe the visible vertical/horizontal market-monitor table scroll contract
- [ ] Update README/PLAN verification inventory or current frontend surface text if the new scrollbar validation script should be listed
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including the final scroll strategy and provider-verification status

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — table scroll ownership, visible scrollbar behavior, and responsive/full-viewport implications
- `README.md` — verification entry-point list/current frontend surface if adding the new validation script or changing table behavior summary
- `PLAN.md` — active/follow-up direction if affected

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if frontend market-monitor/runtime contract text changes
- `docs/architecture/provider-abstractions.md` — update only if exact identity/source/provider-state handling changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Market monitor rows scroll vertically inside the table viewport with a visible vertical scrollbar when rows overflow
- [ ] Wide market monitor columns scroll horizontally with a visible horizontal scrollbar when columns overflow
- [ ] Sticky headers, sorting, selected rows, pin/chart/analysis actions, source/status chips, and exact provider identity columns remain usable
- [ ] The main page/body remains non-scrolling and no retired chrome or command/order-entry surfaces are reintroduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-057): complete Step N — description`
- **Bug fixes:** `fix(TP-057): description`
- **Tests:** `test(TP-057): description`
- **Hydration:** `hydrate: TP-057 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Solve table overflow by enabling page-level scrolling on `html`, `body`, `.atrade-terminal-app`, or retired layout regions
- Remove dense table columns, exact provider identity, pin/chart/analysis actions, sticky headers, sorting, filters, or truthful provider-state copy to make the table fit
- Copy FinceptTerminal/Bloomberg source, table styles, screenshots, assets, names, trademarks, or branding
- Reintroduce the removed command system, old shell/list route wrappers, context/monitor/footer chrome, top app brand header, or visible global safety strip
- Add fake market data, fake chart candles, placeholder news/research/AI content, or invented provider responses
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, LEAN, or any provider runtime
- Add real order placement, simulated order-entry UI, buy/sell buttons, order tickets, previews, confirmations, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
