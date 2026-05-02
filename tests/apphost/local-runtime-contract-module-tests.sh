#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_template_path="$repo_root/.env.template"
readme_path="$repo_root/README.md"
scripts_readme_path="$repo_root/scripts/README.md"
overview_path="$repo_root/docs/architecture/overview.md"
paper_workspace_path="$repo_root/docs/architecture/paper-trading-workspace.md"
analysis_engines_path="$repo_root/docs/architecture/analysis-engines.md"
start_wrapper_test_path="$repo_root/tests/start-contract/start-wrapper-tests.sh"
paper_config_test_path="$repo_root/tests/apphost/paper-trading-config-contract-tests.sh"

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

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s to not contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_env_template_defaults() {
  python3 - <<'PY' "$env_template_path"
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
values: dict[str, str] = {}

for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' not in line:
        raise SystemExit(f'invalid .env.template line: {raw_line}')
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip().strip('"\'')
    if not key:
        raise SystemExit(f'invalid empty .env.template key in line: {raw_line}')
    if key in values:
        raise SystemExit(f'duplicate .env.template key: {key}')
    values[key] = value

expected = {
    'ATRADE_API_HTTP_PORT': '5181',
    'ATRADE_FRONTEND_DIRECT_HTTP_PORT': '3111',
    'ATRADE_APPHOST_FRONTEND_HTTP_PORT': '3000',
    'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT': '0',
    'ATRADE_POSTGRES_DATA_VOLUME': 'atrade-postgres-data',
    'ATRADE_POSTGRES_PASSWORD': 'ATRADE_POSTGRES_PASSWORD',
    'ATRADE_TIMESCALEDB_DATA_VOLUME': 'atrade-timescaledb-data',
    'ATRADE_TIMESCALEDB_PASSWORD': 'ATRADE_TIMESCALEDB_PASSWORD',
    'ATRADE_BROKER_INTEGRATION_ENABLED': 'false',
    'ATRADE_BROKER_ACCOUNT_MODE': 'Paper',
    'ATRADE_IBKR_GATEWAY_URL': 'https://127.0.0.1:5000',
    'ATRADE_IBKR_GATEWAY_PORT': '5000',
    'ATRADE_IBKR_GATEWAY_IMAGE': 'voyz/ibeam:latest',
    'ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS': '15',
    'ATRADE_IBKR_USERNAME': 'IBKR_USERNAME',
    'ATRADE_IBKR_PASSWORD': 'IBKR_PASSWORD',
    'ATRADE_IBKR_PAPER_ACCOUNT_ID': 'IBKR_ACCOUNT_ID',
    'ATRADE_FRONTEND_API_BASE_URL': 'http://127.0.0.1:5181',
    'NEXT_PUBLIC_ATRADE_API_BASE_URL': 'http://127.0.0.1:5181',
    'ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES': '30',
    'ATRADE_ANALYSIS_ENGINE': 'none',
    'ATRADE_LEAN_RUNTIME_MODE': 'cli',
    'ATRADE_LEAN_CLI_COMMAND': 'lean',
    'ATRADE_LEAN_DOCKER_COMMAND': 'docker',
    'ATRADE_LEAN_DOCKER_IMAGE': 'quantconnect/lean:latest',
    'ATRADE_LEAN_WORKSPACE_ROOT': 'artifacts/lean-workspaces',
    'ATRADE_LEAN_TIMEOUT_SECONDS': '45',
    'ATRADE_LEAN_KEEP_WORKSPACE': 'false',
    'ATRADE_LEAN_MANAGED_CONTAINER_NAME': 'atrade-lean-engine',
    'ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT': '/workspace',
}

missing = sorted(set(expected) - set(values))
if missing:
    raise SystemExit(f'.env.template missing expected keys: {missing}')

for key, expected_value in expected.items():
    actual_value = values[key]
    if actual_value != expected_value:
        raise SystemExit(f'{key} expected {expected_value!r}, found {actual_value!r}')

for key, value in values.items():
    if value.lower() == 'live':
        raise SystemExit(f'{key} must not default to live mode')
    if re.search(r'(TOKEN|COOKIE|SESSION)', key, re.IGNORECASE):
        raise SystemExit(f'session/token/cookie-bearing key must not be committed to .env.template: {key}')
    if key in {'ATRADE_IBKR_USERNAME', 'ATRADE_IBKR_PASSWORD', 'ATRADE_IBKR_PAPER_ACCOUNT_ID'}:
        continue
    if re.fullmatch(r'(DU|U)\d+', value, re.IGNORECASE):
        raise SystemExit(f'{key} must not contain a real-looking broker account id')

if values['ATRADE_IBKR_USERNAME'] != 'IBKR_USERNAME':
    raise SystemExit('ATRADE_IBKR_USERNAME must stay an obvious fake placeholder')
if values['ATRADE_IBKR_PASSWORD'] != 'IBKR_PASSWORD':
    raise SystemExit('ATRADE_IBKR_PASSWORD must stay an obvious fake placeholder')
if values['ATRADE_IBKR_PAPER_ACCOUNT_ID'] != 'IBKR_ACCOUNT_ID':
    raise SystemExit('ATRADE_IBKR_PAPER_ACCOUNT_ID must stay an obvious fake placeholder')
PY
}

assert_docs_and_existing_tests_share_defaults() {
  assert_file_contains "$scripts_readme_path" '`ATRADE_API_HTTP_PORT` — direct `ATrade.Api` startup and smoke coverage; committed default `5181`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_FRONTEND_DIRECT_HTTP_PORT` — direct `frontend/` `npm run dev` verification path; committed default `3111`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_APPHOST_FRONTEND_HTTP_PORT` — AppHost-managed Next.js frontend port; committed default `3000`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_ASPIRE_DASHBOARD_HTTP_PORT` — Aspire dashboard UI bind port used by `./start run`, `./start.ps1 run`, and `./start.cmd run`; the committed default `0`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_BROKER_INTEGRATION_ENABLED` — feature flag for local broker/iBeam wiring; committed default stays `false`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_IBKR_GATEWAY_URL` — local iBeam/IBKR Gateway Client Portal API base URL; committed default is `https://127.0.0.1:5000`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_IBKR_GATEWAY_PORT` — local host bind port for the iBeam Client Portal API; committed default is `5000`'
  assert_file_contains "$scripts_readme_path" '`ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` — non-secret TimescaleDB market-data cache freshness window; committed default is `30`'

  assert_file_contains "$readme_path" '(`ATRADE_ASPIRE_DASHBOARD_HTTP_PORT`, default `0` for ephemeral loopback)'
  assert_file_contains "$readme_path" 'mapped to the container'"'"'s internal Client Portal port `5000`'
  assert_file_contains "$readme_path" '`ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`'
  assert_file_contains "$readme_path" '(default `30`) controls whether TimescaleDB rows'

  assert_file_contains "$overview_path" 'dashboard UI keeps the safe ephemeral loopback default (`0`)'
  assert_file_contains "$paper_workspace_path" 'iBeam/Gateway container image `voyz/ibeam:latest`, which is disabled by default'
  assert_file_contains "$paper_workspace_path" 'URL default is `https://127.0.0.1:5000`'
  assert_file_contains "$analysis_engines_path" 'ATRADE_ANALYSIS_ENGINE=none'
  assert_file_contains "$analysis_engines_path" 'ATRADE_LEAN_RUNTIME_MODE=cli'

  assert_file_contains "$start_wrapper_test_path" "assert_file_contains \"\$repo_root/.env.template\" 'ATRADE_APPHOST_FRONTEND_HTTP_PORT=3000'"
  assert_file_contains "$start_wrapper_test_path" "assert_file_contains \"\$repo_root/.env.template\" 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0'"
  assert_file_contains "$paper_config_test_path" "'ATRADE_BROKER_INTEGRATION_ENABLED': 'false'"
  assert_file_contains "$paper_config_test_path" "'ATRADE_IBKR_GATEWAY_URL': 'https://127.0.0.1:5000'"
  assert_file_contains "$paper_config_test_path" "'ATRADE_IBKR_GATEWAY_PORT': '5000'"
}

assert_removed_lane_specific_defaults() {
  assert_file_not_contains "$env_template_path" 'ATRADE_API_HTTP_PORT=15181'
  assert_file_not_contains "$env_template_path" 'ATRADE_FRONTEND_DIRECT_HTTP_PORT=13111'
  assert_file_not_contains "$env_template_path" 'ATRADE_APPHOST_FRONTEND_HTTP_PORT=13000'
  assert_file_not_contains "$env_template_path" 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=10001'
  assert_file_not_contains "$env_template_path" 'ATRADE_IBKR_GATEWAY_URL=https://127.0.0.1:15000'
  assert_file_not_contains "$env_template_path" 'ATRADE_IBKR_GATEWAY_PORT=15000'
  assert_file_not_contains "$env_template_path" 'ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES=10'
}

main() {
  assert_env_template_defaults
  assert_docs_and_existing_tests_share_defaults
  assert_removed_lane_specific_defaults
}

main "$@"
