# TP-012: Externalize local port allocation into a repo `.env` contract — Status

**Current Step:** Step 1: Define the `.env` contract
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-24
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Inventory current port literals and classify them correctly
- [x] Confirm whether a repo `.env` contract already exists
- [x] Confirm how AppHost and tests currently obtain their ports

---

### Step 1: Define the `.env` contract
**Status:** 🟨 In Progress

- [ ] Choose the committed template/local-file shape
- [ ] Define clear variables for developer-controlled ports
- [ ] Preserve intentionally ephemeral internal ports where appropriate
- [ ] Document fallback behavior when `.env` is absent

---

### Step 2: Wire AppHost and startup paths to the env contract
**Status:** ⏳ Not started

- [ ] Update AppHost/startup code to read the env-driven port values
- [ ] Centralize the relevant frontend/api/infra runtime path configuration
- [ ] Avoid regressing TP-010 / TP-011 fixes

---

### Step 3: Wire tests to the same source of truth
**Status:** ⏳ Not started

- [ ] Update affected test harnesses to use the shared env contract
- [ ] Remove stale duplicated port assumptions where appropriate
- [ ] Keep CI deterministic

---

### Step 4: Verification
**Status:** ⏳ Not started

- [ ] Prove the `.env` contract is actually consumed
- [ ] Verify direct API/frontend startup still works
- [ ] Verify AppHost manifest/runtime checks still pass
- [ ] Verify at least one changed env port propagates correctly

---

### Step 5: Documentation
**Status:** ⏳ Not started

- [ ] Update `scripts/README.md`
- [ ] Update `README.md` / `PLAN.md` only if wording would otherwise be stale

---

### Step 6: Final verification
**Status:** ⏳ Not started

- [ ] Run the affected tests
- [ ] Confirm the repo still boots with defaults
- [ ] Confirm the env contract is the single source of truth for developer-controlled local ports

---

### Step 7: Delivery
**Status:** ⏳ Not started

- [ ] Commit with conventions

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Port inventory classified: developer bind ports = `5181` (API direct-start), `3111` (frontend direct-start), `3000` (AppHost frontend); service target ports = `5432`/`6379`/`4222` plus frontend target `3000`; intentionally ephemeral internal ports = AppHost `127.0.0.1:0` launch settings. | Use `.env` only for developer-controlled bind values; keep service/internal ports in code where they are protocol- or runtime-defined. | `tests/apphost/api-bootstrap-tests.sh`, `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, `src/ATrade.AppHost/Program.cs`, `src/ATrade.AppHost/Properties/launchSettings.json` |
| Repo-level `.env` contract does not exist yet; `find .env*` returned no files and `.gitignore` already ignores developer-local `.env`. | Add a committed template (likely `.env.example`) plus fallback defaults instead of committing a machine-specific `.env`. | `.gitignore`, repository root |
| Current port acquisition is split: AppHost sets frontend `PORT` via `.WithHttpEndpoint(targetPort: 3000, env: "PORT")`; API direct-start test hard-codes `ASPNETCORE_URLS=http://127.0.0.1:5181`; frontend direct-start test derives `PORT` from `frontend_url=3111`; launch settings keep AppHost internals on `127.0.0.1:0`. | Replace duplicated developer-facing literals with a shared env/default helper while preserving the intentionally ephemeral AppHost internal endpoints. | `src/ATrade.AppHost/Program.cs`, `tests/apphost/api-bootstrap-tests.sh`, `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, `src/ATrade.AppHost/Properties/launchSettings.json` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-24 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-24 14:36 | Task started | Runtime V2 lane-runner execution |
| 2026-04-24 14:36 | Step 0 started | Preflight |
| 2026-04-24 14:44 | Port inventory captured | Classified current literals into bind, service-target, and intentionally ephemeral buckets from AppHost/test sources |
| 2026-04-24 14:45 | Env contract checked | Verified there is no committed repo `.env` template or live contract; only `.gitignore` has a local `.env` ignore rule |
| 2026-04-24 14:46 | Port source paths confirmed | Captured how AppHost, launch settings, and direct-start tests currently obtain their ports and which values are duplicated |
| 2026-04-24 14:46 | Step 0 completed | Preflight inventory recorded in STATUS discoveries |
| 2026-04-24 14:46 | Step 1 started | Defining the repo-level `.env` contract |

---

## Blockers

*None yet*

---

## Notes

*Goal: make local port allocation env-driven and centralized without freezing ports that should remain dynamic by design.*
