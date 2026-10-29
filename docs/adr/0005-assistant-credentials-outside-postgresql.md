# AI assistant credentials stay in the assistant service, not in PostgreSQL or `.env`

The user enters model provider credentials (subscription logins and API keys)
in the web UI. The `assistant` service keeps them in a file with mode `0600`
in its own volume (`atrade-assistant-pi`). They do not go to PostgreSQL and
not to `.env`. The reasons: pi keeps only 1 credential for each provider, but
the user wants several API keys for one provider and selects one for each
conversation, so ATrade gives pi its own credential store; and the `web`
process and the database backups must not hold model keys. This is a
deliberate exception to section 15 of `docs/architecture.md` (secrets come
from environment variables). Decided in
[#140](https://github.com/Mano-Liaoyan/ATrade/issues/140).

## Considered options

- PostgreSQL: one backup for all data, but the database and its backups then
  hold model keys.
- `.env` only: follows section 15, but a new API key then needs a file
  change and a restart, and the user wants to add keys in the web UI.

## Consequences

- When the volume is lost, the user must log in and enter the API keys again.
- A backup of the volume holds credentials. Keep it like `.env`.
