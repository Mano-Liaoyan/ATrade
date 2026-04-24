# TP-012: Externalize local port allocation into a repo `.env` contract — Status

**Current Step:** Step 2: Wire AppHost and startup paths to the env contract
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
**Status:** ✅ Complete

- [x] Choose the committed template/local-file shape
- [x] Define clear variables for developer-controlled ports
- [x] Preserve intentionally ephemeral internal ports where appropriate
- [x] Document fallback behavior when `.env` is absent

---

### Step 2: Wire AppHost and startup paths to the env contract
**Status:** 🟨 In Progress

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
| Chosen contract shape: committed repo-root `.env.example` plus ignored developer-local `.env`. | Keep portable defaults committed while allowing per-machine overrides in `.env`. | `.env.example`, `.gitignore` |
| Defined contract variables: `ATRADE_API_HTTP_PORT`, `ATRADE_FRONTEND_DIRECT_HTTP_PORT`, and `ATRADE_APPHOST_FRONTEND_HTTP_PORT`. | Use explicit names tied to the direct API path, direct frontend path, and AppHost-managed frontend path. | `.env.example` |
| Intentionally ephemeral/internal ports remain outside the contract. | `.env.example` now explicitly leaves AppHost `127.0.0.1:0` internals and service target ports (`5432`/`6379`/`4222`) in code instead of freezing them in `.env`. | `.env.example`, `src/ATrade.AppHost/Properties/launchSettings.json`, `src/ATrade.AppHost/Program.cs` |
| Fallback behavior is defined at the contract boundary. | `.env.example` documents that local startup and test helpers should use the committed template values whenever a developer-local `.env` file is absent. | `.env.example` |

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
| 2026-04-24 14:48 | Env template shape chosen | Added repo-root `.env.example` to define the contract while keeping `.env` developer-local |
| 2026-04-24 14:49 | Env variables defined | Added explicit developer-controlled port variable names to `.env.example` |
| 2026-04-24 14:50 | Ephemeral ports preserved | Documented the ports intentionally excluded from the repo-level env contract |
| 2026-04-24 14:50 | Fallback contract documented | Recorded that `.env.example` supplies the default local-port values when `.env` is absent |
| 2026-04-24 14:50 | Step 1 completed | Repo-level env contract shape and variables recorded |
| 2026-04-24 14:50 | Step 2 started | Wiring AppHost and direct startup paths to the shared env contract |

---

## Blockers

*None yet*

---

## Notes

*Goal: make local port allocation env-driven and centralized without freezing ports that should remain dynamic by design.*
