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
(issue #68), code completion (issue #69), the paper account check with the
account panel (issue #74), paper orders sent by hand (issue #75), backtests
(issue #70), the backtest comparison (issue #72), the backtest isolation
controls (issue #71), and the start and stop of forward tests (issue #76):

- The `web` service serves the app shell, `GET /api/health`,
  `GET /api/ibkr/gateway`, the instrument search, the watchlist routes under
  `/api/watchlist`, the strategy routes under `/api/strategies`, the
  language server WebSocket `/ws/strategy-language-server`, the paper order
  routes under `/api/paper-trading`, the backtest routes under
  `/api/backtests` and `/api/backtest-limits`, the forward test routes under
  `/api/forward-tests`, `/ws/paper-trading`, and `/ws/forward-tests`.
- The app shell header shows the backend status and the IB Gateway status.
- The `web` service connects to IB Gateway and connects again after a lost
  connection. It starts also when the Gateway is not reachable.
- After each connection, the `web` service checks the paper account. The home
  page shows the account panel: the check result, the balance, and the
  positions, updated live. When the check fails, the panel shows the actual
  and the expected account number.
- Paper orders by hand: after a passed check, the account panel sends market
  and limit orders (DAY or GTC) to the IBKR paper account, after a
  confirmation dialog with a `PAPER` mark. The open order list shows all open
  orders of the account with their source ("by hand" or "forward test N").
  Only orders by hand can be cancelled. ATrade never sends live orders. An
  order by hand on the instrument of a running forward test is refused, with
  the forward test named. The panel also lists the filled orders by hand of
  the current day, with the fills from IBKR. See
  [`docs/architecture/paper_trading.md`](docs/architecture/paper_trading.md).
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
- Watchlist: the user adds an instrument from the search candidates (choose
  it with the arrow keys and press Enter, or click it) and deletes
  it from the watchlist panel on the home page. The watchlist is in
  PostgreSQL, so it stays after a restart. A watchlist instrument opens the
  instrument page `/instruments/<exchange>/<symbol>?currency=<currency>`.
  Routes are under `/api/watchlist`. See
  [`docs/architecture/market_data.md`](docs/architecture/market_data.md)
  section 8.3.
- Bar chart: the instrument page shows the bar chart of the instrument for
  one bar period (1 minute to 1 day). Bars come from IBKR and stay in
  PostgreSQL. The next request for the same range does not call IBKR, so
  saved bars show also when IB Gateway is not reachable. The route is
  `GET /api/market-data/bars`. See
  [`docs/architecture/market_data.md`](docs/architecture/market_data.md)
  section 8.4.
- Live bars: the chart gets the current bar from IBKR over the WebSocket
  `/ws/market-data` and updates it without a page reload. The page connects
  again after a lost connection and when a background tab becomes visible.
  See [`docs/architecture/market_data.md`](docs/architecture/market_data.md)
  section 8.5.
- Backtests: the "New backtest" button on `/backtests` starts a backtest of a strategy version on
  the saved bars of one USD instrument, with paper capital from the paper
  account balance or the local setting. Each backtest runs in its own child
  process of `web`. The child has only the environment variables `PATH`,
  `HOME`, `TZ`, and `DATABASE_URL`, runs with `nice 10`, and has
  `oom_score_adj` 1000. The "Backtest limits" button on `/backtests` sets the timeout
  (default 120 minutes) and the number of backtests at the same time
  (default 1). Other backtests wait in the queue. A backtest that runs longer
  than the timeout stops with the status "Timed out". The backtest page shows the list of
  backtests and the open backtest on one page: the status, the key metrics,
  the equity and drawdown curves, the trades, and the strategy error (Logs). Backtests
  read only bars that are in PostgreSQL. Add the instrument to the watchlist
  and open its bar chart first: the form offers only watchlist instruments
  with saved bars of the selected bar period, and `POST /api/backtests`
  refuses a time range without saved bars (`422`). See
  [`docs/architecture/backtest.md`](docs/architecture/backtest.md).
- Backtest comparison: select 2 backtests of the same strategy in the list on
  `/backtests` and click "Compare". The comparison page shows the code diff, the
  metric table, and both equity curves on one chart. ATrade refuses 2
  backtests of different strategies. See
  [`docs/architecture/backtest.md`](docs/architecture/backtest.md) section 10.7.
- Forward tests: the page `/forward-tests` starts a forward test of a
  strategy version on one instrument and one IB live bar period, and shows
  the metrics of the latest backtest of that version. The `forward-test`
  service runs each forward test in its own child process with a
  NautilusTrader LiveNode and the client ID 10 to 13. The child checks the
  paper account first. Orders go only to the IBKR paper account. A stop
  cancels the open orders of the forward test. Positions stay open. One
  forward test per instrument, 4 at the same time. A restart of `web` does
  not stop forward tests. Before the start, the child reads the warm-up bars
  of the last 7 days (or more for long bar periods) from IBKR, so
  `request_bars` in the strategy gets them, as in a backtest. The forward
  test ID in the list opens the forward test page: its state, its
  interruptions, its equity curve and fills, and a link to the comparison
  with each backtest of the same period. See
  [`docs/architecture/forward_test.md`](docs/architecture/forward_test.md).
- Forward test records and comparison: at the end of each bar, the
  forward test records its new fills and one equity point in PostgreSQL. The
  button "Backtest the same period" starts a normal backtest of the same
  strategy version, instrument, bar period, and period, with the start
  balance as paper capital. The comparison page shows the metric table, both
  equity curves on one chart with the interruptions in grey, and the fill
  price of each side and the difference for each bar. See
  [`docs/architecture/forward_test.md`](docs/architecture/forward_test.md)
  section 12.10.

## Requirements

- Unix, or Windows through WSL. There is no native Windows start script.
- Docker with Docker Compose v2.

For development and checks, also:

- [uv](https://docs.astral.sh/uv/) 0.13. uv installs Python 3.14.
- [Vite+](https://viteplus.dev/) 1.4 (`vp`). Install it with
  `curl -fsSL https://vite.plus | bash`. `vp` installs Node.js 24 (from
  `frontend/.node-version`) and pnpm 10 (from `packageManager` in
  `frontend/package.json`).

## Run ATrade

### First start

1. If a `.env` from the old ATrade stack is in the repository root (it has
   variables such as `ATRADE_API_HTTP_PORT` or
   `ATRADE_IBKR_PAPER_ACCOUNT_ID`), move it to a different name, for example
   `.env.old-stack`. The rewrite does not read these variables.
2. Copy `.env.example` to `.env`.
3. Replace the placeholder values in `.env`. Do not commit `.env`. Set
   `ATRADE_POSTGRES_PASSWORD` to a new password (letters, digits, and `-`
   only). PostgreSQL keeps this password in its volume at the first start.
4. On rootless Podman without the memory cgroup controller, set
   `ATRADE_WEB_MEMORY_LIMIT=0`.
5. Start all services:

   ```sh
   ./start run -d --wait
   ```

6. Open <http://127.0.0.1:8000> (or the port in `ATRADE_WEB_PORT`).
   `GET /api/health` returns `"status": "ok"`.

`./start run` stops with a message when `ATRADE_POSTGRES_PASSWORD` is not
set, and writes a warning for each variable of the old stack.

When `web` stops with "PostgreSQL refused the password", the volume
`atrade-postgres18-data` has the password of an earlier start. Set that
password again in `.env`. If the volume has no data that you need, you can
remove it by hand (this deletes the data permanently):
`docker compose --file deploy/compose.yaml --env-file .env down`, then
`docker volume rm atrade-postgres18-data`.

Compose shows a warning about orphan containers when containers of the old
stack (`atrade-nats-1`, `atrade-ibeam-1`, and others) are in the Compose
project `atrade`. The warning does not stop the start. To remove these old
containers once (volumes stay):
`docker compose -p atrade down --remove-orphans`, before the first start of
the rewrite.

### Connect to the IBKR paper account

Without IB Gateway, ATrade starts, and the header shows "IB Gateway not
reachable". To connect:

1. In `.env`, set `COMPOSE_PROFILES=ibkr`.
2. Set `ATRADE_IBKR_USERNAME` and `ATRADE_IBKR_PASSWORD` to the login of the
   IBKR paper account. Set `ATRADE_IBKR_ACCOUNT_ID` to the paper account
   number (it starts with `DU`). IBC restarts the Gateway each day at
   `ATRADE_IBKR_AUTO_RESTART_TIME` in `ATRADE_IBKR_TIME_ZONE` (default
   `11:45 PM`, `America/New_York`).
3. Run `./start run`. The header shows "IB Gateway connected." after the
   Gateway has logged in. The account panel shows "Paper account DU...
   checked." when the paper account check passes.

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
| `postgres` | PostgreSQL 18. Volume `atrade-postgres18-data`. Not published outside the Compose network. |
| `ib-gateway` | IB Gateway and IBC, logged in to the paper account. Profile `ibkr`. The API port (`ib-gateway:4004`) is not published outside the Compose network. |
| `web` | FastAPI app (`python -m atrade.app.web`) and the built frontend. Port `127.0.0.1:${ATRADE_WEB_PORT}`. Memory limit, read-only root file system, writable `/tmp`. Health check on `/api/health`. |
| `forward-test` | Forward-test worker (`python -m atrade.app.forward_test_worker`) and 1 child process per running forward test. Same image as `web`. Starts after the health check of `web` passes. No IBKR user name or password. |

At start, `web` runs the Alembic migrations. When `ATRADE_TRADING_MODE` is
`live`, `web` does not start and writes the reason.

Rootless Podman without the memory cgroup controller cannot set a memory
limit. On such a host, set `ATRADE_WEB_MEMORY_LIMIT=0` in `.env`.

### Old data

The rewrite migrates no old data. The new database uses the new volume
`atrade-postgres18-data`. The old PostgreSQL volumes (for example
`atrade_postgres_data`, and `atrade-pgdata` of earlier test starts) and the
old containers are not used. ATrade does not delete or change them. To remove them, do these steps by hand. This deletes the old data
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
  `cd frontend && vp exec playwright install`. The Playwright backend
  listens on port 4173. Set `ATRADE_E2E_PORT` to use a different port, for
  example when 2 checkouts run the checks at the same time.
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
cd frontend && vp run generate:api
```

This writes `frontend/src/lib/api/openapi.json` and
`frontend/src/lib/api/index.ts`. Commit both files. A backend test fails when
`openapi.json` does not match the routes. `vp run check:api` (in
`./scripts/check frontend`) fails when `index.ts` does not match
`openapi.json`.

## Development without Docker

```sh
cd backend && uv sync
DATABASE_URL=postgresql://... ATRADE_FRONTEND_BUILD_DIR=../frontend/build uv run python -m atrade.app.web
cd frontend && vp install && vp dev    # sends /api and /ws to 127.0.0.1:8000
```

In `frontend/`, `vp dev`, `vp build`, and `vp test` run Vite and Vitest.
`vp run lint:eslint` runs ESLint and `vp run check:svelte` runs
`svelte-check`. Do not use `vp lint`, `vp fmt`, or `vp check`: ATrade does not
use Oxlint or Oxfmt.

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
