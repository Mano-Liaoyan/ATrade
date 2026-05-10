## Plan Review: Step 1 — Model opt-in Compose infrastructure mode

### Verdict: APPROVE

### Summary
The four checkboxes correctly map to the PROMPT.md Step 1 requirements. The approach — adding an `ATRADE_INFRASTRUCTURE_MODE` runtime variable, building localhost connection strings from the TP-069-established port values (`ATRADE_POSTGRES_PORT` et al.), keeping passwords secret via Aspire parameter plumbing, and validating consistently with the existing `LocalRuntimeContract` style — is sound and preserves the current AppHost-managed default. The plan stays properly scoped to mode modeling without leaking into graph-wiring concerns (those belong in Step 2).

### Issues Found
*None.* All PROMPT.md Step 1 requirements have a corresponding plan outcome.

### Missing Items
*None.* The four outcomes cover the stated requirements.

### Suggestions
- **Mode integration point:** The plan doesn't specify where the mode variable lives — consider integrating it into `LocalRuntimeContract` (add to `KnownVariableNames`, `LocalRuntimeContractDefaults`, and a new `LocalRuntimeInfrastructureSettings` record or a bare string field) rather than loading it as a standalone AppHost-side env read. This keeps validation, defaulting, and `.env.template` → `.env` → process-environment precedence consistent with the rest of the runtime contract.
- **Connection string format awareness:** The four infrastructure services use different connection string formats. Postgres and TimescaleDB use Npgsql format (`Host=127.0.0.1;Port=...;Username=postgres;Password=...;Database=postgres`). Redis uses `host:port` format. NATS uses `nats://host:port`. The step's helper file should produce each in the format Aspire's `WithReference` / `ConnectionStrings__*` plumbing expects. The TimescaleDB connection string is the same Npgsql format as Postgres, just on a different port (5433 by default).
- **TimescaleDB password reuse:** The existing `AppHostStorageContract` surfaces both `PostgresPassword` and `TimescalePassword` separately. The Compose-mode connection strings should use those same values so they stay consistent between modes (which matters if TP-071 cuts over the default without wiping volumes).
