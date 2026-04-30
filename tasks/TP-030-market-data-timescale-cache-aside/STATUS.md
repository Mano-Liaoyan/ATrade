# TP-030: Serve market data through TimescaleDB cache-aside — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Dependency preflight and data-path plan
**Status:** ⬜ Not Started

- [ ] TP-028 completion and scanner content-length regression coverage confirmed
- [ ] TP-029 completion and Timescale repository/options confirmed
- [ ] Cache-aside plan for trending, candles, indicators, and unavailable states recorded

---

### Step 1: Compose a cache-aware market-data service
**Status:** ⬜ Not Started

- [ ] Timescale module registered in `ATrade.Api` using `ConnectionStrings:timescaledb`
- [ ] Cache-aware `IMarketDataService` implementation/decorator added without endpoint provider coupling
- [ ] Idempotent schema initialization and storage-unavailable behavior implemented
- [ ] Freshness window read via typed options from `.env`/configuration
- [ ] Targeted API/market-data build/tests run

---

### Step 2: Cache-aside `/api/market-data/trending`
**Status:** ⬜ Not Started

- [ ] Fresh Timescale trending/scanner snapshot read before IBKR/iBeam call
- [ ] Fresh persisted snapshot returned with honest source metadata
- [ ] Missing/stale snapshot triggers provider fetch, persistence write, and provider response
- [ ] Provider-unavailable with fresh cache returns cache; provider-unavailable with stale-only cache returns safe error
- [ ] Tests cover hit, miss, stale refresh, write-after-fetch, and fresh-cache unavailable behavior

---

### Step 3: Cache-aside candles and indicator inputs
**Status:** ⬜ Not Started

- [ ] Candle endpoint reads fresh Timescale candles before provider call
- [ ] Missing/stale candle series fetches provider candles, persists them, and returns fresh response
- [ ] Indicator endpoint computes from cached candles when fresh
- [ ] Unsupported/timeframe/provider errors preserved without stale-as-fresh behavior
- [ ] Tests cover candle and indicator cache paths

---

### Step 4: API/frontend compatibility and observability
**Status:** ⬜ Not Started

- [ ] Existing routes and frontend clients remain stable unless minimal metadata is required
- [ ] Home page can load from fresh Timescale data after service restart
- [ ] No-fresh-cache provider errors remain safe and actionable
- [ ] Frontend tests updated only if visible source/error text changes
- [ ] Targeted endpoint/apphost tests run

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `bash tests/apphost/market-data-timescale-persistence-tests.sh` passing or cleanly skipped
- [ ] `bash tests/apphost/market-data-feature-tests.sh` passing
- [ ] `bash tests/apphost/ibkr-market-data-provider-tests.sh` passing
- [ ] Frontend trading workspace tests passing if frontend files changed
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Frontend build passing if frontend files changed
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with cache semantics, unavailable behavior, and future-work notes

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
