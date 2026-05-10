## Plan Review: Step 2 — Add the Compose infrastructure definition

### Verdict: APPROVE

### Summary
The 4 outcome-level checkboxes map cleanly to the 4 core requirements from PROMPT.md:
default infra services, durable named volumes, AppHost safety-mirroring, and optional
ibkr/lean profiles. The worker demonstrated thorough understanding of the codebase in
Step 1 (the `LocalRuntimeContract`, `.env.template`, and AppHost `Program.cs` patterns)
and is well-positioned to author a correct `compose.yaml`. The plan is coherent and the
scope is appropriately constrained to one new file.

### Issues Found
*None at the outcome level that would block progress. See Suggestions for wording
refinements that would reduce implementation risk.*

### Missing Items
*None.* All 4 PROMPT.md Step 2 requirements are represented.

### Suggestions
- **Checkbox 1 wording:** The PROMPT explicitly requires services be "bound to
  `127.0.0.1`" — not `0.0.0.0`. This is a security guardrail (no accidental LAN
  exposure of Postgres/Redis/NATS). Consider making this explicit in the checkbox
  (e.g., "Create default … services bound to `127.0.0.1` on configured
  `ATRADE_*_PORT` values") so the loopback requirement isn't accidentally missed.
- **Checkbox 4 wording:** The PROMPT calls out three structural requirements beyond
  variable reuse: "iBeam inputs mount, LEAN workspace mount, stable LEAN container
  name." The current wording "using existing runtime variables" could lead to
  forgetting these mount/container-name requirements. Consider adding them to the
  checkbox.
- **Volumes declaration:** Compose requires a top-level `volumes:` section to use
  named volumes like `ATRADE_POSTGRES_DATA_VOLUME` and
  `ATRADE_TIMESCALEDB_DATA_VOLUME`. This is an implementation detail but an easy
  one to miss — the worker should remember to declare these at the file root, not
  just in service definitions.
- **AppHost alignment:** The worker should match the AppHost's
  `timescale/timescaledb:latest-pg17` image tag in Compose so volume data remains
  compatible across the Aspire→Compose cutover. Similarly, the iBeam profile should
  mirror the AppHost's `IBEAM_ACCOUNT` / `IBEAM_PASSWORD` container env mapping
  (the bridge between `ATRADE_IBKR_USERNAME`/`PASSWORD` and the iBeam container)
  and the `PYTHONDONTWRITEBYTECODE=1` / `tail -f /dev/null` LEAN engine idle
  contract.
