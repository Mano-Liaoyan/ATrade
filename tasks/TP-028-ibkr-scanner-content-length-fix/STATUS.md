# TP-028: Fix IBKR scanner 411 Length Required for trending — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and failure classification
**Status:** ⬜ Not Started

- [ ] Sanitized `/api/market-data/trending` 411 failure recorded without secrets
- [ ] Current scanner request shape inspected and likely root cause recorded
- [ ] Fake-handler and optional real-iBeam verification plan recorded

---

### Step 1: Send a Client Portal-compatible scanner request
**Status:** ⬜ Not Started

- [ ] Scanner request sends POST JSON with explicit positive `Content-Length` and no chunked transfer
- [ ] Scanner payload semantics remain equivalent or source-evidenced corrections are documented
- [ ] Safe provider error mapping and no-secrets diagnostics preserved
- [ ] Scanner response parsing still maps valid fake IBKR responses to trending symbols
- [ ] Targeted provider tests run

---

### Step 2: Add scanner request-shape regression coverage
**Status:** ⬜ Not Started

- [ ] New focused scanner request contract test file added
- [ ] Fake `411 Length Required` error mapping covered safely
- [ ] Apphost/source contract scripts updated if needed
- [ ] Targeted tests/scripts run

---

### Step 3: Verify home-page trending behavior
**Status:** ⬜ Not Started

- [ ] Disabled/missing/unreachable/unauthenticated iBeam states still return safe provider errors
- [ ] Fake authenticated scanner responses flow through `/api/market-data/trending`
- [ ] Optional real authenticated iBeam smoke check run or skip rationale recorded
- [ ] Frontend error copy updated only if needed

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `bash tests/apphost/ibkr-market-data-provider-tests.sh` passing
- [ ] `bash tests/apphost/market-data-feature-tests.sh` passing
- [ ] Frontend trading workspace tests passing if frontend files changed
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Frontend build passing if frontend files changed
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with root cause, coverage, and real-runtime verification/skip rationale

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
