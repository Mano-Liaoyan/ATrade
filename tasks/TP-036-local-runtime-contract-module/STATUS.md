# TP-036: Deepen the local runtime contract module — Status

**Current Step:** Step 2: Deepen shared env parsing and resolved contract interface
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-02
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Inventory and fix committed contract drift
**Status:** ✅ Complete

- [x] Runtime defaults compared across template, shims, docs, and tests
- [x] Safe paper-only committed defaults restored and documented
- [x] New runtime-contract drift test added
- [x] Targeted startup/config contract tests passing

---

### Step 2: Deepen shared env parsing and resolved contract interface
**Status:** ✅ Complete

> ⚠️ Hydrate: Expand checkboxes when entering this step based on the chosen shared module location and existing contract reader call sites.

- [x] `ATrade.ServiceDefaults` shared local runtime contract loader added for `.env.template`/`.env` parsing, process overlay, defaults, validation, and secret classification
- [x] Local port, AppHost storage, paper trading, and LEAN contract readers adapted to the shared loader with duplicate parser implementations removed
- [x] Resolved contract values preserve broker/iBeam, LEAN, database, API/frontend/dashboard behavior while keeping credential-bearing values classified as secret
- [x] Targeted .NET contract tests added/passing for overlay, defaults, validation, and secret/non-secret handling

---

### Step 3: Project resolved contract values into startup shims and AppHost
**Status:** ⬜ Not Started

- [ ] Startup shims and AppHost use consistent resolved defaults
- [ ] `start run` contract preserved on Unix and Windows shims
- [ ] AppHost environment handoff preserves broker/iBeam, LEAN, database, API, and frontend behavior
- [ ] Targeted AppHost/start-contract tests passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Integration/contract tests passing or cleanly skipped where applicable
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
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
| Prompt/file-scope references `scripts/start.run.cmd`, but the repository's committed Windows cmd shim is root `start.cmd`; `scripts/start.run.ps1` is the delegated Windows script. | Treat root `start.cmd` plus `scripts/start.run.ps1` as the Windows cmd/PowerShell startup surface unless implementation discovers a real need for a new delegated cmd script. | Preflight / `scripts/README.md` planned layout |
| Default drift found in `.env.template`: ports use high lane values (`15181`/`13111`/`13000`/dashboard `10001`), broker integration defaults `true`, iBeam host URL/port use `15000`, frontend API URLs use `15181`, and cache freshness is `10`; docs and tests expect safe shared defaults (`5181`/`3111`/`3000`/dashboard `0`, broker `false`, iBeam `https://127.0.0.1:5000`, cache freshness `30`). | Restore `.env.template` to documented/tested paper-safe defaults and add a drift test so future changes fail fast. | `.env.template`, `README.md`, `scripts/README.md`, `tests/start-contract/start-wrapper-tests.sh`, `tests/apphost/paper-trading-config-contract-tests.sh`, architecture docs |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-02 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-02 13:51 | Task started | Runtime V2 lane-runner execution |
| 2026-05-02 13:51 | Step 0 started | Preflight |
| 2026-05-02 16:00 | Step 0 completed | Preflight files/dependencies verified; `scripts/start.run.cmd` prompt mismatch logged as discovery. |
| 2026-05-02 16:01 | Step 1 started | Inventorying committed runtime defaults across template, startup shims, tests, and active docs. |
| 2026-05-02 16:04 | Runtime drift inventory | Compared `.env.template`, startup shims, existing contract tests, README/PLAN/scripts docs, and active architecture docs; drift isolated to committed template defaults while docs/tests already describe the paper-safe contract. |
| 2026-05-02 16:07 | Paper-safe defaults restored | `.env.template` now matches documented defaults: API `5181`, direct frontend `3111`, AppHost frontend `3000`, dashboard `0`, broker integration `false`, iBeam HTTPS port `5000`, frontend API `5181`, and cache freshness `30`; `scripts/README.md` now documents the committed port defaults. |
| 2026-05-02 16:12 | Drift test added | Added `tests/apphost/local-runtime-contract-module-tests.sh`; `bash -n` and the new test passed locally. |
| 2026-05-02 16:16 | Step 1 targeted tests | `bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/start-contract/start-wrapper-tests.sh` passed. |
| 2026-05-02 16:17 | Step 1 completed | Committed defaults, docs, drift test, and targeted startup/config contract tests are aligned on paper-safe runtime defaults. |
| 2026-05-02 16:18 | Step 2 hydrated | Chosen shared module location: `src/ATrade.ServiceDefaults`; AppHost contract readers will adapt to that loader while preserving public record shapes. |
| 2026-05-02 16:28 | Shared loader implemented | Added `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` with template/.env/process overlays, built-in safe defaults, port/volume validation, resolved settings records, and secret classification for credential/password/account-id values; AppHost project build passed after the shared loader change. |
| 2026-05-02 16:30 | Contract readers adapted | `LocalDevelopmentPortContractLoader`, AppHost storage, paper-trading, and LEAN contract records now map from `LocalRuntimeContract`; grep confirms duplicate `ParseEnvironmentFile` implementations remain only in the shared loader. |
| 2026-05-02 16:39 | Resolved contract behavior verified | New ServiceDefaults tests verify overlay order, safe built-in defaults, port/volume validation, frontend URL derivation, LEAN path normalization, and secret classification for database passwords plus IBKR username/password/account id. |
| 2026-05-02 16:40 | Step 2 targeted .NET tests | `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal` passed (9 tests); `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal` passed after adapter changes. |
| 2026-05-02 16:41 | Step 2 completed | Shared ServiceDefaults runtime contract loader owns .NET env parsing/resolution; duplicate AppHost/port parsing was removed or isolated behind adapters. |

---

## Blockers

*None*

---

## Notes

- Preflight dependency check: `dotnet 10.0.203`, GNU bash 5.3.9, git 2.54.0, node v24.15.0/npm 11.12.1, Docker 29.3.0-ce, Podman 5.8.1 available; `pwsh` is not installed locally, so Windows PowerShell wrapper coverage remains via repository Windows harness/CI.

