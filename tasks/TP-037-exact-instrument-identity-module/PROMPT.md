# Task: TP-037 - Deepen the Exact Instrument Identity module

**Created:** 2026-05-02
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This task touches backend market-data shapes, Timescale cache keys, workspace watchlist identity, frontend provisional pin keys, and docs. It preserves HTTP paths and payload compatibility but changes an important identity seam.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-037-exact-instrument-identity-module/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen the Exact Instrument Identity module so provider, provider symbol id, symbol, exchange, currency, and asset class are normalized once and preserved across market-data search/trending/chart/cache/watchlist flows. This matters because the current implementation duplicates the instrument key invariant across C#, TypeScript, SQL, and tests, while some chart/cache flows still collapse provider-backed instruments to bare symbols.

## Dependencies

- **Task:** TP-036 (local runtime contract defaults and docs must be stable first)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/provider-abstractions.md` — provider-neutral market-data and identity contract
- `docs/architecture/modules.md` — module map for MarketData, Timescale, Workspaces, and frontend
- `docs/architecture/paper-trading-workspace.md` — exact pins, search, and chart workspace contract

## Environment

- **Workspace:** `src/ATrade.MarketData`, `src/ATrade.Workspaces`, `frontend/`
- **Services required:** None for unit tests; AppHost scripts must skip cleanly if local runtimes are unavailable

## File Scope

- `src/ATrade.MarketData/MarketDataProviderModels.cs`
- `src/ATrade.MarketData/MarketDataModels.cs`
- `src/ATrade.MarketData.Ibkr/*`
- `src/ATrade.MarketData.Timescale/*`
- `src/ATrade.Workspaces/WorkspaceWatchlistInstrumentKey.cs`
- `src/ATrade.Workspaces/WorkspaceWatchlistNormalizer.cs`
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs`
- `src/ATrade.Api/Program.cs`
- `frontend/lib/watchlistClient.ts`
- `frontend/types/marketData.ts`
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/SymbolSearch.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/app/symbols/[symbol]/page.tsx`
- `tests/ATrade.Workspaces.Tests/*`
- `tests/ATrade.MarketData.Timescale.Tests/*`
- `tests/ATrade.ProviderAbstractions.Tests/ExactInstrumentIdentityContractTests.cs` (new)
- `tests/apphost/*watchlist*`
- `docs/architecture/*`

## Steps

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Establish Exact Instrument Identity as the backend-owned interface

- [ ] Add or deepen a backend Exact Instrument Identity module that owns normalization, defaulting, encoding, equality, and provider/market field projection
- [ ] Move duplicated C# instrument key construction into that module while preserving existing `instrumentKey` / `pinKey` payloads
- [ ] Add `tests/ATrade.ProviderAbstractions.Tests/ExactInstrumentIdentityContractTests.cs` or equivalent new test file covering same-symbol/different-market and manual legacy identities
- [ ] Run targeted identity/workspace tests

**Artifacts:**
- `src/ATrade.MarketData/*` or `src/ATrade.Workspaces/*` identity module files (new/modified)
- `tests/ATrade.ProviderAbstractions.Tests/ExactInstrumentIdentityContractTests.cs` (new)

### Step 2: Preserve identity through market-data and Timescale flows

- [ ] Ensure search, trending, candle, indicator, and latest-update flows can carry Exact Instrument Identity where provider-backed identity exists
- [ ] Update Timescale cache models/queries so provider symbol id, exchange, currency, and asset class are persisted and read where available; bare-symbol legacy reads must still work
- [ ] Keep current HTTP paths and existing payload fields compatible for callers that only supply a symbol
- [ ] Run targeted market-data/provider/Timescale tests

**Artifacts:**
- `src/ATrade.MarketData*/` (modified)
- `src/ATrade.MarketData.Timescale/*` (modified)
- `tests/ATrade.MarketData.Timescale.Tests/*` (modified/new tests as needed)

### Step 3: Make frontend provisional identity use one adapter

- [ ] Replace duplicated TypeScript key construction/parsing with one frontend adapter that mirrors backend identity only for optimistic UI state
- [ ] Preserve backend-owned persisted keys as the authority after a watchlist response
- [ ] Keep `/symbols/{symbol}` working as a legacy/manual route and add exact identity handoff through query/path state only if needed and documented
- [ ] Run targeted frontend workspace contract tests or TypeScript build checks

**Artifacts:**
- `frontend/lib/watchlistClient.ts` (modified or split)
- `frontend/types/marketData.ts` (modified)
- `frontend/components/*` (modified)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run integration tests if affected: `bash tests/apphost/postgres-watchlist-persistence-tests.sh`, `bash tests/apphost/apphost-postgres-watchlist-volume-tests.sh`, `bash tests/apphost/ibkr-symbol-search-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal` and `cd frontend && npm run build`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `tasks/CONTEXT.md` — sharpen Exact Instrument Identity if implementation changes the accepted definition
- `docs/architecture/provider-abstractions.md` — provider-neutral identity contract
- `docs/architecture/paper-trading-workspace.md` — exact watchlist/chart identity behavior
- `docs/architecture/modules.md` — module map if a new identity module/seam is introduced

**Check If Affected:**
- `README.md` — runtime/current surface summary if payload behavior changes
- `docs/architecture/overview.md` — data ownership summary if cache keys change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Same-symbol instruments from different provider/market identities stay distinct through search, pinning, persistence, and chart handoff
- [ ] Backend remains the authority for persisted exact instrument keys

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-037): complete Step N — description`
- **Bug fixes:** `fix(TP-037): description`
- **Tests:** `test(TP-037): description`
- **Hydration:** `hydrate: TP-037 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Break existing HTTP paths or remove legacy bare-symbol behavior in this task
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies
- Add real order placement or live-trading behavior

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
