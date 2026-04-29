# TP-021: Wire iBeam runtime and `.env` credential contract for IBKR API login — Status

**Current Step:** Step 1: Update the committed environment templates without secrets
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-29
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] `.env` ignore and absence of committed real credentials confirmed
- [x] Previous Gateway image placeholder contract confirmed
- [x] iBeam env variable names verified before mapping

---

### Step 1: Update the committed environment templates without secrets
**Status:** ✅ Complete

- [x] `.env.example` updated with safe iBeam/IBKR placeholders
- [x] `.env.template` created or synchronized
- [x] `voyz/ibeam:latest` and gateway placeholders added safely
- [x] Credential placeholders are obviously fake and no real values are committed
- [x] `.gitignore` reviewed for `.env`

---

### Step 2: Wire `voyz/ibeam:latest` into AppHost safely
**Status:** ⬜ Not Started

- [ ] Environment contract loads new iBeam variables safely
- [ ] AppHost declares iBeam container when integration is enabled
- [ ] Secrets are not exposed in logs/status/resource names
- [ ] Existing AppHost resource wiring preserved
- [ ] Targeted AppHost resource tests pass

---

### Step 3: Extend broker options, worker status, and redaction
**Status:** ⬜ Not Started

- [ ] Broker env constants/options include new credential-bearing variables
- [ ] API/worker status distinguishes safe iBeam states
- [ ] Paper/data-only guardrails remain in force
- [ ] Redaction/live-mode tests cover new env names
- [ ] Targeted broker safety tests pass

---

### Step 4: Add iBeam runtime contract verification
**Status:** ⬜ Not Started

- [ ] iBeam runtime shell test added
- [ ] Env template safety verified
- [ ] `.env.template` and `.env.example` synchronization verified
- [ ] AppHost iBeam image/default-disabled behavior verified
- [ ] Status redaction verified

---

### Step 5: Update runtime and safety documentation
**Status:** ⬜ Not Started

- [ ] Startup docs updated for ignored `.env` and iBeam
- [ ] Paper-trading architecture updated for user-approved iBeam runtime
- [ ] Modules/overview/README reviewed and updated if stale

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker/iBeam-dependent runtime tests pass or cleanly skip
- [ ] All failures fixed
- [ ] Solution build passes

---

### Step 7: Documentation & Delivery
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
| Official iBeam docs verify `IBEAM_ACCOUNT` and `IBEAM_PASSWORD` as required runtime credentials, optional `IBEAM_KEY`, and example Docker port `5000:5000`; ATrade will map its own fake/ignored credential names to those container variables without committing real values. | Used as the verified environment mapping baseline for TP-021. | https://raw.githubusercontent.com/Voyz/ibeam/master/README.md and https://raw.githubusercontent.com/wiki/Voyz/ibeam/Runtime-environment.md |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-29 20:42 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 20:42 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
