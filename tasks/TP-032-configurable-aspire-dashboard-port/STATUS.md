# TP-032: Make Aspire dashboard port configurable from .env — Status

**Current Step:** Step 3: Add configuration and runtime regression coverage
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and naming decision
**Status:** ✅ Complete

- [x] Current dashboard/OTLP binding behavior inspected
- [x] Dashboard `.env` variable name chosen and recorded
- [x] OTLP configurability decision recorded
- [x] Default ephemeral behavior confirmed

---

### Step 1: Extend the local port contract
**Status:** ✅ Complete

- [x] `.env.template` defines dashboard HTTP port variable with `0`/ephemeral default
- [x] `LocalDevelopmentPortContract` parses optional dashboard port with `0` allowed
- [x] Existing required port validation preserved
- [x] Default/fixed/invalid dashboard port tests added
- [x] Variable remains non-secret and independent from broker settings

---

### Step 2: Apply the dashboard port in Unix and Windows start wrappers
**Status:** ✅ Complete

- [x] Unix `start.run.sh` exports dashboard `ASPNETCORE_URLS` from local contract
- [x] PowerShell `start.run.ps1` loads local contract and exports equivalent dashboard setting
- [x] PowerShell env loader added or equivalent parsing implemented without printing secrets
- [x] Existing wrapper errors/arguments/delegation preserved
- [x] OTLP default preserved unless evidence requires configurability

---

### Step 3: Add configuration and runtime regression coverage
**Status:** ✅ Complete

- [x] Local-port contract test covers non-zero dashboard port
- [x] Start-wrapper tests assert new variable/wrapper loading/safe launch defaults
- [x] Bounded AppHost dashboard-port smoke check added if feasible
- [x] Windows wrapper smoke expectations updated if needed
- [x] Targeted startup/config tests run

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `bash tests/start-contract/start-wrapper-tests.sh` passing
- [ ] `bash tests/apphost/local-port-contract-tests.sh` passing
- [ ] `bash tests/apphost/paper-trading-config-contract-tests.sh` passing
- [ ] `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh` passing
- [ ] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with variable name, default behavior, and OTLP decision

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Dashboard UI port variable will be `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT`. | Use as the committed `.env.template` non-secret setting and parse it through the local port contract. | Step 0 |
| OTLP dashboard endpoint remains `ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL=http://127.0.0.1:0`. | Do not add a second `.env` variable unless tests/runtime evidence later proves it is required. | Step 0 |
| Dashboard UI default will be `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0`. | Preserves current ephemeral loopback dashboard binding and allows ignored `.env` to opt into a fixed non-zero local port. | Step 0 |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 16:10 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 16:10 | Step 0 started | Preflight and naming decision |
| 2026-04-30 | Step 0 preflight | `launchSettings.json` binds Aspire dashboard UI via `ASPNETCORE_URLS=http://127.0.0.1:0` and OTLP via `ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL=http://127.0.0.1:0`. |
| 2026-04-30 | Step 1 started | Local port contract implementation started; existing Step 1 checklist is sufficiently hydrated. |
| 2026-04-30 | Step 1 targeted tests | `bash tests/apphost/local-port-contract-tests.sh` and `bash tests/apphost/paper-trading-config-contract-tests.sh` passed. |
| 2026-04-30 | Step 2 started | Start wrapper implementation started; existing Step 2 checklist is sufficiently hydrated. |
| 2026-04-30 | Step 2 targeted tests | `bash -n` wrapper syntax checks and `bash tests/start-contract/start-wrapper-tests.sh` passed; PowerShell syntax smoke skipped because `pwsh` is unavailable in this environment. |
| 2026-04-30 | Step 3 started | Runtime regression coverage started; existing Step 3 checklist is sufficiently hydrated. |
| 2026-04-30 | Step 3 targeted tests | `bash -n` startup/config scripts, `bash tests/start-contract/start-wrapper-tests.sh`, `bash tests/apphost/local-port-contract-tests.sh`, and `bash tests/apphost/paper-trading-config-contract-tests.sh` passed. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
