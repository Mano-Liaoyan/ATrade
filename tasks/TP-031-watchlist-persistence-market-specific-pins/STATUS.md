# TP-031: Fix watchlist persistence and market-specific search pins — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Diagnose current restart and symbol-only pin behavior
**Status:** ⬜ Not Started

- [ ] Service-restart persistence path reproduced or inspected
- [ ] Symbol-only schema/API/frontend pin behavior recorded
- [ ] Durable provider/market instrument identity chosen and recorded
- [ ] localStorage confirmed non-authoritative and unable to mask persistence failure

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

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
