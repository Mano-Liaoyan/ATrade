# ATrade

ATrade is a personal trading platform for one user. It finds instruments,
shows bar charts, tests strategies on history and on live market data, and
sends paper orders to the IBKR paper account.

The architecture specification is [`docs/architecture.md`](docs/architecture.md).
Terms have the meaning that [`GLOSSARY.md`](GLOSSARY.md) gives them. The plan
is in GitHub Issues.

## Current state

The repository holds the minimum runnable skeleton (issue #62), the IBKR
connection (issue #63), instrument search (issue #64), the strategy editor
(issue #68), and code completion (issue #69):

- The `web` service serves the app shell, `GET /api/health`,
  `GET /api/ibkr/gateway`, the strategy routes under `/api/strategies`, and the
  language server WebSocket `/ws/strategy-language-server`.
- The app shell header shows the backend status and the IB Gateway status.
- The `web` service connects to IB Gateway and connects again after a lost
  connection. It starts also when the Gateway is not reachable.
- The `ib-gateway` service runs IB Gateway for the IBKR paper account. It is
  in the Compose profile `ibkr`.
- The `postgres` service holds the database.
- Instrument search: the home page finds instruments by symbol through
  IB Gateway and shows each match as symbol / exchange / currency, for
  example `700 / SEHK / HKD`. The search needs a connected IB Gateway. See
  [`docs/architecture/market_data.md`](docs/architecture/market_data.md).
- Strategies: the page `/strategies` creates a strategy from a template. The
  editor saves the code as strategy versions after the checks before save.
  Unsaved edits stay in the browser. The editor shows code completion and
  live type errors from basedpyright. Type errors do not block the save. See
  [`docs/architecture/strategy.md`](docs/architecture/strategy.md).
- Bars, watchlist, backtests, paper trading, and forward tests are not
  available yet.

## Requirements

- Unix, or Windows through WSL. There is no native Windows start script.
- Docker with Docker Compose v2.

For development and checks, also:

- [uv](https://docs.astral.sh/uv/) 0.13. uv installs Python 3.14.
- Node.js 24 and pnpm 10.

## Run ATrade

1. Copy `.env.example` to `.env`.
2. Replace the placeholder values in `.env`. Do not commit `.env`.
3. Start all services:

   ```sh
   ./start run
   ```

4. Open <http://127.0.0.1:8000> (or the port in `ATRADE_WEB_PORT`).

### Connect to the IBKR paper account

Without IB Gateway, ATrade starts, and the header shows "IB Gateway not
reachable". To connect:

1. In `.env`, set `COMPOSE_PROFILES=ibkr`.
2. Set `ATRADE_IBKR_USERNAME` and `ATRADE_IBKR_PASSWORD` to the login of the
   IBKR paper account. Set `ATRADE_IBKR_ACCOUNT_ID` to the paper account
   number (it starts with `DU`).
3. Run `./start run`. The header shows "IB Gateway connected." after the
   Gateway has logged in.

A login on the IBKR website or phone app with the same user name competes
with the Gateway session.

`./start run` runs `docker compose up --build` with `deploy/compose.yaml` and
`.env`. It sends other arguments to `docker compose up`. For example,
`./start run -d` starts the services in the background. When `.env` is not
there, `./start run` writes a warning and uses the placeholder values in
`.env.example`.

To stop the services:

```sh
docker compose --file deploy/compose.yaml --env-file .env down
```

With `COMPOSE_PROFILES=ibkr` in `.env`, this command also stops `ib-gateway`.

### Services

| Service | Content |
|---|---|
| `postgres` | PostgreSQL 18. Volume `atrade-pgdata`. Not published outside the Compose network. |
| `ib-gateway` | IB Gateway and IBC, logged in to the paper account. Profile `ibkr`. The API port (`ib-gateway:4004`) is not published outside the Compose network. |
| `web` | FastAPI app (`python -m atrade.app.web`) and the built frontend. Port `127.0.0.1:${ATRADE_WEB_PORT}`. Memory limit, read-only root file system, writable `/tmp`. |

At start, `web` runs the Alembic migrations. When `ATRADE_TRADING_MODE` is
`live`, `web` does not start and writes the reason.

Rootless Podman without the memory cgroup controller cannot set a memory
limit. On such a host, set `ATRADE_WEB_MEMORY_LIMIT=0` in `.env`.

### Old data

The rewrite migrates no old data. The new database uses the new volume
`atrade-pgdata`. The old PostgreSQL volume and the old containers are not
used. To remove them, do these steps by hand. This deletes the old data
permanently.

```sh
docker volume ls | grep -i atrade      # find the old volumes, for example atrade-postgres-data
docker volume rm <old volume name>
```

## Check the code

One command runs the same checks as CI:

```sh
./scripts/check            # all checks
./scripts/check backend    # ruff, basedpyright, import-linter, file length, pytest
./scripts/check frontend   # API types, ESLint, svelte-check, Vitest, build
./scripts/check e2e        # Playwright
```

- The tests need a real PostgreSQL. When `ATRADE_TEST_DATABASE_URL` is not
  set, `./scripts/check` starts a temporary `postgres:18.3` container and
  removes it at exit.
- Playwright runs 4 projects: chromium, firefox, webkit, msedge. Set
  `ATRADE_PLAYWRIGHT_PROJECTS` to the browsers on your machine, for example
  `ATRADE_PLAYWRIGHT_PROJECTS="chromium firefox"`. The value `none` skips the
  end-to-end tests. Install browsers with
  `pnpm --dir frontend exec playwright install`.
- Real IBKR tests have the pytest mark `ibkr_paper`. CI does not run them,
  and the default pytest options leave them out. Run them by hand with
  `cd backend && uv run pytest -m ibkr_paper`. They read `.env`, and they skip
  when `.env`, `ATRADE_IBKR_ACCOUNT_ID`, or IB Gateway is not available. The
  Gateway port is not published, so set `ATRADE_IBKR_HOST` and
  `ATRADE_IBKR_PAPER_PORT` to an address that you can reach, for example an
  SSH tunnel. See `docs/architecture/ibkr.md` section 7.5.

## Generate the API types

The frontend API types come from the OpenAPI document of the backend. After a
change to an HTTP route or to its request or response model, run:

```sh
cd frontend && pnpm generate:api
```

This writes `frontend/src/lib/api/openapi.json` and
`frontend/src/lib/api/index.ts`. Commit both files. A backend test fails when
`openapi.json` does not match the routes. `pnpm check:api` (in
`./scripts/check frontend`) fails when `index.ts` does not match
`openapi.json`.

## Development without Docker

```sh
cd backend && uv sync
DATABASE_URL=postgresql://... ATRADE_FRONTEND_BUILD_DIR=../frontend/build uv run python -m atrade.app.web
cd frontend && pnpm install && pnpm dev    # sends /api and /ws to 127.0.0.1:8000
```

## Repository layout

```
backend/
  src/atrade/        # one directory per capability, plus app/ and foundation/
  tests/             # one directory per capability; fakes/; e2e_server.py
  migrations/        # Alembic, SQL only
frontend/
  src/lib/           # one directory per capability, plus foundation/
  src/routes/        # pages
  e2e/               # Playwright tests
deploy/              # compose.yaml, web.Dockerfile
scripts/check        # the quality gate
start                # ./start run
```

## License

See [LICENSE](LICENSE).
