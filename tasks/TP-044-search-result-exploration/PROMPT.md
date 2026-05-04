# Task: TP-044 - Make stock search results easier to explore

**Created:** 2026-05-04
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This task stays inside the frontend search workflow/components, CSS, and shell tests while preserving backend API contracts. It adapts existing workflow patterns to present search results in a capped, grouped, filterable format, so plan review is enough.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-044-search-result-exploration/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Redesign the stock search experience so users are not overwhelmed by a long flat result list. The search UI should help users quickly identify the best match, understand provider/market identity, narrow by market/currency/asset metadata, and intentionally reveal more results only when requested. This complements the terminal-style shell by making search behave more like an industry terminal command/search panel: concise by default, information-dense, keyboard-friendly, and explicit about exact IBKR/iBeam instruments.

## Dependencies

- **Task:** TP-043 (terminal-style workspace shell must exist so search exploration fits the redesigned navigation model)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — frontend search/watchlist/chart behavior and localStorage guardrails
- `docs/architecture/modules.md` — frontend workflow module responsibilities
- `docs/architecture/provider-abstractions.md` — provider-neutral search result identity metadata

## Environment

- **Workspace:** `frontend/`
- **Services required:** None for source/build checks; frontend/API shell tests must skip cleanly when optional local runtimes are unavailable

## File Scope

- `frontend/components/SymbolSearch.tsx`
- `frontend/components/SymbolSearchResults.tsx` (new if useful)
- `frontend/components/SymbolSearchFilters.tsx` (new if useful)
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/app/globals.css`
- `frontend/lib/symbolSearchWorkflow.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/types/marketData.ts`
- `tests/apphost/frontend-symbol-search-exploration-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Model bounded, ranked search result state

- [ ] Update `frontend/lib/symbolSearchWorkflow.ts` to derive a result view model with best/exact matches first, visible-result limits, available exchange/currency filters, selected filters, and a deliberate `show more` action
- [ ] Keep backend search behind `searchSymbols()` and pass explicit `limit` values; do not fetch an unbounded result list or add direct provider access from the browser
- [ ] Preserve provider/authentication error formatting, minimum query validation, debounce behavior, and exact instrument identity payloads for pin/chart actions
- [ ] Add source-level assertions in a new shell test for capped defaults, filtering state, and no unbounded search fetches

**Artifacts:**
- `frontend/lib/symbolSearchWorkflow.ts` (modified)
- `frontend/lib/marketDataClient.ts` (modified only if request options need clearer naming)
- `frontend/types/marketData.ts` (modified if search view-model types are exported)
- `tests/apphost/frontend-symbol-search-exploration-tests.sh` (new)

### Step 2: Implement a concise, explorable search UI

- [ ] Update `SymbolSearch.tsx` and optional extracted `SymbolSearchResults.tsx` / `SymbolSearchFilters.tsx` components so the default result panel shows a short, ranked list with a prominent best match and an explicit result count
- [ ] Add market/currency/asset metadata filters or chips using existing provider-neutral fields (`exchange`, `currency`, `assetClass`, `provider`, `providerSymbolId`) without requiring backend changes
- [ ] Add `show more` / `show less` affordances and keyboard/focus-friendly controls so users can explore additional matches intentionally
- [ ] Keep pin buttons, chart links, market logos, accessible result labels, and compact chart-page search behavior intact

**Artifacts:**
- `frontend/components/SymbolSearch.tsx` (modified)
- `frontend/components/SymbolSearchResults.tsx` (new if useful)
- `frontend/components/SymbolSearchFilters.tsx` (new if useful)
- `frontend/app/globals.css` (modified)

### Step 3: Integrate search exploration in the workspace shell

- [ ] Update `TradingWorkspace.tsx` and `SymbolChartView.tsx` only as needed so search panels use the new concise/explorable UI in both home and chart contexts
- [ ] Ensure long IBKR result sets do not push watchlist/trending/chart context off-screen on desktop or mobile in the terminal-style shell
- [ ] Update existing frontend shell tests only where user-facing markers intentionally move
- [ ] Run targeted frontend build/shell tests

**Artifacts:**
- `frontend/components/TradingWorkspace.tsx` (modified if needed)
- `frontend/components/SymbolChartView.tsx` (modified if needed)
- `tests/apphost/frontend-symbol-search-exploration-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified if needed)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run integration/shell tests: `bash tests/apphost/frontend-symbol-search-exploration-tests.sh`, `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, and `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — search UX now uses bounded/ranked/explorable result groups and exact provider-market identity metadata
- `docs/architecture/modules.md` — frontend workflow/component responsibilities if new search result/filter components or workflow view models are introduced
- `README.md` — verification entry point list if `frontend-symbol-search-exploration-tests.sh` is added

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if frontend interpretation of search result identity/source metadata changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Search result panel is concise by default and no longer presents a long flat list
- [ ] Users can intentionally explore more matches and narrow results by provider-neutral market metadata
- [ ] Pin result and open chart actions still preserve exact instrument identity
- [ ] Frontend still talks only to `ATrade.Api` and does not add direct provider/database access

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-044): complete Step N — description`
- **Bug fixes:** `fix(TP-044): description`
- **Tests:** `test(TP-044): description`
- **Hydration:** `hydrate: TP-044 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Fetch or render unbounded search result lists in the browser
- Hide exact provider/market/currency/asset-class identity metadata from pin/chart actions
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
