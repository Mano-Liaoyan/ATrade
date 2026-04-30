# TP-027: Fix authenticated iBeam refresh transport failures — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-30
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and failure classification
**Status:** ⬜ Not Started

- [ ] Sanitized user-observed failure recorded without secrets/session values
- [ ] Gateway URL scheme/port handling inventoried across code, templates, docs, and tests
- [ ] Root cause classified as transport scheme/TLS/certificate, readiness/race, port mapping, or another issue
- [ ] Real-runtime reproduction performed with redacted output, or automated simulation/skip rationale recorded

---

### Step 1: Implement the shared IBKR/iBeam transport fix
**Status:** ⬜ Not Started

- [ ] Broker and market-data clients share corrected gateway transport configuration
- [ ] Any self-signed certificate handling is local-loopback scoped and not global
- [ ] AppHost endpoint metadata and committed template defaults align with actual iBeam transport behavior
- [ ] Transport reset/scheme mismatch diagnostics are actionable and redacted
- [ ] Targeted broker/market-data tests affected by transport changes pass

---

### Step 2: Add regression coverage for the transport contract
**Status:** ⬜ Not Started

- [ ] New focused transport regression test file added
- [ ] Existing broker and market-data tests updated for corrected URL/diagnostic behavior
- [ ] AppHost/config shell tests guard the corrected gateway scheme/port/template contract
- [ ] Optional real-iBeam smoke coverage added or explicit skip rationale recorded
- [ ] Targeted changed tests/scripts pass

---

### Step 3: Verify API and frontend refresh behavior
**Status:** ⬜ Not Started

- [ ] Broker status and market-data trending endpoints use corrected transport path
- [ ] Safe disabled/missing/unauthenticated/unreachable iBeam responses are preserved
- [ ] TradingWorkspace retry/refresh recovers after iBeam authentication, with safe error copy if still unavailable
- [ ] Provider-neutral payloads and no-secrets output preserved

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal` passes
- [ ] `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passes
- [ ] `bash tests/apphost/ibeam-runtime-contract-tests.sh` passes or cleanly skips runtime-dependent checks
- [ ] `bash tests/apphost/ibkr-paper-safety-tests.sh` passes
- [ ] `bash tests/apphost/ibkr-market-data-provider-tests.sh` passes
- [ ] `bash tests/apphost/market-data-feature-tests.sh` passes
- [ ] `bash tests/apphost/frontend-trading-workspace-tests.sh` passes if frontend files changed
- [ ] `dotnet test ATrade.slnx --nologo --verbosity minimal` passes
- [ ] Optional real-runtime `./start run` / frontend retry / API trending verification recorded if local ignored `.env` and iBeam are available
- [ ] All failures fixed or unrelated pre-existing failures documented with evidence

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs/templates modified
- [ ] "Check If Affected" docs reviewed and updated where relevant
- [ ] Root cause, chosen fix, and skipped real-runtime checks logged in Discoveries
- [ ] Delivery notes explain safe local iBeam retry/refresh steps

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| `tasks/CONTEXT.md` and `PLAN.md` still advertised `TP-026` as next while a `tasks/TP-026-*` packet already existed. | Task creator used the next unused ID (`TP-027`) and advanced tracking to `TP-028`. | `tasks/CONTEXT.md`, `PLAN.md` |

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

User-observed failure summary for implementer: refreshing IBKR market data in Aspire caused `GET /api/market-data/trending` to return 503 after both `IIbkrMarketDataClient` and `IIbkrGatewayClient` attempted `GET http://127.0.0.1:<gateway-port>/v1/api/iserver/auth/status` and hit `Connection reset by peer`, while iBeam reported the gateway was running/authenticated. Session/account details from the user log were intentionally omitted.
