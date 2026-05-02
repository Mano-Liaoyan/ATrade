#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
manifest_path=''
enabled_manifest_path=''
status_file=''
configured_status_file=''
health_file=''
api_log=''
api_pid=''

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  rm -f "$manifest_path" "$enabled_manifest_path" "$status_file" \
    "$configured_status_file" "$health_file" "$api_log"
}

trap cleanup EXIT

allocate_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

publish_manifest() {
  local output_path="$1"
  local integration_enabled="$2"
  local username="$3"
  local password="$4"
  local account_id="$5"

  ATRADE_BROKER_INTEGRATION_ENABLED="$integration_enabled" \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL=https://127.0.0.1:5000 \
  ATRADE_IBKR_GATEWAY_PORT=5000 \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=15 \
  ATRADE_IBKR_USERNAME="$username" \
  ATRADE_IBKR_PASSWORD="$password" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID="$account_id" \
  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$output_path" >/dev/null
}

start_api() {
  local api_port="$1"
  local gateway_port="$2"
  local username="$3"
  local password="$4"
  local account_id="$5"
  local api_url="http://127.0.0.1:${api_port}"

  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  api_log="$(mktemp)"

  ATRADE_BROKER_INTEGRATION_ENABLED=true \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL="https://127.0.0.1:${gateway_port}" \
  ATRADE_IBKR_GATEWAY_PORT="$gateway_port" \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=1 \
  ATRADE_IBKR_USERNAME="$username" \
  ATRADE_IBKR_PASSWORD="$password" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID="$account_id" \
  ASPNETCORE_URLS="$api_url" \
  dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  for _ in {1..40}; do
    if [[ "$(curl --silent --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'ATrade.Api did not become healthy at %s.\n' "$api_url" >&2
  cat "$api_log" >&2
  return 1
}

stop_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  api_pid=''
}

assert_template_is_safe() {
  python3 - <<'PY' "$repo_root/.env.template"
from pathlib import Path
import re
import sys

template_path = Path(sys.argv[1])

def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise SystemExit(f'invalid env line in {path}: {raw_line}')
        key, value = line.split('=', 1)
        values[key] = value
    return values

values = parse(template_path)

required = {
    'ATRADE_BROKER_INTEGRATION_ENABLED': 'false',
    'ATRADE_BROKER_ACCOUNT_MODE': 'Paper',
    'ATRADE_IBKR_GATEWAY_URL': 'https://127.0.0.1:5000',
    'ATRADE_IBKR_GATEWAY_PORT': '5000',
    'ATRADE_IBKR_GATEWAY_IMAGE': 'voyz/ibeam:latest',
    'ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS': '15',
    'ATRADE_IBKR_USERNAME': 'IBKR_USERNAME',
    'ATRADE_IBKR_PASSWORD': 'IBKR_PASSWORD',
    'ATRADE_IBKR_PAPER_ACCOUNT_ID': 'IBKR_ACCOUNT_ID',
}
for key, expected in required.items():
    actual = values.get(key)
    if actual != expected:
        raise SystemExit(f'{key} expected {expected!r}, found {actual!r}')

safe_password_placeholders = {'ATRADE_POSTGRES_PASSWORD', 'ATRADE_TIMESCALEDB_PASSWORD'}
for key, value in values.items():
    upper_key = key.upper()
    upper_value = value.upper()
    if any(token in upper_key for token in ('TOKEN', 'SESSION', 'COOKIE', 'SECRET')):
        raise SystemExit(f'committed env template must not introduce token/session/cookie/secret key: {key}')
    if key in {'ATRADE_IBKR_USERNAME', 'ATRADE_IBKR_PASSWORD', 'ATRADE_IBKR_PAPER_ACCOUNT_ID'} | safe_password_placeholders:
        continue
    if any(token in upper_value for token in ('PASSWORD', 'TOKEN', 'SESSION', 'COOKIE', 'SECRET')):
        raise SystemExit(f'committed env template contains suspicious credential-like value for {key}')

if re.fullmatch(r'(DU|U)\d+', values['ATRADE_IBKR_PAPER_ACCOUNT_ID']):
    raise SystemExit('committed paper account id must remain an obvious placeholder')
if values['ATRADE_BROKER_INTEGRATION_ENABLED'].lower() != 'false':
    raise SystemExit('broker integration must stay disabled by default')
if any(value.lower() == 'live' for key, value in values.items() if key != 'ATRADE_BROKER_ACCOUNT_MODE'):
    raise SystemExit('committed defaults must not enable live behavior')
PY
}

assert_apphost_ibeam_manifest_contract() {
  manifest_path="$(mktemp --suffix=.json)"
  enabled_manifest_path="$(mktemp --suffix=.json)"

  publish_manifest "$manifest_path" false IBKR_USERNAME IBKR_PASSWORD IBKR_ACCOUNT_ID
  publish_manifest "$enabled_manifest_path" true REAL_USERNAME_SHOULD_NOT_SURFACE REAL_PASSWORD_SHOULD_NOT_SURFACE DU1234567

  python3 - <<'PY' "$manifest_path" "$enabled_manifest_path" "$repo_root/src/ATrade.AppHost/Program.cs" "$repo_root/src/ATrade.AppHost/ibeam-inputs/conf.yaml"
from pathlib import Path
import json
import sys

disabled_manifest = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
enabled_manifest_path = Path(sys.argv[2])
enabled_text = enabled_manifest_path.read_text(encoding='utf-8')
enabled_manifest = json.loads(enabled_text)
program_text = Path(sys.argv[3]).read_text(encoding='utf-8')
ibeam_conf_text = Path(sys.argv[4]).read_text(encoding='utf-8')

if 'AddContainer("ibkr-gateway"' not in program_text:
    raise SystemExit('AppHost must declare the ibkr-gateway container resource')
if 'IBEAM_ACCOUNT' not in program_text and 'IbeamAccount' not in program_text:
    raise SystemExit('AppHost must map the verified IBEAM_ACCOUNT variable')
if 'IBEAM_PASSWORD' not in program_text and 'IbeamPassword' not in program_text:
    raise SystemExit('AppHost must map the verified IBEAM_PASSWORD variable')

if 'ibkr-gateway' in disabled_manifest.get('resources', {}):
    raise SystemExit('default disabled AppHost manifest must not start ibkr-gateway')

enabled_resources = enabled_manifest.get('resources', {})
container = enabled_resources.get('ibkr-gateway')
if container is None:
    raise SystemExit('enabled AppHost manifest must include ibkr-gateway')
if container.get('image') != 'voyz/ibeam:latest':
    raise SystemExit(f'ibkr-gateway image must be voyz/ibeam:latest: {container!r}')
if container.get('env') != {'IBEAM_ACCOUNT': '{ibkr-username.value}', 'IBEAM_PASSWORD': '{ibkr-password.value}'}:
    raise SystemExit(f'ibkr-gateway must receive only required redacted iBeam env vars: {container.get("env")!r}')
bind_mounts = container.get('bindMounts', [])
if not any(mount.get('target') == '/srv/inputs' and mount.get('readOnly') is True and 'ibeam-inputs' in mount.get('source', '') for mount in bind_mounts):
    raise SystemExit(f'ibkr-gateway must mount the repo-local iBeam inputs directory read-only: {bind_mounts!r}')
for required in ('172.16.*', '172.31.*', '192.168.*', '10.*', '127.0.0.1'):
    if required not in ibeam_conf_text:
        raise SystemExit(f'iBeam custom conf.yaml must allow local/private Docker caller range {required}')
for forbidden in ('IBKR_USERNAME', 'IBKR_PASSWORD', 'IBKR_ACCOUNT_ID', 'REAL_USERNAME', 'REAL_PASSWORD', 'DU1234567'):
    if forbidden in ibeam_conf_text:
        raise SystemExit(f'iBeam custom conf.yaml must not contain credential/account placeholders: {forbidden}')
https_binding = container.get('bindings', {}).get('https')
if https_binding is None:
    raise SystemExit(f'ibkr-gateway must expose an HTTPS binding, found {container.get("bindings")!r}')
if https_binding.get('scheme') != 'https' or https_binding.get('targetPort') != 5000:
    raise SystemExit(f'ibkr-gateway HTTPS binding must target Client Portal port 5000: {https_binding!r}')
for resource_name in ('ibkr-username', 'ibkr-password', 'ibkr-paper-account-id'):
    resource = enabled_resources.get(resource_name)
    if resource is None or resource.get('type') != 'parameter.v0':
        raise SystemExit(f'missing secret parameter resource {resource_name}')
    if resource.get('inputs', {}).get('value', {}).get('secret') is not True:
        raise SystemExit(f'{resource_name} must be marked secret')
for forbidden in ('REAL_USERNAME_SHOULD_NOT_SURFACE', 'REAL_PASSWORD_SHOULD_NOT_SURFACE', 'DU1234567'):
    if forbidden in enabled_text:
        raise SystemExit(f'AppHost manifest leaked raw credential/account value: {forbidden}')
PY
}

assert_status_payloads_are_redacted() {
  health_file="$(mktemp)"
  status_file="$(mktemp)"
  configured_status_file="$(mktemp)"

  local missing_port
  missing_port="$(allocate_port)"
  start_api "$missing_port" 5000 IBKR_USERNAME IBKR_PASSWORD IBKR_ACCOUNT_ID
  curl --silent --fail --output "$status_file" "http://127.0.0.1:${missing_port}/api/broker/ibkr/status" >/dev/null
  stop_api

  local configured_port
  local closed_gateway_port
  configured_port="$(allocate_port)"
  closed_gateway_port="$(allocate_port)"
  start_api "$configured_port" "$closed_gateway_port" REAL_USERNAME_SHOULD_NOT_LEAK REAL_PASSWORD_SHOULD_NOT_LEAK DU1234567
  curl --silent --fail --output "$configured_status_file" "http://127.0.0.1:${configured_port}/api/broker/ibkr/status" >/dev/null
  stop_api

  python3 - <<'PY' "$status_file" "$configured_status_file"
from pathlib import Path
import json
import sys

missing = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
configured = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
if missing.get('state') != 'credentials-missing':
    raise SystemExit(f'placeholder credentials must produce credentials-missing status: {missing!r}')
if configured.get('state') != 'ibeam-container-configured':
    raise SystemExit(f'configured but unreachable iBeam must produce safe configured status: {configured!r}')
for payload in (missing, configured):
    serialized = json.dumps(payload)
    for forbidden in (
        'IBKR_USERNAME',
        'IBKR_PASSWORD',
        'IBKR_ACCOUNT_ID',
        'REAL_USERNAME_SHOULD_NOT_LEAK',
        'REAL_PASSWORD_SHOULD_NOT_LEAK',
        'DU1234567',
        'sessionCookie',
        'token',
    ):
        if forbidden in serialized:
            raise SystemExit(f'status payload leaked forbidden value: {forbidden}')
    if 'paperAccountId' in payload or 'gatewayUrl' in payload or 'username' in payload or 'password' in payload:
        raise SystemExit(f'status payload exposed unsafe fields: {payload!r}')
PY
}

assert_optional_real_ibeam_https_smoke() {
  if [[ "${ATRADE_IBKR_REAL_SMOKE:-}" != "1" ]]; then
    return 0
  fi

  local gateway_url="${ATRADE_IBKR_GATEWAY_URL:-https://127.0.0.1:5000}"
  case "$gateway_url" in
    https://127.0.0.1:*|https://localhost:*) ;;
    *)
      return 0
      ;;
  esac

  local smoke_file
  smoke_file="$(mktemp)"
  local status_code
  status_code="$(curl --silent --show-error --insecure --max-time 5 --output "$smoke_file" --write-out '%{http_code}' "${gateway_url%/}/v1/api/iserver/auth/status" 2>/dev/null || true)"

  if [[ "$status_code" != 2* ]]; then
    rm -f "$smoke_file"
    return 0
  fi

  python3 - <<'PY' "$smoke_file"
from pathlib import Path
import json
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if not isinstance(payload.get('authenticated'), bool) or not isinstance(payload.get('connected'), bool):
    raise SystemExit('real iBeam auth-status smoke response must include boolean authenticated and connected fields')
serialized = json.dumps(payload)
for forbidden in ('IBKR_USERNAME', 'IBKR_PASSWORD', 'IBKR_ACCOUNT_ID', 'sessionCookie', 'cookie', 'token'):
    if forbidden in serialized:
        raise SystemExit(f'real iBeam smoke response included forbidden value marker: {forbidden}')
PY
  rm -f "$smoke_file"
}

main() {
  assert_template_is_safe
  assert_apphost_ibeam_manifest_contract
  assert_status_payloads_are_redacted
  assert_optional_real_ibeam_https_smoke
}

main "$@"
