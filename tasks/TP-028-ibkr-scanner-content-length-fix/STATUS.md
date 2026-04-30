# TP-028: Fix IBKR scanner 411 Length Required for trending — Status

**Current Step:** Step 2: Add scanner request-shape regression coverage
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and failure classification
**Status:** ✅ Complete

- [x] Sanitized `/api/market-data/trending` 411 failure recorded without secrets
- [x] Current scanner request shape inspected and likely root cause recorded
- [x] Fake-handler and optional real-iBeam verification plan recorded

---

### Step 1: Send a Client Portal-compatible scanner request
**Status:** ✅ Complete

- [x] Scanner request sends POST JSON with explicit positive `Content-Length` and no chunked transfer
- [x] Scanner payload semantics remain equivalent or source-evidenced corrections are documented
- [x] Safe provider error mapping and no-secrets diagnostics preserved
- [x] Scanner response parsing still maps valid fake IBKR responses to trending symbols
- [x] Targeted provider tests run

---

### Step 2: Add scanner request-shape regression coverage
**Status:** ✅ Complete

- [x] New focused scanner request contract test file added
- [x] Fake `411 Length Required` error mapping covered safely
- [x] Apphost/source contract scripts updated if needed
- [x] Targeted tests/scripts run

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
| Sanitized observed failure: `GET /api/market-data/trending` fails when the IBKR/iBeam scanner response is `411 Length Required` with an HTML edge/Akamai-style body; no credentials, account IDs, cookies, tokens, or session values were recorded. | Classify scanner request shape and fix provider transport. | Step 0 preflight |
| Current scanner implementation uses `HttpClient.PostAsJsonAsync` for `POST /v1/api/iserver/scanner/run` with JSON scanner payload (`instrument=STK`, `location=STK.US.MAJOR`, `type=TOP_PERC_GAIN`, empty `filter`). This preserves method/content-type/payload intent but does not guarantee a precomputed `Content-Length`; .NET may send streaming JSON with `Transfer-Encoding: chunked`, which is the likely Client Portal-incompatible shape behind the edge `411 Length Required`. | Replace scanner transport with buffered JSON content that explicitly sets a positive `Content-Length` and leaves chunked transfer disabled. | `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` |
| Verification plan: fake `HttpMessageHandler` tests can capture the scanner `HttpRequestMessage`, assert method/path/content-type/body/`Content-Length`/no chunked transfer, return fake scanner payloads, and return fake `411 Length Required` HTML bodies without any real IBKR credentials. Optional real iBeam verification will use ignored local `.env` plus `./start run` only if already configured/authenticated; otherwise record a clean skip rationale. | Cover request shape and error mapping in automated fake-handler tests; defer real-runtime smoke to Step 3. | `tests/ATrade.MarketData.Ibkr.Tests` / Step 3 |
| Scanner payload semantics were preserved while changing transport: the request still serializes `instrument=STK`, `location=STK.US.MAJOR`, `type=TOP_PERC_GAIN`, and an empty `filter` array. | No source-evidenced payload correction required for TP-028; regression coverage will assert the existing payload shape. | `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` |
| Provider error mapping remains `401/403` => `authentication-required` and other scanner failures (including `411`) => `provider-unavailable`; provider diagnostics now redact configured username, password, paper account id, and gateway URL/host before logging or returning scanner/status errors. | Regression tests will cover safe `411` response mapping and secret redaction. | `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` |
| Fake `411 Length Required` scanner responses are now covered by a provider-level regression test that asserts `provider-unavailable` and verifies configured username/password/account id, gateway host, token, and cookie snippets are absent from the returned error. | Safe error mapping coverage added. | `tests/ATrade.MarketData.Ibkr.Tests/IbkrScannerRequestContractTests.cs` |
| Apphost/source contract coverage now asserts the IBKR scanner client keeps buffered content, explicit `ContentLength`, `TransferEncodingChunked = false`, and the focused scanner request contract test file. | Updated `ibkr-market-data-provider-tests.sh`; `market-data-feature-tests.sh` did not need endpoint assertion changes for this source-level transport contract. | `tests/apphost/ibkr-market-data-provider-tests.sh` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 14:52 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 14:52 | Step 0 started | Preflight and failure classification |
| 2026-04-30 14:52 | Sanitized failure recorded | `/api/market-data/trending` scanner failure classified as safe `411 Length Required` HTML edge response without secrets. |
| 2026-04-30 14:52 | Scanner request inspected | Found `PostAsJsonAsync` scanner transport likely omits explicit `Content-Length` / may use chunked transfer despite otherwise-correct POST JSON payload. |
| 2026-04-30 14:52 | Verification plan recorded | Fake HTTP handlers can assert scanner request shape and safe `411` mapping; optional real iBeam smoke will be skipped unless local ignored credentials and authenticated runtime are available. |
| 2026-04-30 14:52 | Step 0 completed | Failure classified; root cause and verification approach recorded. |
| 2026-04-30 14:53 | Step 1 started | Implement Client Portal-compatible buffered scanner request. |
| 2026-04-30 14:53 | Scanner transport updated | Replaced scanner `PostAsJsonAsync` with buffered `HttpRequestMessage` JSON content, explicit positive `Content-Length`, and chunked transfer disabled. |
| 2026-04-30 14:53 | Scanner payload preserved | Kept existing top-percent-gainer stock scanner semantics while changing only request buffering/headers. |
| 2026-04-30 14:53 | Provider diagnostics preserved | Kept auth/unavailable mapping and added configured-value redaction before provider messages are logged or returned. |
| 2026-04-30 14:54 | Scanner parsing verified | `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --filter FullyQualifiedName~Provider_MapsContractLookupSnapshotsHistoricalBarsAndScannerResults` passed (1/1). |
| 2026-04-30 14:54 | Step 1 targeted tests run | `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passed (8/8). |
| 2026-04-30 14:54 | Step 1 completed | Scanner transport, payload preservation, safe error mapping, parsing, and targeted provider tests completed. |
| 2026-04-30 14:55 | Step 2 started | Add scanner request-shape and `411` regression coverage. |
| 2026-04-30 14:55 | Scanner request contract test added | Added `IbkrScannerRequestContractTests` and verified the request-shape test passes with explicit JSON content length and no chunked transfer. |
| 2026-04-30 14:56 | Safe `411` mapping test added | `Provider_ConvertsScannerLengthRequiredToSafeUnavailableErrorWithoutLeakingConfiguredSecrets` passed and covers sanitized provider-unavailable mapping. |
| 2026-04-30 14:56 | Source contract script updated | `ibkr-market-data-provider-tests.sh` now asserts scanner buffered/content-length/no-chunked contract tokens; `bash -n` passed. |
| 2026-04-30 14:57 | Step 2 targeted tests/scripts run | `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passed (10/10); `bash tests/apphost/ibkr-market-data-provider-tests.sh` passed (`SCRIPT_EXIT:0`). |
| 2026-04-30 14:57 | Step 2 completed | Added request-shape regression coverage, safe `411` coverage, source-contract assertions, and targeted script verification. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
