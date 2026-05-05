# TP-058: Paper capital source — Status

**Current Step:** Step 5: Documentation & Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-05-06
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 2
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
**Status:** ✅ Complete

- [x] "Must Update" docs modified
- [x] README/PLAN updated if affected
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| IBKR paper-capital balance seam uses the Client Portal account-summary endpoint `/v1/api/portfolio/{configured paper account id}/summary`; the account id is an internal path segment only. Parser prefers `totalcashvalue` variants, then `netliquidation` variants, accepting numeric values or objects with `currency` plus `amount`/`value`/`current`/`balance`. | Documented in active architecture docs; tests use fakes and redaction assertions. | `src/ATrade.Brokers.Ibkr/IbkrAccountSummaryClient.cs`, `docs/architecture/paper-trading-workspace.md`, `docs/architecture/modules.md`, `docs/architecture/provider-abstractions.md` |
| Real IBKR/iBeam smoke was skipped for this automated lane because real runtime credentials/account identifiers must remain in ignored local `.env` values and are optional; verification stayed on fake provider tests plus apphost contract validation. | No blocker; follows task safety rules. | Step 4 test results, `tests/ATrade.Brokers.Ibkr.Tests/IbkrPaperCapitalProviderTests.cs`, `tests/apphost/paper-capital-source-tests.sh` |
| `docs/architecture/provider-abstractions.md` was affected by the Accounts-facing paper-capital provider seam even though broker order/status capabilities remain paper-safe/read-only. | Updated to describe `IPaperCapitalService`, `IIbkrPaperCapitalProvider`, unavailable-state mapping, and redaction guardrails. | `docs/architecture/provider-abstractions.md` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 22:13 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 22:13 | Step 0 started | Preflight |
| 2026-05-05 22:34 | Worker iter 1 | done in 1290s, tools: 192 |
| 2026-05-06 | Step 5 completed | Active docs, README/PLAN, provider-abstractions review, and discoveries updated |
| 2026-05-05 22:40 | Worker iter 2 | done in 370s, tools: 87 |
| 2026-05-05 22:40 | Task complete | .DONE created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
