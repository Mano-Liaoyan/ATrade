# TP-006: Replace the placeholder frontend with the first Next.js slice — Status

**Current Step:** Step 4: Update docs
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-22
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the current frontend, AppHost, test, and architecture files
- [x] Confirm `frontend/` is still the placeholder Node server
- [x] Confirm the AppHost frontend resource still targets `npm run dev`

---

### Step 1: Scaffold the Next.js app
**Status:** ✅ Complete

- [x] Convert `frontend/` into a minimal Next.js application
- [x] Keep `npm run dev` as the frontend entrypoint
- [x] Add the necessary Next.js config and app files
- [x] Replace the placeholder server with a real page at `/`
- [x] Expose stable visible text markers for shell smoke tests
- [x] Ignore Next.js local build artifacts and dependencies

---

### Step 2: Keep AppHost orchestration working
**Status:** ✅ Complete

- [x] Update `src/ATrade.AppHost/Program.cs` only as needed
- [x] Preserve the existing API + frontend bootstrap graph
- [x] Keep infra resources out of scope

---

### Step 3: Add smoke coverage
**Status:** ✅ Complete

- [x] Create `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [x] Verify direct frontend startup and page markers
- [x] Update `tests/start-contract/start-wrapper-tests.sh` for the Next.js contract

---

### Step 4: Update docs
**Status:** 🟨 In Progress

- [ ] Update `scripts/README.md`
- [ ] Update `docs/architecture/modules.md`
- [ ] Update `docs/architecture/overview.md` if current-slice wording changed
- [ ] Update `README.md` if current-status wording changed

---

### Step 5: Verification
**Status:** ⬜ Not Started

- [ ] `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `dotnet build ATrade.sln`
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
| AppHost JavaScript resource did not need a `Program.cs` change because `AddJavaScriptApp("frontend", "../../frontend", "dev")` still launches `npm run dev` with the existing `PORT` endpoint wiring. | Verified by direct AppHost startup smoke; keep `src/ATrade.AppHost/Program.cs` unchanged. | `src/ATrade.AppHost/Program.cs` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-22 23:54 | Task started | Runtime V2 lane-runner execution |
| 2026-04-22 23:54 | Step 0 started | Preflight |
| 2026-04-23 | Step 2 graph verification | Confirmed `src/ATrade.AppHost/Program.cs` still declares both `api` and `frontend` Aspire resources. |
| 2026-04-23 | Step 2 scope verification | Confirmed the AppHost change set adds no Aspire infra resources beyond the existing API + frontend graph. |

---

## Blockers

*None*

---

## Notes

*Goal: swap the placeholder frontend runtime for a minimal real Next.js app while keeping the current API + AppHost bootstrap contract intact.*
