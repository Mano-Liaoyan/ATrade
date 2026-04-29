# TP-022: Replace mocked market data with IBKR/iBeam provider and remove production mocks — Status

**Current Step:** Step 5: Update docs for real IBKR data and removed mocks
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-29
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] iBeam image/env/redaction baseline confirmed
- [x] Current production mocked provider files confirmed before removal
- [x] Test-only fake handler strategy confirmed

---

### Step 1: Implement the IBKR/iBeam market-data provider
**Status:** ✅ Complete

- [x] IBKR market-data provider project/implementation added
- [x] Provider uses iBeam/Gateway config and not direct credential reads
- [x] Contract lookup, snapshots, historical bars, and scanner/trending mapping implemented
- [x] Provider-unavailable/not-authenticated errors implemented
- [x] Targeted IBKR MarketData tests/build pass

---

### Step 2: Remove production mocked market-data code and configuration
**Status:** ✅ Complete

- [x] Production mock provider files removed or excluded from build
- [x] Hard-coded catalogs/source values/user-facing mocked labels removed
- [x] Production DI has no mock fallback
- [x] Test fixtures/fake handlers isolated to tests
- [x] Source audit recorded

---

### Step 3: Wire IBKR-backed HTTP and SignalR behavior
**Status:** ✅ Complete

- [x] API endpoints use IBKR provider abstraction
- [x] SignalR snapshots/streaming use provider or return unavailable safely
- [x] Endpoint shapes/source metadata updated
- [x] Frontend copy/error states updated for real provider status
- [x] Targeted API/frontend checks pass

---

### Step 4: Replace mocked-data verification with IBKR-provider verification
**Status:** ✅ Complete

- [x] IBKR market-data provider shell test added
- [x] Old mocked endpoint assertions replaced
- [x] No-credential provider-unavailable behavior verified
- [x] Fake HTTP mapping tests cover IBKR responses
- [x] Frontend tests no longer assert mocked copy
- [x] Targeted verification scripts pass

---

### Step 5: Update docs for real IBKR data and removed mocks
**Status:** ✅ Complete

- [x] Paper-trading workspace doc updated for IBKR data and no production mocks
- [x] Modules doc updated for MarketData/API/frontend/provider current state
- [x] Provider abstractions doc updated for IBKR implementation
- [x] README reviewed and updated if stale

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker/iBeam-dependent runtime tests pass or cleanly skip
- [ ] All failures fixed
- [ ] Source audit confirms mocks/configuration removed
- [ ] Frontend build passes
- [ ] Solution build passes

---

### Step 7: Documentation & Delivery
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
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-29 22:21 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 22:21 | Step 0 started | Preflight |
| 2026-04-30 | Step 2 source audit | `git grep -n -E 'MockMarketData|mock-deterministic|Mocked' -- src frontend` returned no matches |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
