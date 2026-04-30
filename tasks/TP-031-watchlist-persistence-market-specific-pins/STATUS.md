# TP-031: Fix watchlist persistence and market-specific search pins — Status

**Current Step:** Step 0: Diagnose current restart and symbol-only pin behavior
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
**Status:** ⬜ Not Started

- [ ] Stable `pinKey` / `instrumentKey` exposed in API JSON
- [ ] Idempotent Postgres migration preserves existing rows and allows same-symbol market-specific rows
- [ ] Upsert duplicate handling merges only exact instrument keys
- [ ] Unpin removes exact instrument key/provider identity with unambiguous legacy fallback
- [ ] Restart persistence root cause fixed or verified
- [ ] Targeted Workspaces tests run

---

### Step 2: Update frontend pin state to use exact instrument identity
**Status:** ⬜ Not Started

- [ ] `watchlistClient` types/helpers carry backend instrument key/provider-market identity
- [ ] `TradingWorkspace`, `SymbolSearch`, `TrendingList`, and `Watchlist` use exact keys for pinned/saving state
- [ ] Removal actions use exact unpin path where possible
- [ ] localStorage remains legacy/manual/non-authoritative only
- [ ] Frontend build or targeted tests run

---

### Step 3: Show market/exchange logos and explicit market metadata in search
**Status:** ⬜ Not Started

- [ ] Local market/exchange logo or badge component added
- [ ] Search results render provider, exchange/market, currency, asset class, and provider id/conid when available
- [ ] Duplicate-name/symbol results use unique keys and accessible market labels
- [ ] Saved watchlist renders market identity after restart
- [ ] Frontend source/runtime tests updated

---

### Step 4: Add restart and duplicate-market regression coverage
**Status:** ⬜ Not Started

- [ ] Postgres watchlist persistence script verifies provider-backed pins survive restart
- [ ] Duplicate-market fixtures/tests prove pin/remove affects only one exact instrument
- [ ] Frontend tests detect symbol-only pinned-state regressions
- [ ] Database-unavailable behavior does not claim cached pins were persisted
- [ ] Targeted backend/frontend tests/scripts run

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
