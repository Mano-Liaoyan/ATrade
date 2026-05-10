#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
doc_path="$repo_root/docs/architecture/paper-trading-workspace.md"
index_path="$repo_root/docs/INDEX.md"
env_path="$repo_root/.env.template"
overview_path="$repo_root/docs/architecture/overview.md"
modules_path="$repo_root/docs/architecture/modules.md"
readme_path="$repo_root/README.md"

assert_file_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if ! grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_architecture_doc_frontmatter() {
  node - <<'JS' "$doc_path"
const fs = require('fs');
const docPath = process.argv[2];
const text = fs.readFileSync(docPath, 'utf8');

if (!text.startsWith('---\n') && !text.startsWith('---\r\n')) throw new Error(`${docPath} is missing a frontmatter block`);
const parts = text.split(/---\r?\n/);
if (parts.length < 3) throw new Error(`${docPath} does not contain a complete frontmatter block`);
const frontmatter = parts[1];
for (const field of ['status:', 'owner:', 'updated:', 'summary:', 'see_also:']) {
  if (!frontmatter.includes(field)) throw new Error(`${docPath} frontmatter missing ${field}`);
}
if (!frontmatter.includes('status: active')) throw new Error(`${docPath} frontmatter must declare status: active`);
JS
}

assert_env_contract_is_paper_safe() {
  node - <<'JS' "$env_path"
const fs = require('fs');
const envPath = process.argv[2];
const values = new Map();

for (const rawLine of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
  const line = rawLine.trim();
  if (!line || line.startsWith('#')) continue;
  const separatorIndex = line.indexOf('=');
  if (separatorIndex <= 0) throw new Error(`invalid env contract line: ${rawLine}`);
  values.set(line.slice(0, separatorIndex), line.slice(separatorIndex + 1));
}

const required = {
  ATRADE_API_HTTP_PORT: '5181',
  ATRADE_FRONTEND_DIRECT_HTTP_PORT: '3111',
  ATRADE_APPHOST_FRONTEND_HTTP_PORT: '3000',
  ATRADE_ASPIRE_DASHBOARD_HTTP_PORT: '0',
  ATRADE_COMPOSE_COMMAND: '',
  ATRADE_COMPOSE_PROJECT_NAME: 'atrade',
  ATRADE_POSTGRES_PORT: '5432',
  ATRADE_TIMESCALEDB_PORT: '5433',
  ATRADE_REDIS_PORT: '6379',
  ATRADE_NATS_PORT: '4222',
  ATRADE_POSTGRES_DATA_VOLUME: 'atrade-postgres-data',
  ATRADE_POSTGRES_PASSWORD: 'ATRADE_POSTGRES_PASSWORD',
  ATRADE_TIMESCALEDB_DATA_VOLUME: 'atrade-timescaledb-data',
  ATRADE_TIMESCALEDB_PASSWORD: 'ATRADE_TIMESCALEDB_PASSWORD',
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_BROKER_ACCOUNT_MODE: 'Paper',
  ATRADE_IBKR_GATEWAY_URL: 'https://127.0.0.1:5000',
  ATRADE_IBKR_GATEWAY_PORT: '5000',
  ATRADE_IBKR_GATEWAY_IMAGE: 'voyz/ibeam:latest',
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS: '15',
  ATRADE_IBKR_USERNAME: 'IBKR_USERNAME',
  ATRADE_IBKR_PASSWORD: 'IBKR_PASSWORD',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: 'IBKR_ACCOUNT_ID',
  ATRADE_FRONTEND_API_BASE_URL: 'http://127.0.0.1:5181',
  NEXT_PUBLIC_ATRADE_API_BASE_URL: 'http://127.0.0.1:5181',
};

for (const [key, expected] of Object.entries(required)) {
  const actual = values.get(key);
  if (actual !== expected) throw new Error(`${key} expected ${JSON.stringify(expected)}, found ${JSON.stringify(actual)}`);
}

if (values.get('ATRADE_IBKR_USERNAME') !== 'IBKR_USERNAME') throw new Error('ATRADE_IBKR_USERNAME must stay an obvious fake placeholder');
if (values.get('ATRADE_IBKR_PASSWORD') !== 'IBKR_PASSWORD') throw new Error('ATRADE_IBKR_PASSWORD must stay an obvious fake placeholder');

for (const key of values.keys()) {
  if (/(TOKEN|SECRET|COOKIE|SESSION)/.test(key)) throw new Error(`unexpected token/session/secret-bearing key committed to .env.template: ${key}`);
}

if (values.get('ATRADE_BROKER_ACCOUNT_MODE') !== 'Paper') throw new Error('ATRADE_BROKER_ACCOUNT_MODE must remain Paper in committed defaults');
if (values.get('ATRADE_ASPIRE_DASHBOARD_HTTP_PORT') !== '0') throw new Error('ATRADE_ASPIRE_DASHBOARD_HTTP_PORT must preserve the ephemeral dashboard default');
if (values.get('ATRADE_POSTGRES_DATA_VOLUME') !== 'atrade-postgres-data') throw new Error('ATRADE_POSTGRES_DATA_VOLUME must preserve the shared non-secret default Postgres volume name');
if (values.get('ATRADE_POSTGRES_PASSWORD') !== 'ATRADE_POSTGRES_PASSWORD') throw new Error('ATRADE_POSTGRES_PASSWORD must stay an obvious fake local-dev placeholder');
if (values.get('ATRADE_TIMESCALEDB_DATA_VOLUME') !== 'atrade-timescaledb-data') throw new Error('ATRADE_TIMESCALEDB_DATA_VOLUME must preserve the shared non-secret default TimescaleDB volume name');
if (values.get('ATRADE_TIMESCALEDB_PASSWORD') !== 'ATRADE_TIMESCALEDB_PASSWORD') throw new Error('ATRADE_TIMESCALEDB_PASSWORD must stay an obvious fake local-dev placeholder');

if ([...values.keys()].some((key) => ['TOKEN', 'SECRET', 'COOKIE', 'SESSION'].some((token) => 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT'.includes(token)))) {
  throw new Error('ATRADE_ASPIRE_DASHBOARD_HTTP_PORT must remain a non-secret local port key');
}
if (['TOKEN', 'SECRET', 'COOKIE', 'SESSION'].some((token) => 'ATRADE_POSTGRES_DATA_VOLUME'.includes(token))) {
  throw new Error('ATRADE_POSTGRES_DATA_VOLUME must remain a non-secret local Docker volume key');
}
if (['TOKEN', 'SECRET', 'COOKIE', 'SESSION'].some((token) => 'ATRADE_TIMESCALEDB_DATA_VOLUME'.includes(token))) {
  throw new Error('ATRADE_TIMESCALEDB_DATA_VOLUME must remain a non-secret local Docker volume key');
}

if (/^(DU|U)\d+$/i.test(values.get('ATRADE_POSTGRES_PASSWORD'))) throw new Error('ATRADE_POSTGRES_PASSWORD must not look like a broker account id');
if (/^(DU|U)\d+$/i.test(values.get('ATRADE_TIMESCALEDB_PASSWORD'))) throw new Error('ATRADE_TIMESCALEDB_PASSWORD must not look like a broker account id');
if (values.get('ATRADE_BROKER_INTEGRATION_ENABLED').toLowerCase() !== 'false') throw new Error('ATRADE_BROKER_INTEGRATION_ENABLED must remain false in committed defaults');
if (values.get('ATRADE_IBKR_PAPER_ACCOUNT_ID') !== 'IBKR_ACCOUNT_ID' || /^(DU|U)\d+$/i.test(values.get('ATRADE_IBKR_PAPER_ACCOUNT_ID'))) {
  throw new Error('ATRADE_IBKR_PAPER_ACCOUNT_ID must stay a placeholder, not a real-looking account id');
}

for (const [key, value] of values) {
  if (key !== 'ATRADE_BROKER_ACCOUNT_MODE' && value.toLowerCase() === 'live') throw new Error(`${key} must not default to live mode`);
}
JS
}

assert_docs_capture_paper_trading_contract() {
  assert_file_contains "$doc_path" '# Paper-Trading Workspace Architecture'
  assert_file_contains "$doc_path" 'lightweight-charts'
  assert_file_contains "$doc_path" 'SignalR'
  assert_file_contains "$doc_path" 'volume spike'
  assert_file_contains "$doc_path" 'price momentum'
  assert_file_contains "$doc_path" 'volatility'
  assert_file_contains "$doc_path" 'external signal'
  assert_file_contains "$doc_path" 'IBKR Scanner Trending Factors Now'
  assert_file_contains "$doc_path" 'LEAN'
  assert_file_contains "$doc_path" 'Real trades are forbidden'
  assert_file_contains "$doc_path" 'paper-only'
  assert_file_contains "$doc_path" 'voyz/ibeam:latest'
  assert_file_contains "$doc_path" 'credentials-missing'
  assert_file_contains "$doc_path" 'IBEAM_ACCOUNT'

  assert_file_contains "$index_path" '| [`architecture/paper-trading-workspace.md`](architecture/paper-trading-workspace.md) | maintainer | Authoritative paper-trading workspace architecture and paper-only configuration contract for the staged IBKR-backed trading UI slice.   |'
  assert_file_contains "$overview_path" 'paper-trading workspace'
  assert_file_contains "$overview_path" 'SignalR'
  assert_file_contains "$modules_path" 'lightweight-charts'
  assert_file_contains "$modules_path" 'paper-only'
  assert_file_contains "$modules_path" 'LEAN'
  assert_file_contains "$readme_path" 'paper-trading workspace contract'
  assert_file_contains "$readme_path" 'voyz/ibeam:latest'
}

main() {
  assert_architecture_doc_frontmatter
  assert_env_contract_is_paper_safe
  assert_docs_capture_paper_trading_contract
}

main "$@"
