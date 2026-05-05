# TP-058: Paper capital source — Status

**Current Step:** Step 4: Testing & Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Add provider-neutral paper-capital contracts and local ledger persistence
**Status:** ✅ Complete

- [x] Accounts paper-capital contracts created
- [x] Postgres local paper capital repository/schema added
- [x] Local capital validation and storage error shapes implemented
- [x] `tests/ATrade.Accounts.Tests` covers local persistence, validation, unconfigured state, and redaction

---

### Step 2: Add safe IBKR/iBeam paper balance read seam
**Status:** ✅ Complete

> ⚠️ Hydrate: Expand based on the existing broker gateway transport/client patterns and selected safe Client Portal balance endpoint.

- [x] Client Portal account-summary read client parses `/v1/api/portfolio/{configuredPaperAccountId}/summary` for `totalcashvalue`/`netliquidation`
- [x] Authenticated-readiness gate and Accounts `IIbkrPaperCapitalProvider` adapter added
- [x] Account id use remains internal and redacted from availability/messages/logs/tests
- [x] Disabled/missing credentials/unauthenticated/rejected-live/timeout/provider failure states mapped safely
- [x] IBKR broker tests cover balance success, unavailable states, timeout/error redaction, and no leaked account identifiers

---

### Step 3: Expose paper-capital APIs through `ATrade.Api`
**Status:** ✅ Complete

- [x] Accounts services composed with required configuration/Postgres dependencies
- [x] `GET /api/accounts/paper-capital` implemented
- [x] `PUT /api/accounts/local-paper-capital` implemented
- [x] API/apphost contract validation added

---

### Step 4: Testing & Verification
**Status:** ✅ Complete

- [x] Targeted Accounts tests passing
- [x] Targeted IBKR broker tests passing
- [x] Paper-capital apphost/API validation passing
- [x] FULL test suite passing
- [x] All failures fixed
- [x] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] README/PLAN updated if affected
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
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 22:13 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 22:13 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
