# TP-027: Fix authenticated iBeam refresh transport failures — Status

**Current Step:** Step 1: Implement the shared IBKR/iBeam transport fix
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and failure classification
**Status:** ✅ Complete

- [x] Sanitized user-observed failure recorded without secrets/session values
- [x] Gateway URL scheme/port handling inventoried across code, templates, docs, and tests
- [x] Root cause classified as transport scheme/TLS/certificate, readiness/race, port mapping, or another issue
- [x] Real-runtime reproduction performed with redacted output, or automated simulation/skip rationale recorded

---

### Step 1: Implement the shared IBKR/iBeam transport fix
**Status:** ✅ Complete

- [x] Broker and market-data clients share corrected gateway transport configuration
- [x] Any self-signed certificate handling is local-loopback scoped and not global
- [x] AppHost endpoint metadata and committed template defaults align with actual iBeam transport behavior
- [x] Transport reset/scheme mismatch diagnostics are actionable and redacted
- [x] Targeted broker/market-data tests affected by transport changes pass

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
| Current iBeam transport inventory: broker `IbkrGatewayOptions` defaults `GatewayBaseUrl` to `http://127.0.0.1:5000`; broker and market-data `AddHttpClient` registrations independently set `BaseAddress`/timeout from that option and do not share a handler/certificate policy; AppHost declares `ibkr-gateway` with an HTTP endpoint on the configured port and forwards `ATRADE_IBKR_GATEWAY_URL`/`PORT` to API and worker; `.env.template`, active startup docs, and apphost shell tests assert `http://127.0.0.1:5000`; `.env.example` is referenced by docs/tests but is absent in this lane; unit tests mostly use fake `https://gateway.paper.local` URLs. | Step 0 inventory recorded for transport fix; no ignored `.env` values read. | `src/ATrade.Brokers.Ibkr`, `src/ATrade.MarketData.Ibkr`, `src/ATrade.AppHost/Program.cs`, `.env.template`, `scripts/README.md`, `tests/apphost/*`, `tests/ATrade.*.Tests/*` |
| Root cause classified as a transport scheme/TLS mismatch: authenticated `voyz/ibeam:latest` / Client Portal traffic is HTTPS on the local gateway port with a development/self-signed certificate, while the committed ATrade contract and observed backend request used plain HTTP to the same loopback port. That mismatch reaches the port but fails before auth readiness or market-data logic, producing empty-reply/reset-style transport exceptions. | Fix should move the shared gateway base URL to HTTPS and add narrowly scoped loopback iBeam certificate validation; no port-mapping or readiness race was identified as the primary issue. | `IbkrGatewayOptions`, `.env.template`, `scripts/README.md`, local TLS simulation |
| Shared transport helper added: `IbkrGatewayTransport` normalizes local iBeam HTTP loopback URLs to HTTPS, centralizes `HttpClient` base-address/timeout configuration, and supplies the primary handler used by both `IIbkrGatewayClient` and `IIbkrMarketDataClient`. | Implemented in Step 1; broker, market-data, and AppHost projects build successfully after the change. | `src/ATrade.Brokers.Ibkr/IbkrGatewayTransport.cs`, `IbkrServiceCollectionExtensions.cs`, `IbkrMarketDataProvider.cs` |
| Self-signed certificate handling is scoped to local iBeam HTTPS only: the handler accepts certificate errors only when the configured gateway and request URI are HTTPS loopback endpoints on the same port, the configured image is `voyz/ibeam:latest`, and the certificate is self-signed; arbitrary remote hosts and non-iBeam images keep default failure behavior for TLS errors. | Implemented in Step 1; focused regression tests will lock this down in Step 2. | `src/ATrade.Brokers.Ibkr/IbkrGatewayTransport.cs` |
| AppHost/template transport defaults now use HTTPS for iBeam: the `ibkr-gateway` resource is declared with an HTTPS endpoint, `.env.template` defaults `ATRADE_IBKR_GATEWAY_URL` to `https://127.0.0.1:5000`, and `.env.example` was restored from the synchronized template. | Implemented in Step 1; shell contract tests will be updated in Step 2 for the new expected scheme. | `src/ATrade.AppHost/Program.cs`, `.env.template`, `.env.example` |
| Transport diagnostics now avoid echoing exception text or configured gateway values for unreachable/reset cases and instead tell developers to verify local iBeam HTTPS transport, authentication, and retry; credential/account/session fields are still omitted from broker and market-data payloads. | Implemented in Step 1; redaction/safe-response tests will verify in Steps 2-4. | `IbkrBrokerStatusService.cs`, `IbkrMarketDataProvider.cs`, `IbkrGatewayTransport.cs` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 07:49 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 07:49 | Step 0 started | Preflight and failure classification |
| 2026-04-30 | Step 0 complete | Sanitized failure recorded, transport inventory captured, TLS/scheme mismatch classified, and no-secret simulation/default-port probe recorded. |
| 2026-04-30 | Step 1 started | Implement shared HTTPS/local-certificate iBeam transport behavior. |
| 2026-04-30 | Step 1 targeted tests | `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal` passed (13/13) and `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passed (5/5). |
| 2026-04-30 | Step 1 complete | Shared HTTPS transport, local iBeam certificate scoping, AppHost/template alignment, and safe diagnostics implemented. |

---

## Blockers

*None*

---

## Notes

User-observed failure summary for implementer: refreshing IBKR market data in Aspire caused `GET /api/market-data/trending` to return 503 after both `IIbkrMarketDataClient` and `IIbkrGatewayClient` attempted `GET http://127.0.0.1:<gateway-port>/v1/api/iserver/auth/status` and hit `Connection reset by peer`, while iBeam reported the gateway was running/authenticated. Session/account details from the user log were intentionally omitted.

Step 0 sanitized failure evidence: reviewed PROMPT/STATUS and retained only endpoint path, loopback host placeholder, exception family, and high-level iBeam authenticated/running state; no raw credentials, session ids, cookies, account ids, tokens, or ignored `.env` values were read or recorded.

Step 0 real-runtime/simulation note: a no-secret probe against the default loopback gateway port (`http://127.0.0.1:5000/...` and `https://127.0.0.1:5000/...` with response bodies discarded) found no local listener (`curl exit=7` for both), so no real iBeam session was exercised. An automated local TLS simulation using a temporary self-signed certificate showed plain HTTP to a TLS-only loopback port returns an empty reply/reset-style transport failure, while `https://127.0.0.1:<temp-port>/...` with local certificate trust reaches an HTTPS response. This supports the HTTP-vs-HTTPS/TLS classification without real credentials.
