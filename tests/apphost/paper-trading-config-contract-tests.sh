#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
doc_path="$repo_root/docs/architecture/paper-trading-workspace.md"
index_path="$repo_root/docs/INDEX.md"
env_path="$repo_root/.env.example"
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
  python3 - <<'PY' "$doc_path"
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding='utf-8')

if not text.startswith('---\n'):
    raise SystemExit(f'{path} is missing a frontmatter block')

parts = text.split('---\n', 2)
if len(parts) < 3:
    raise SystemExit(f'{path} does not contain a complete frontmatter block')

frontmatter = parts[1]
required_fields = ['status:', 'owner:', 'updated:', 'summary:', 'see_also:']
for field in required_fields:
    if field not in frontmatter:
        raise SystemExit(f'{path} frontmatter missing {field}')

if 'status: active' not in frontmatter:
    raise SystemExit(f'{path} frontmatter must declare status: active')
PY
}

assert_env_contract_is_paper_safe() {
  python3 - <<'PY' "$env_path"
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
values = {}
for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' not in line:
        raise SystemExit(f'invalid env contract line: {raw_line}')
    key, value = line.split('=', 1)
    values[key] = value

required = {
    'ATRADE_API_HTTP_PORT': '5181',
    'ATRADE_FRONTEND_DIRECT_HTTP_PORT': '3111',
    'ATRADE_APPHOST_FRONTEND_HTTP_PORT': '3000',
    'ATRADE_BROKER_INTEGRATION_ENABLED': 'false',
    'ATRADE_BROKER_ACCOUNT_MODE': 'Paper',
    'ATRADE_IBKR_GATEWAY_URL': 'http://127.0.0.1:5000',
    'ATRADE_IBKR_GATEWAY_PORT': '5000',
    'ATRADE_IBKR_GATEWAY_IMAGE': 'voyz/ibeam:latest',
    'ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS': '15',
    'ATRADE_IBKR_USERNAME': 'IBKR_USERNAME',
    'ATRADE_IBKR_PASSWORD': 'IBKR_PASSWORD',
    'ATRADE_IBKR_PAPER_ACCOUNT_ID': 'IBKR_ACCOUNT_ID',
    'ATRADE_FRONTEND_API_BASE_URL': 'http://127.0.0.1:5181',
    'NEXT_PUBLIC_ATRADE_API_BASE_URL': 'http://127.0.0.1:5181',
}

for key, expected in required.items():
    actual = values.get(key)
    if actual != expected:
        raise SystemExit(f'{key} expected {expected!r}, found {actual!r}')

if values['ATRADE_IBKR_USERNAME'] != 'IBKR_USERNAME':
    raise SystemExit('ATRADE_IBKR_USERNAME must stay an obvious fake placeholder')

if values['ATRADE_IBKR_PASSWORD'] != 'IBKR_PASSWORD':
    raise SystemExit('ATRADE_IBKR_PASSWORD must stay an obvious fake placeholder')

for key in values:
    if re.search(r'(TOKEN|SECRET|COOKIE|SESSION)', key):
        raise SystemExit(f'unexpected token/session/secret-bearing key committed to .env.example: {key}')

if values['ATRADE_BROKER_ACCOUNT_MODE'] != 'Paper':
    raise SystemExit('ATRADE_BROKER_ACCOUNT_MODE must remain Paper in committed defaults')

if values['ATRADE_BROKER_INTEGRATION_ENABLED'].lower() != 'false':
    raise SystemExit('ATRADE_BROKER_INTEGRATION_ENABLED must remain false in committed defaults')

if values['ATRADE_IBKR_PAPER_ACCOUNT_ID'] != 'IBKR_ACCOUNT_ID' or re.fullmatch(r'(DU|U)\d+', values['ATRADE_IBKR_PAPER_ACCOUNT_ID']):
    raise SystemExit('ATRADE_IBKR_PAPER_ACCOUNT_ID must stay a placeholder, not a real-looking account id')

for key, value in values.items():
    if key != 'ATRADE_BROKER_ACCOUNT_MODE' and value.lower() == 'live':
        raise SystemExit(f'{key} must not default to live mode')
PY
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
