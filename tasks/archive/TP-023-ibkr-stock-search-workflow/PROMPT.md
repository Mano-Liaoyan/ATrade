# Task: TP-023 - Add IBKR stock search and pin-any-symbol workflow

**Created:** 2026-04-29
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This adds a user-facing search path over IBKR's instrument universe and connects it to the Postgres-backed watchlist. It spans backend search endpoints, provider mapping, frontend search UX, persistence metadata, tests, and docs, but builds on the iBeam provider and does not introduce new secrets or trading behavior.
**Score:** 5/8 — Blast radius: 1, Pattern novelty: 2, Security: 1, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-023-ibkr-stock-search-workflow/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Let users search for any stock available through the IBKR platform and pin results into the backend-persisted watchlist. Search must call the IBKR/iBeam instrument search/contract-detail flow through the provider abstraction rather than a hard-coded symbol list. The frontend should provide a clear search box/autocomplete flow from the trading workspace and symbol page, show provider/authentication errors honestly, and store selected symbols with enough provider metadata to retrieve market data later.

## Dependencies

- **Task:** TP-020 (Postgres-backed watchlist persistence must exist first)
- **Task:** TP-022 (IBKR/iBeam market-data provider and production mock removal must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/provider-abstractions.md` — provider-neutral search/symbol identity seam
- `docs/architecture/paper-trading-workspace.md` — symbol search/watchlist/data-flow contract
- `docs/architecture/modules.md` — Workspaces, MarketData, API, and frontend module boundaries
- `src/ATrade.MarketData/*` — market-data/search contracts
- `src/ATrade.MarketData.Ibkr/*` — IBKR provider implementation from TP-022
- `src/ATrade.Workspaces/*` — Postgres watchlist schema/repository from TP-020
- `src/ATrade.Api/Program.cs` — endpoint registration style
- `frontend/components/TradingWorkspace.tsx` — workspace landing UX
- `frontend/components/Watchlist.tsx` — backend watchlist rendering
- `frontend/components/SymbolChartView.tsx` — symbol page UI
- `frontend/lib/marketDataClient.ts` — market-data client helpers
- `frontend/lib/watchlistClient.ts` — watchlist client from TP-020
- `tests/apphost/ibkr-market-data-provider-tests.sh` — provider-test style
- `tests/apphost/postgres-watchlist-persistence-tests.sh` — persisted watchlist test style
- `tests/apphost/frontend-trading-workspace-tests.sh` — frontend smoke test pattern

## Environment

- **Workspace:** Project root plus `frontend/`
- **Services required:** Automated tests must not require real IBKR credentials. Backend/provider tests should use fake IBKR HTTP responses in test projects. Manual verification may use a real ignored `.env` and active iBeam session.

## File Scope

> This task intentionally overlaps market data, workspace persistence, API, and frontend watchlist/search files.

- `src/ATrade.MarketData/*`
- `src/ATrade.MarketData.Ibkr/*`
- `src/ATrade.Workspaces/*`
- `src/ATrade.Api/Program.cs`
- `frontend/components/SymbolSearch.tsx` (new)
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/Watchlist.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/watchlistClient.ts`
- `frontend/types/marketData.ts`
- `tests/ATrade.MarketData.Ibkr.Tests/*`
- `tests/ATrade.Workspaces.Tests/*`
- `tests/apphost/ibkr-symbol-search-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/provider-abstractions.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm production mocked symbol catalog has been removed by TP-022
- [ ] Confirm Postgres watchlist schema can store provider metadata needed by IBKR search results

### Step 1: Add backend IBKR stock search contracts and endpoints

- [ ] Extend the market-data provider contract with a stock/instrument search method if TP-019/TP-022 did not already add one
- [ ] Implement IBKR/iBeam search using the Client Portal instrument/contract search flow (for example secdef search/detail endpoints) and return provider-neutral results with symbol, name, asset class, exchange, currency, provider, and IBKR `conid`
- [ ] Add API endpoint(s), e.g. `GET /api/market-data/search?query=...&assetClass=stock&limit=...`, with minimum query length, max result limit, cancellation, and safe provider-unavailable/authentication-required errors
- [ ] Avoid hard-coded allowlists; results must come from IBKR/iBeam provider data or test-only fake responses
- [ ] Run targeted provider/API tests with fake IBKR responses

**Artifacts:**
- `src/ATrade.MarketData/MarketDataModels.cs` (modified)
- `src/ATrade.MarketData/*Search*.cs` (new or modified)
- `src/ATrade.MarketData.Ibkr/*Search*.cs` (new or modified)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/ATrade.MarketData.Ibkr.Tests/*` (modified)

### Step 2: Connect search results to persisted watchlists

- [ ] Update the Workspaces watchlist command model so pinning a searched symbol stores provider metadata (`provider`, `conid`, `name`, `exchange`, `currency`, `assetClass`) when available
- [ ] Ensure existing watchlist rows from TP-020 continue to load and can be enriched when a user re-pins or selects a searched result
- [ ] Validate duplicate results by provider/conid when present and by normalized symbol otherwise
- [ ] Add tests for pinning IBKR search results and loading them after API restart
- [ ] Run targeted Workspaces tests: `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Workspaces/*` (modified)
- `tests/ATrade.Workspaces.Tests/*` (modified)
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (modified if endpoint payload changes)

### Step 3: Add frontend search and pin UX

- [ ] Create a reusable `SymbolSearch` component for the workspace and/or symbol page
- [ ] Add frontend client helpers and types for the search endpoint and provider metadata
- [ ] Let users search IBKR stocks, open a selected symbol page, and pin/unpin a selected result into the backend watchlist
- [ ] Show loading, no-results, provider-unavailable, authentication-required, and validation states clearly
- [ ] Ensure the UI no longer limits users to the old trending list or any hard-coded symbol catalog
- [ ] Run targeted frontend build: `cd frontend && npm run build`

**Artifacts:**
- `frontend/components/SymbolSearch.tsx` (new)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `frontend/components/Watchlist.tsx` (modified)
- `frontend/components/SymbolChartView.tsx` (modified)
- `frontend/lib/marketDataClient.ts` (modified)
- `frontend/lib/watchlistClient.ts` (modified)
- `frontend/types/marketData.ts` (modified)

### Step 4: Add IBKR stock search verification

- [ ] Create `tests/apphost/ibkr-symbol-search-tests.sh`
- [ ] Verify backend source contains no hard-coded production stock allowlist for search
- [ ] Verify fake IBKR search responses map to API results with symbol/name/exchange/currency/conid
- [ ] Verify provider-unavailable/no-credential state returns a stable non-200 or error payload without fake results
- [ ] Verify frontend source renders search controls and no longer constrains pinning to the trending list only
- [ ] Run targeted tests: `bash tests/apphost/ibkr-symbol-search-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh`

**Artifacts:**
- `tests/apphost/ibkr-symbol-search-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)

### Step 5: Update docs for IBKR search

- [ ] Update `docs/architecture/paper-trading-workspace.md` with the implemented IBKR stock search UX/API and persisted metadata flow
- [ ] Update `docs/architecture/modules.md` for MarketData, Workspaces, API, and frontend current-state notes
- [ ] Update `docs/architecture/provider-abstractions.md` with the provider-neutral search contract and IBKR implementation details
- [ ] Update `README.md` only if current-status wording becomes stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/provider-abstractions.md` (modified)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/ibeam-runtime-contract-tests.sh && bash tests/apphost/ibkr-market-data-provider-tests.sh && bash tests/apphost/ibkr-symbol-search-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker/iBeam-dependent runtime tests pass or cleanly skip without real credentials
- [ ] Fix all failures
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — record IBKR stock search and pin-any-symbol workflow
- `docs/architecture/modules.md` — update MarketData, Workspaces, API, and frontend responsibilities
- `docs/architecture/provider-abstractions.md` — document the search contract and provider metadata

**Check If Affected:**
- `README.md` — update if user-facing current status becomes stale
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)

## Completion Criteria

- [ ] Users can search IBKR-sourced stocks beyond any trending/default list
- [ ] Search results come from IBKR/iBeam provider data, not production hard-coded lists
- [ ] Searched symbols can be opened and pinned into the Postgres-backed watchlist with provider metadata
- [ ] Tests cover provider mapping, API errors, frontend search controls, and persistence integration
- [ ] Active docs accurately describe the IBKR search workflow and provider metadata shape

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-023): complete Step N — description`
- **Bug fixes:** `fix(TP-023): description`
- **Tests:** `test(TP-023): description`
- **Hydration:** `hydrate: TP-023 expand Step N checkboxes`

## Do NOT

- Reintroduce hard-coded production stock catalogs or mock search configuration
- Require real IBKR credentials for automated tests
- Store IBKR passwords, session cookies, or tokens in Postgres, localStorage, frontend code, or logs
- Add real order placement, live-trading controls, or LEAN behavior in this task
- Couple frontend search directly to IBKR-specific response shapes instead of provider-neutral API payloads
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
