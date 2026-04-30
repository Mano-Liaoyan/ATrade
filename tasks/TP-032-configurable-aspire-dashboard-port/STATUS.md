# TP-032: Make Aspire dashboard port configurable from .env — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-30
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and naming decision
**Status:** ⬜ Not Started

- [ ] Current dashboard/OTLP binding behavior inspected
- [ ] Dashboard `.env` variable name chosen and recorded
- [ ] OTLP configurability decision recorded
- [ ] Default ephemeral behavior confirmed

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
