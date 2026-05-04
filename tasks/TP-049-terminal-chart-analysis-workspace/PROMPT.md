# Task: TP-049 - Rebuild chart and analysis as terminal workspaces

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This replaces the chart route/module rendering and analysis presentation with a multi-panel terminal workspace while preserving chart range semantics, SignalR/HTTP fallback, provider metadata, and analysis API contracts. It is frontend-heavy with broad visual impact and new layout behavior, but does not change auth, persistence, or backend provider contracts.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-049-terminal-chart-analysis-workspace/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Replace the existing symbol chart page and analysis panel with a richer Fincept-style terminal chart workspace: instrument header, resizable chart/indicator/analysis/provider regions, range controls, provider/source diagnostics, market monitor handoff, and `CHART <symbol>` / `ANALYSIS <symbol>` command integration. The new workspace must preserve ATrade's current chart, indicator, SignalR fallback, exact identity, and analysis-engine behavior while feeling like a terminal module rather than a standalone page.

## Dependencies

- **Task:** TP-048 (terminal market monitor and exact instrument handoff must be integrated)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — terminal chart/analysis workspace and visual guardrails
- `docs/architecture/paper-trading-workspace.md` — chart range, SignalR fallback, provider state, analysis, and paper-only contracts
- `docs/architecture/analysis-engines.md` — provider-neutral analysis engine discovery/run behavior
- `docs/architecture/provider-abstractions.md` — market-data source and exact identity payload behavior
- `docs/architecture/modules.md` — frontend workflow/component responsibilities

## Environment

- **Workspace:** `frontend/`
- **Services required:** None for source/build checks; real IBKR/iBeam or LEAN checks must skip cleanly unless local ignored `.env` runtime is configured

## File Scope

- `frontend/components/terminal/TerminalChartWorkspace.tsx` (new)
- `frontend/components/terminal/TerminalInstrumentHeader.tsx` (new)
- `frontend/components/terminal/TerminalIndicatorGrid.tsx` (new)
- `frontend/components/terminal/TerminalAnalysisWorkspace.tsx` (new)
- `frontend/components/terminal/TerminalProviderDiagnostics.tsx` (new)
- `frontend/components/SymbolChartView.tsx` (delete, retire, or wrap if replaced)
- `frontend/components/CandlestickChart.tsx`
- `frontend/components/IndicatorPanel.tsx` (delete, retire, or wrap if replaced)
- `frontend/components/AnalysisPanel.tsx` (delete, retire, or wrap if replaced)
- `frontend/components/BrokerPaperStatus.tsx` (delete, retire, or wrap if replaced)
- `frontend/components/TimeframeSelector.tsx` (delete, retire, or wrap if replaced)
- `frontend/lib/symbolChartWorkflow.ts`
- `frontend/lib/analysisClient.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/marketDataStream.ts`
- `frontend/lib/terminalCommandRegistry.ts`
- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/app/symbols/[symbol]/page.tsx`
- `frontend/app/globals.css`
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (new)
- `tests/apphost/frontend-chart-range-preset-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/analysis-engine-contract-tests.sh`
- `tests/apphost/lean-analysis-engine-tests.sh`
- `README.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/analysis-engines.md`
- `docs/architecture/modules.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Preserve chart workflow contracts behind terminal view models

- [ ] Keep or adapt `symbolChartWorkflow` so normalized chart range values, exact identity query metadata, candle/indicator HTTP reads, SignalR subscription state, stream update application, and HTTP polling fallback remain intact
- [ ] Ensure `CHART <symbol>` and market-monitor chart actions open the chart module for that symbol; exact identity metadata from search/trending/watchlist must be preserved when available
- [ ] Ensure `ANALYSIS <symbol>` opens/focuses analysis for that symbol using provider-neutral `analysisClient` behavior with explicit no-engine/unavailable states
- [ ] Add source assertions that no chart/analysis module introduces direct browser access to IBKR/iBeam, LEAN, databases, or broker order routes

**Artifacts:**
- `frontend/lib/symbolChartWorkflow.ts` (modified if needed)
- `frontend/lib/terminalCommandRegistry.ts` (modified)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (new)

### Step 2: Build the terminal chart workspace

- [ ] Create `TerminalChartWorkspace` and `TerminalInstrumentHeader` with dense symbol/source/range/stream/identity metadata and terminal-styled range controls
- [ ] Create or adapt chart and indicator regions so candlesticks, indicator summaries, loading/error/empty states, source labels, and fallback notes fit the resizable terminal layout
- [ ] Preserve the supported range list (`1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, `all`) and user copy that treats them as lookbacks from now
- [ ] Keep `CandlestickChart` reusable if useful, but remove/retire old page-level chart shell components once equivalent terminal modules exist

**Artifacts:**
- `frontend/components/terminal/TerminalChartWorkspace.tsx` (new)
- `frontend/components/terminal/TerminalInstrumentHeader.tsx` (new)
- `frontend/components/terminal/TerminalIndicatorGrid.tsx` (new)
- `frontend/components/CandlestickChart.tsx` (modified if needed)
- `frontend/components/IndicatorPanel.tsx` (deleted, retired, or wrapped)
- `frontend/components/TimeframeSelector.tsx` (deleted, retired, or wrapped)
- `frontend/app/globals.css` (modified)

### Step 3: Build terminal analysis and provider diagnostics panels

- [ ] Create `TerminalAnalysisWorkspace` that uses existing analysis discovery/run behavior, makes no-engine/unavailable states explicit, and keeps the no-order-routing guardrail visible
- [ ] Create `TerminalProviderDiagnostics` that presents broker/IBKR/iBeam/data-source/SignalR states as diagnostics, not as order controls or credentials UI
- [ ] Replace or retire `AnalysisPanel` and `BrokerPaperStatus` usage from active routes once terminal equivalents exist
- [ ] Ensure disabled `PORTFOLIO` and `ORDERS` modules remain placeholders and no simulated order-entry submit UI is added

**Artifacts:**
- `frontend/components/terminal/TerminalAnalysisWorkspace.tsx` (new)
- `frontend/components/terminal/TerminalProviderDiagnostics.tsx` (new)
- `frontend/components/AnalysisPanel.tsx` (deleted, retired, or wrapped)
- `frontend/components/BrokerPaperStatus.tsx` (deleted, retired, or wrapped)

### Step 4: Integrate symbol route and command flows

- [ ] Update `frontend/app/symbols/[symbol]/page.tsx` so direct symbol URLs hydrate the terminal frame and chart module instead of rendering a standalone old workspace page
- [ ] Ensure `CHART <symbol>`, `ANALYSIS <symbol>`, market monitor row actions, and direct `/symbols/[symbol]` navigation all converge on the same terminal chart/analysis workspace behavior
- [ ] Update chart/range/search/analysis tests for new terminal markers without weakening chart range or provider/analysis safety assertions
- [ ] Run targeted chart/analysis tests and frontend build

**Artifacts:**
- `frontend/app/symbols/[symbol]/page.tsx` (modified)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `tests/apphost/frontend-chart-range-preset-tests.sh` (modified if needed)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified if needed)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (new)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run terminal chart/analysis validation: `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run chart range validation: `bash tests/apphost/frontend-chart-range-preset-tests.sh`
- [ ] Run frontend workspace validation: `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run analysis shell validation: `bash tests/apphost/analysis-engine-contract-tests.sh` and `bash tests/apphost/lean-analysis-engine-tests.sh`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — describe terminal chart workspace, chart/analysis command flows, provider diagnostics, and preserved range/fallback behavior
- `docs/architecture/analysis-engines.md` — update frontend terminal analysis panel behavior if user-facing discovery/run states change
- `docs/architecture/modules.md` — record terminal chart/analysis component ownership and retired old components
- `README.md` — add `tests/apphost/frontend-terminal-chart-analysis-tests.sh` to verification entry points once created

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update only if approved chart/analysis interaction refinements are discovered
- `docs/architecture/provider-abstractions.md` — update only if source/identity label interpretation changes, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Chart and analysis live in terminal modules with resizable chart/indicator/analysis/provider regions
- [ ] `CHART <symbol>`, `ANALYSIS <symbol>`, market-monitor actions, and direct symbol URLs converge on the same terminal workspace
- [ ] Chart range lookback controls, SignalR-to-HTTP fallback, source metadata, exact identity, and analysis no-engine/unavailable states are preserved
- [ ] No order-entry, simulated-submit, fake provider data, or direct browser provider/database access is introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-049): complete Step N — description`
- **Bug fixes:** `fix(TP-049): description`
- **Tests:** `test(TP-049): description`
- **Hydration:** `hydrate: TP-049 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Change backend market-data, SignalR, analysis, or provider contracts unless a test proves a frontend-only route is impossible
- Copy FinceptTerminal/Bloomberg source, assets, screenshots, branding, or pixel-identical proprietary layouts
- Add drawing tools, multi-chart synchronization, saved chart templates, or full advanced charting beyond the specified multi-panel workspace
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement, simulated order-entry UI, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
