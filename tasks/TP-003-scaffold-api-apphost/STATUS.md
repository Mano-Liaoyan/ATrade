# TP-003: Scaffold `ATrade.Api` and wire it into AppHost — Status

**Current Step:** Step 6: Delivery
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-22
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the listed docs and current AppHost / ServiceDefaults / test files
- [x] Confirm `src/ATrade.Api/` does not yet exist
- [x] Confirm `ATrade.sln` does not yet include an API project
- [x] Confirm the current AppHost graph only launches the placeholder frontend

---

### Step 1: Scaffold `src/ATrade.Api`
**Status:** ✅ Complete

- [x] Create `src/ATrade.Api/ATrade.Api.csproj`
- [x] Create `src/ATrade.Api/Program.cs`
- [x] Add `ATrade.Api` to `ATrade.sln`
- [x] Reference `ATrade.ServiceDefaults`
- [x] Expose `GET /health` with a stable success response

---

### Step 2: Wire shared defaults and AppHost
**Status:** ✅ Complete

- [x] Add the minimum shared extension code in `src/ATrade.ServiceDefaults/Extensions.cs`
- [x] Update `src/ATrade.AppHost/ATrade.AppHost.csproj` for API project wiring
- [x] Update `src/ATrade.AppHost/Program.cs` to launch `ATrade.Api` and the frontend
- [x] Keep infra resources out of scope

---

### Step 3: Add regression coverage
**Status:** ✅ Complete

- [x] Create `tests/apphost/api-bootstrap-tests.sh`
- [x] Verify direct API smoke coverage for `GET /health`
- [x] Update `tests/start-contract/start-wrapper-tests.sh` only if the new graph changes expected bootstrap behavior

---

### Step 4: Update docs
**Status:** ✅ Complete

- [x] Update `scripts/README.md`
- [x] Update `docs/architecture/modules.md`
- [x] Update `docs/architecture/overview.md` if bootstrap-status wording changed
- [x] Update `README.md` if current runnable-slice wording changed

---

### Step 5: Verification
**Status:** ✅ Complete

- [x] `dotnet build ATrade.sln`
- [x] `bash tests/start-contract/start-wrapper-tests.sh`
- [x] `bash tests/apphost/api-bootstrap-tests.sh`
- [x] `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- [x] `timeout 20s ./start run`

---

### Step 6: Delivery
**Status:** 🟨 In Progress

- [ ] Commit with conventions

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
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-22 23:14 | Task started | Runtime V2 lane-runner execution |
| 2026-04-22 23:14 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*First implementation slice after the architecture docs: scaffold one minimal API project, keep infra and domain logic out of scope, and preserve the existing placeholder frontend bootstrap.*
