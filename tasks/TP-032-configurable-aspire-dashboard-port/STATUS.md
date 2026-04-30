# TP-032: Make Aspire dashboard port configurable from .env — Status

**Current Step:** Step 0: Preflight and naming decision
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
**Status:** ⬜ Not Started

- [ ] `.env.template` defines dashboard HTTP port variable with `0`/ephemeral default
- [ ] `LocalDevelopmentPortContract` parses optional dashboard port with `0` allowed
- [ ] Existing required port validation preserved
- [ ] Default/fixed/invalid dashboard port tests added
- [ ] Variable remains non-secret and independent from broker settings

---

### Step 2: Apply the dashboard port in Unix and Windows start wrappers
**Status:** ⬜ Not Started

- [ ] Unix `start.run.sh` exports dashboard `ASPNETCORE_URLS` from local contract
- [ ] PowerShell `start.run.ps1` loads local contract and exports equivalent dashboard setting
- [ ] PowerShell env loader added or equivalent parsing implemented without printing secrets
- [ ] Existing wrapper errors/arguments/delegation preserved
- [ ] OTLP default preserved unless evidence requires configurability

---

### Step 3: Add configuration and runtime regression coverage
**Status:** ⬜ Not Started

- [ ] Local-port contract test covers non-zero dashboard port
- [ ] Start-wrapper tests assert new variable/wrapper loading/safe launch defaults
- [ ] Bounded AppHost dashboard-port smoke check added if feasible
- [ ] Windows wrapper smoke expectations updated if needed
- [ ] Targeted startup/config tests run

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
