# TP-003: Scaffold `ATrade.Api` and wire it into AppHost — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-23
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Read the listed docs and current AppHost / ServiceDefaults / test files
- [ ] Confirm `src/ATrade.Api/` does not yet exist
- [ ] Confirm `ATrade.sln` does not yet include an API project
- [ ] Confirm the current AppHost graph only launches the placeholder frontend

---

### Step 1: Scaffold `src/ATrade.Api`
**Status:** ⬜ Not Started

- [ ] Create `src/ATrade.Api/ATrade.Api.csproj`
- [ ] Create `src/ATrade.Api/Program.cs`
- [ ] Add `ATrade.Api` to `ATrade.sln`
- [ ] Reference `ATrade.ServiceDefaults`
- [ ] Expose `GET /health` with a stable success response

---

### Step 2: Wire shared defaults and AppHost
**Status:** ⬜ Not Started

- [ ] Add the minimum shared extension code in `src/ATrade.ServiceDefaults/Extensions.cs`
- [ ] Update `src/ATrade.AppHost/ATrade.AppHost.csproj` for API project wiring
- [ ] Update `src/ATrade.AppHost/Program.cs` to launch `ATrade.Api` and the frontend
- [ ] Keep infra resources out of scope

---

### Step 3: Add regression coverage
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/api-bootstrap-tests.sh`
- [ ] Verify direct API smoke coverage for `GET /health`
- [ ] Update `tests/start-contract/start-wrapper-tests.sh` only if the new graph changes expected bootstrap behavior

---

### Step 4: Update docs
**Status:** ⬜ Not Started

- [ ] Update `scripts/README.md`
- [ ] Update `docs/architecture/modules.md`
- [ ] Update `docs/architecture/overview.md` if bootstrap-status wording changed
- [ ] Update `README.md` if current runnable-slice wording changed

---

### Step 5: Verification
**Status:** ⬜ Not Started

- [ ] `dotnet build ATrade.sln`
- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `bash tests/apphost/api-bootstrap-tests.sh`
- [ ] `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- [ ] `timeout 20s ./start run`

---

### Step 6: Delivery
**Status:** ⬜ Not Started

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

---

## Blockers

*None*

---

## Notes

*First implementation slice after the architecture docs: scaffold one minimal API project, keep infra and domain logic out of scope, and preserve the existing placeholder frontend bootstrap.*
