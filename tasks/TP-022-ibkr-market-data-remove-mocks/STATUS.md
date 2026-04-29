# TP-022: Replace mocked market data with IBKR/iBeam provider and remove production mocks — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-29
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] iBeam image/env/redaction baseline confirmed
- [ ] Current production mocked provider files confirmed before removal
- [ ] Test-only fake handler strategy confirmed

---

### Step 1: Implement the IBKR/iBeam market-data provider
**Status:** ⬜ Not Started

- [ ] IBKR market-data provider project/implementation added
- [ ] Provider uses iBeam/Gateway config and not direct credential reads
- [ ] Contract lookup, snapshots, historical bars, and scanner/trending mapping implemented
- [ ] Provider-unavailable/not-authenticated errors implemented
- [ ] Targeted IBKR MarketData tests/build pass

---

### Step 2: Remove production mocked market-data code and configuration
**Status:** ⬜ Not Started

- [ ] Production mock provider files removed or excluded from build
- [ ] Hard-coded catalogs/source values/user-facing mocked labels removed
- [ ] Production DI has no mock fallback
- [ ] Test fixtures/fake handlers isolated to tests
- [ ] Source audit recorded

---

### Step 3: Wire IBKR-backed HTTP and SignalR behavior
**Status:** ⬜ Not Started

- [ ] API endpoints use IBKR provider abstraction
- [ ] SignalR snapshots/streaming use provider or return unavailable safely
- [ ] Endpoint shapes/source metadata updated
- [ ] Frontend copy/error states updated for real provider status
- [ ] Targeted API/frontend checks pass

---

### Step 4: Replace mocked-data verification with IBKR-provider verification
**Status:** ⬜ Not Started

- [ ] IBKR market-data provider shell test added
- [ ] Old mocked endpoint assertions replaced
- [ ] No-credential provider-unavailable behavior verified
- [ ] Fake HTTP mapping tests cover IBKR responses
- [ ] Frontend tests no longer assert mocked copy

---

### Step 5: Update docs for real IBKR data and removed mocks
**Status:** ⬜ Not Started

- [ ] Paper-trading workspace doc updated for IBKR data and no production mocks
- [ ] Modules doc updated for MarketData/API/frontend/provider current state
- [ ] Provider abstractions doc updated for IBKR implementation
- [ ] README reviewed and updated if stale

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
