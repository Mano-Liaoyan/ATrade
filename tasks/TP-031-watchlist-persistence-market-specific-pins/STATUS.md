# TP-031: Fix watchlist persistence and market-specific search pins — Status

**Current Step:** Step 4: Add restart and duplicate-market regression coverage
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Diagnose current restart and symbol-only pin behavior
**Status:** ✅ Complete

- [x] Service-restart persistence path reproduced or inspected
- [x] Symbol-only schema/API/frontend pin behavior recorded
- [x] Durable provider/market instrument identity chosen and recorded
- [x] localStorage confirmed non-authoritative and unable to mask persistence failure

---

### Step 1: Make backend watchlist persistence durable and instrument-specific
**Status:** ✅ Complete

- [x] Stable `pinKey` / `instrumentKey` exposed in API JSON
- [x] Idempotent Postgres migration preserves existing rows and allows same-symbol market-specific rows
- [x] Upsert duplicate handling merges only exact instrument keys
- [x] Unpin removes exact instrument key/provider identity with unambiguous legacy fallback
- [x] Restart persistence root cause fixed or verified
- [x] Targeted Workspaces tests run

---

### Step 2: Update frontend pin state to use exact instrument identity
**Status:** ✅ Complete

- [x] `watchlistClient` types/helpers carry backend instrument key/provider-market identity
- [x] `TradingWorkspace`, `SymbolSearch`, `TrendingList`, and `Watchlist` use exact keys for pinned/saving state
- [x] Removal actions use exact unpin path where possible
- [x] localStorage remains legacy/manual/non-authoritative only
- [x] Frontend build or targeted tests run

---

### Step 3: Show market/exchange logos and explicit market metadata in search
**Status:** ✅ Complete

- [x] Local market/exchange logo or badge component added
- [x] Search results render provider, exchange/market, currency, asset class, and provider id/conid when available
- [x] Duplicate-name/symbol results use unique keys and accessible market labels
- [x] Saved watchlist renders market identity after restart
- [x] Frontend source/runtime tests updated

---

### Step 4: Add restart and duplicate-market regression coverage
**Status:** ✅ Complete

- [x] Postgres watchlist persistence script verifies provider-backed pins survive restart
- [x] Duplicate-market fixtures/tests prove pin/remove affects only one exact instrument
- [x] Frontend tests detect symbol-only pinned-state regressions
- [x] Database-unavailable behavior does not claim cached pins were persisted
- [x] Targeted backend/frontend tests/scripts run

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `bash tests/apphost/postgres-watchlist-persistence-tests.sh` passing or cleanly skipped where appropriate
- [ ] `bash tests/apphost/ibkr-symbol-search-tests.sh` passing
- [ ] `bash tests/apphost/frontend-trading-workspace-tests.sh` passing
- [ ] Frontend build passing: `cd frontend && npm run build`
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with persistence root cause, identity semantics, and migration caveats

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Existing `postgres-watchlist-persistence-tests.sh` successfully pins via API, restarts `ATrade.Api` against the same disposable Postgres container, and verifies AAPL/MSFT survive; restart persistence path itself passes before identity changes. | Use as baseline; extend later for duplicate provider/market pins. | `tests/apphost/postgres-watchlist-persistence-tests.sh`; run `bash tests/apphost/postgres-watchlist-persistence-tests.sh` |
| Current identity collapses duplicate instruments to bare symbols: Postgres primary key and upsert conflict are `(user_id, workspace_id, symbol)`, replacement normalization merges same-symbol rows, API unpin is `DELETE /api/workspace/watchlist/{symbol}`, and frontend `pinnedSymbolNames`/`savingSymbol`/search pinned set use uppercased symbol strings. | Backend and frontend must move to exact `instrumentKey`/provider-market identity; symbol-only delete can remain only as unambiguous legacy fallback. | `src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs`; `WorkspaceWatchlistNormalizer.cs`; `WorkspaceWatchlistRepository.cs`; `src/ATrade.Api/Program.cs`; `frontend/components/TradingWorkspace.tsx`; `SymbolSearch.tsx` |
| Chosen durable identity: expose `instrumentKey`/`pinKey` as the normalized tuple `provider=<provider>|providerSymbolId=<id>|ibkrConid=<conid>|symbol=<symbol>|exchange=<exchange>|currency=<currency>|assetClass=<assetClass>`. Provider is lower-case; symbol/exchange/currency/assetClass are upper-case; IBKR `conid` is mirrored into `providerSymbolId` when only `ibkrConid` is supplied. Same symbol/name on a different exchange/currency/provider id yields a different key. | Implement in backend normalizer/model/API JSON, Postgres unique key, frontend exact pin state, and docs. | `WorkspaceWatchlistModels.cs`; `WorkspaceWatchlistNormalizer.cs`; frontend exact-key helpers |
| Browser `localStorage` is currently a symbol-only cache/migration source: backend responses write symbols into it, initial backend load migrates unmigrated cached manual symbols, and backend failures show cached rows with `source='cache'`, a watchlist error, and disabled actions. It should remain legacy/manual only and must not infer provider-market pinned state. | Preserve/strengthen read-only cache behavior; database failures must surface as errors instead of being presented as persisted pins. | `frontend/lib/watchlistStorage.ts`; `frontend/components/TradingWorkspace.tsx`; `frontend/components/Watchlist.tsx` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 15:40 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 15:40 | Step 0 started | Diagnose current restart and symbol-only pin behavior |
| 2026-04-30 15:45 | Restart persistence baseline | `bash tests/apphost/postgres-watchlist-persistence-tests.sh` passed; pins persisted across API restart with same Postgres DB. |
| 2026-04-30 15:48 | Symbol-only pin behavior inspected | Schema, repository/API unpin, normalizer duplicate merge, and frontend pinned-state all key off bare symbol, so same-symbol market results appear pinned together. |
| 2026-04-30 15:51 | Instrument identity chosen | Durable watchlist key will be the normalized provider/providerSymbolId/ibkrConid/symbol/exchange/currency/assetClass tuple, exposed as `instrumentKey` and `pinKey`. |
| 2026-04-30 15:53 | localStorage behavior inspected | Cache is symbol-only, loaded only as read-only fallback with an error on backend failure, and used as one-time manual migration after backend load. |
| 2026-04-30 15:55 | Step 1 started | Backend instrument-key persistence implementation. |
| 2026-04-30 16:10 | Backend response key fields added | `WorkspaceWatchlistSymbol` now carries `instrumentKey` and `pinKey`; repository reads/stores the normalized key so minimal API JSON exposes both fields. |
| 2026-04-30 16:12 | Instrument-key migration added | Schema initialization adds/backfills `instrument_key`, rebuilds the primary key on `(user_id, workspace_id, instrument_key)`, and keeps a symbol index for legacy fallback. |
| 2026-04-30 16:13 | Exact duplicate handling implemented | Upserts conflict only on `instrument_key`; replacement normalization no longer merges same symbols unless the full instrument key matches. |
| 2026-04-30 16:14 | Exact unpin path implemented | Added `DELETE /api/workspace/watchlist/pins/{instrumentKey}` and repository exact-delete; legacy symbol delete now only removes one row and raises `ambiguous-symbol` when multiple market-specific pins share a symbol. |
| 2026-04-30 16:25 | Restart persistence root cause verified | Baseline restart script passed in Step 0; backend remains Postgres-authoritative with 503 storage errors, and schema migration preserves rows while moving persistence identity from symbol PK to instrument key. |
| 2026-04-30 16:26 | Targeted Workspaces tests | `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal` passed: 23 tests. |
| 2026-04-30 16:27 | API compile check | `dotnet build src/ATrade.Api/ATrade.Api.csproj --nologo --verbosity minimal` passed with 0 warnings/errors. |
| 2026-04-30 16:28 | Step 2 started | Frontend exact instrument-key state implementation. |
| 2026-04-30 16:40 | Frontend watchlist identity helpers added | `watchlistClient` types include `instrumentKey`/`pinKey`; helpers now compute backend-compatible provider-market keys and call the exact unpin route. |
| 2026-04-30 16:41 | Frontend pin state moved off symbols | `TradingWorkspace`, `SymbolSearch`, `TrendingList`, and `Watchlist` now compare pinned/saving state by exact instrument keys instead of uppercased symbol strings. |
| 2026-04-30 16:42 | Frontend exact removal wired | Toggle/remove actions call `unpinWatchlistInstrument` with `pinKey`/`instrumentKey`; symbol-only unpin remains only as defensive fallback. |
| 2026-04-30 16:43 | localStorage kept non-authoritative | Storage helper is documented as legacy symbol-only; cached symbols migrate as manual instrument keys only and remain read-only when backend watchlist calls fail. |
| 2026-04-30 16:45 | Frontend build | Initial `npm run build` failed because `next` was not installed in the worktree; after `cd frontend && npm ci`, `npm run build` passed. |
| 2026-04-30 16:46 | Step 3 started | Market/exchange badge UI and explicit search/watchlist metadata. |
| 2026-04-30 16:50 | Market badge component added | Added local `MarketLogo` badge component and CSS for NASDAQ, NYSE/ARCA, LSE, TSX/TSE, HKEX, SMART/IBKR, and fallback market badges. |
| 2026-04-30 16:53 | Search metadata rendered | Search result rows now show local market badge plus provider, market/exchange, currency, asset class, and IBKR conid/provider id text. |
| 2026-04-30 16:54 | Duplicate result accessibility hardened | Search and watchlist list items now key by exact instrument key and include market/provider identity in `aria-label` text. |
| 2026-04-30 16:55 | Saved watchlist market identity rendered | Backend-loaded watchlist rows display market badge, `Market <exchange>`, provider, currency, asset class, and provider id/conid metadata; this uses persisted API fields after restart. |
| 2026-04-30 17:02 | Frontend tests updated and run | Updated apphost frontend/search assertions for `MarketLogo`, exact keys, and conid metadata; `cd frontend && npm run build`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, and `bash tests/apphost/ibkr-symbol-search-tests.sh` passed. |
| 2026-04-30 17:04 | Step 4 started | Restart and duplicate-market regression coverage. |
| 2026-04-30 17:15 | Postgres restart regression extended | Persistence script now pins provider-backed AAPL/MSFT instruments, restarts API on the same Postgres DB, and verifies exact `instrumentKey` rows/metadata survive; script passed. |
| 2026-04-30 17:16 | Duplicate-market regression covered | Workspaces normalizer tests and Postgres script cover duplicate AAPL rows on NASDAQ/LSE; legacy symbol delete is ambiguous and exact key delete removes only one market. |
| 2026-04-30 17:18 | Frontend symbol-only regression assertions added | Apphost frontend/search scripts assert `pinnedInstrumentKeys`, `savingPinKey`, `key={pinKey}`, and `pinnedSet.has(pinKey)`, and reject `pinnedSymbolNames`/`savingSymbol`/symbol-set checks. |
| 2026-04-30 17:20 | Cache failure regression assertions added | Frontend apphost script asserts legacy symbol-only storage, cache-source labeling, read-only cached-pin error text, and disabled actions while `watchlistError` is set. |
| 2026-04-30 17:28 | Targeted regression suite | `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj`, `bash tests/apphost/postgres-watchlist-persistence-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, and `bash tests/apphost/ibkr-symbol-search-tests.sh` passed. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
