# TP-019: Introduce provider-neutral broker and market-data abstractions — Status

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
- [ ] Current broker and market-data endpoints pass before refactoring
- [ ] No real iBeam/IBKR/LEAN connection is introduced

---

### Step 1: Add provider-neutral broker contracts
**Status:** ⬜ Not Started

- [ ] Create broker abstraction project and add it to the solution
- [ ] Define provider identity, capabilities, session/status, and account-mode contracts
- [ ] Adapt current IBKR broker status implementation to the neutral contracts
- [ ] Preserve existing broker status endpoint and paper-only no-real-orders guardrails
- [ ] Targeted broker tests/build pass

---

### Step 2: Add provider-neutral market-data contracts
**Status:** ⬜ Not Started

- [ ] Separate market-data contracts from the concrete mocked provider
- [ ] Preserve current HTTP payload behavior through a swappable provider layer
- [ ] Keep existing mocked provider only as temporary compatibility until TP-022
- [ ] Add provider-unavailable/not-configured state handling
- [ ] Targeted MarketData build passes

---

### Step 3: Wire provider composition through the API and tests
**Status:** ⬜ Not Started

- [ ] API composition depends on provider-neutral services
- [ ] Provider swapability tests added
- [ ] Provider abstraction shell test added
- [ ] Existing health/accounts/broker/orders/market-data behavior preserved
- [ ] Targeted provider abstraction tests pass

---

### Step 4: Document the provider abstraction contract
**Status:** ⬜ Not Started

- [ ] Provider abstraction architecture doc created and indexed
- [ ] Module docs updated for broker and market-data seams
- [ ] Paper-trading workspace docs updated for future iBeam/LEAN plug-in boundaries
- [ ] Overview/README reviewed and updated if stale

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker-dependent runtime test passes or cleanly skips
- [ ] All failures fixed
- [ ] Solution build passes

---

### Step 6: Documentation & Delivery
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
