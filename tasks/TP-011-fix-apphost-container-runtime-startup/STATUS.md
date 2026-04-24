# TP-011: Fix AppHost-managed container startup under a Podman-backed Docker API — Status

**Current Step:** Step 0: Preflight
**Status:** ⏳ Not started
**Last Updated:** 2026-04-24
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 0
**Size:** M

---

### Step 0: Preflight
**Status:** ⏳ Not started

- [ ] Reproduce/confirm the AppHost-created container runtime state in this repo
- [ ] Confirm the effective `pids.max` problem on AppHost-created infra containers
- [ ] Confirm the TimescaleDB tuning-script failure mode after pids are fixed

---

### Step 1: Fix process limits for AppHost-managed containers
**Status:** ⏳ Not started

- [ ] Update the AppHost resource configuration so infra containers do not inherit the broken default pids behavior
- [ ] Use an explicit, readable container runtime configuration rather than a hidden machine tweak
- [ ] Apply the fix consistently to the AppHost-managed infra resources that need it

---

### Step 2: Fix TimescaleDB startup for rootless Podman compatibility
**Status:** ⏳ Not started

- [ ] Make `timescaledb` start cleanly under the same runtime path after the pids fix
- [ ] Prefer deterministic tuning inputs or another real configuration fix over hiding the problem
- [ ] Keep the resource in the AppHost graph

---

### Step 3: Preserve the bootstrap graph
**Status:** ⏳ Not started

- [ ] Keep the existing AppHost graph names and roles intact
- [ ] Do not replace Aspire with ad-hoc scripts or `docker compose`
- [ ] Avoid unrelated consumer wiring

---

### Step 4: Add verification
**Status:** ⏳ Not started

- [ ] Add runtime-focused AppHost infrastructure verification when an engine is available
- [ ] Verify affected containers get a real pids limit (`pids.max > 1`)
- [ ] Verify `postgres` and `timescaledb` actually start through the AppHost path
- [ ] Preserve the manifest-based verification path

---

### Step 5: Update docs
**Status:** ⏳ Not started

- [ ] Update `scripts/README.md`
- [ ] Update `README.md` / `PLAN.md` only if wording would otherwise be stale

---

### Step 6: Verification
**Status:** ⏳ Not started

- [ ] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run the new runtime-focused AppHost infrastructure verification
- [ ] Confirm the original startup failure class is resolved

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

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-24 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None yet*

---

## Notes

*Goal: make the AppHost-managed infra resources start reliably under the operator's current container-runtime path instead of failing in entrypoint scripts and cgroup probing.*
