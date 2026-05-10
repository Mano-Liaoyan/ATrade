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
  node - <<'NODE'
const net = require('node:net');
const server = net.createServer();
server.listen(0, '127.0.0.1', () => {
  console.log(server.address().port);
  server.close();
});
NODE
}

publish_manifest() {
  local output_path="$1"
  local integration_enabled="$2"
  local username="$3"
  local password="$4"
  local account_id="$5"

  ATRADE_INFRASTRUCTURE_MODE=compose \
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
  node - "$repo_root/.env.template" <<'NODE'
const fs = require('node:fs');
const templatePath = process.argv[2];
const values = {};
for (const rawLine of fs.readFileSync(templatePath, 'utf8').split(/\r?\n/)) {
  const line = rawLine.trim();
  if (!line || line.startsWith('#')) continue;
  const separator = line.indexOf('=');
  if (separator <= 0) throw new Error(`invalid env line in ${templatePath}: ${rawLine}`);
  values[line.slice(0, separator)] = line.slice(separator + 1);
}
const required = {
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_BROKER_ACCOUNT_MODE: 'Paper',
  ATRADE_IBKR_GATEWAY_URL: 'https://127.0.0.1:5000',
  ATRADE_IBKR_GATEWAY_PORT: '5000',
  ATRADE_IBKR_GATEWAY_IMAGE: 'voyz/ibeam:latest',
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS: '15',
  ATRADE_IBKR_USERNAME: 'IBKR_USERNAME',
  ATRADE_IBKR_PASSWORD: 'IBKR_PASSWORD',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: 'IBKR_ACCOUNT_ID',
};
for (const [key, expected] of Object.entries(required)) if (values[key] !== expected) throw new Error(`${key} expected ${expected}, found ${values[key]}`);
const safe = new Set(['ATRADE_POSTGRES_PASSWORD', 'ATRADE_TIMESCALEDB_PASSWORD']);
for (const [key, value] of Object.entries(values)) {
  const upperKey = key.toUpperCase();
  const upperValue = value.toUpperCase();
  if (['TOKEN', 'SESSION', 'COOKIE', 'SECRET'].some((token) => upperKey.includes(token))) throw new Error(`committed env template must not introduce unsafe key: ${key}`);
  if (['ATRADE_IBKR_USERNAME', 'ATRADE_IBKR_PASSWORD', 'ATRADE_IBKR_PAPER_ACCOUNT_ID'].includes(key) || safe.has(key)) continue;
  if (['PASSWORD', 'TOKEN', 'SESSION', 'COOKIE', 'SECRET'].some((token) => upperValue.includes(token))) throw new Error(`suspicious credential-like value for ${key}`);
}
if (/^(DU|U)\d+$/.test(values.ATRADE_IBKR_PAPER_ACCOUNT_ID)) throw new Error('committed paper account id must remain an obvious placeholder');
if (values.ATRADE_BROKER_INTEGRATION_ENABLED.toLowerCase() !== 'false') throw new Error('broker integration must stay disabled by default');
for (const [key, value] of Object.entries(values)) if (key !== 'ATRADE_BROKER_ACCOUNT_MODE' && value.toLowerCase() === 'live') throw new Error('committed defaults must not enable live behavior');
NODE
}

assert_apphost_ibeam_manifest_contract() {
  manifest_path="$(mktemp --suffix=.json)"
  enabled_manifest_path="$(mktemp --suffix=.json)"

  publish_manifest "$manifest_path" false IBKR_USERNAME IBKR_PASSWORD IBKR_ACCOUNT_ID
  publish_manifest "$enabled_manifest_path" true REAL_USERNAME_SHOULD_NOT_SURFACE REAL_PASSWORD_SHOULD_NOT_SURFACE DU1234567

  node - "$manifest_path" "$enabled_manifest_path" "$repo_root/compose.yaml" "$repo_root/src/ATrade.AppHost/ibeam-inputs/conf.yaml" <<'NODE'
const fs = require('node:fs');
const disabledManifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const enabledText = fs.readFileSync(process.argv[3], 'utf8');
const enabledManifest = JSON.parse(enabledText);
const composeText = fs.readFileSync(process.argv[4], 'utf8');
const ibeamConfText = fs.readFileSync(process.argv[5], 'utf8');
if (!composeText.includes('ibkr-gateway:') || !composeText.includes('- ibkr')) throw new Error('Compose file must own ibkr-gateway behind the ibkr profile');
if (!composeText.includes('IBEAM_ACCOUNT:') || !composeText.includes('IBEAM_PASSWORD:')) throw new Error('Compose iBeam service must map verified credential inputs');
if ((disabledManifest.resources || {})['ibkr-gateway']) throw new Error('default disabled AppHost manifest must not start ibkr-gateway');
const enabledResources = enabledManifest.resources || {};
if (enabledResources['ibkr-gateway']) throw new Error('Compose-owned ibkr-gateway must not appear in the default AppHost manifest');
for (const resourceName of ['api', 'ibkr-worker']) {
  const env = enabledResources[resourceName]?.env || {};
  if (env.ATRADE_BROKER_INTEGRATION_ENABLED !== 'true') throw new Error(`${resourceName} must receive broker integration flag`);
  if (env.ATRADE_IBKR_USERNAME !== '{ibkr-username.value}' || env.ATRADE_IBKR_PASSWORD !== '{ibkr-password.value}') throw new Error(`${resourceName} must receive redacted iBeam credential parameter references`);
}
for (const required of ['172.16.*', '172.31.*', '192.168.*', '10.*', '127.0.0.1']) if (!ibeamConfText.includes(required)) throw new Error(`iBeam custom conf.yaml must allow ${required}`);
for (const forbidden of ['IBKR_USERNAME', 'IBKR_PASSWORD', 'IBKR_ACCOUNT_ID', 'REAL_USERNAME', 'REAL_PASSWORD', 'DU1234567']) if (ibeamConfText.includes(forbidden)) throw new Error(`iBeam custom conf.yaml contains forbidden ${forbidden}`);
for (const resourceName of ['ibkr-username', 'ibkr-password', 'ibkr-paper-account-id']) {
  const resource = enabledResources[resourceName];
  if (!resource || resource.type !== 'parameter.v0') throw new Error(`missing secret parameter resource ${resourceName}`);
  if (resource.inputs?.value?.secret !== true) throw new Error(`${resourceName} must be marked secret`);
}
for (const forbidden of ['REAL_USERNAME_SHOULD_NOT_SURFACE', 'REAL_PASSWORD_SHOULD_NOT_SURFACE', 'DU1234567']) if (enabledText.includes(forbidden)) throw new Error(`AppHost manifest leaked raw value ${forbidden}`);
NODE
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

  node - "$status_file" "$configured_status_file" <<'NODE'
const fs = require('node:fs');
const missing = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const configured = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
if (missing.state !== 'credentials-missing') throw new Error(`placeholder credentials must produce credentials-missing status: ${JSON.stringify(missing)}`);
if (configured.state !== 'ibeam-container-configured') throw new Error(`configured but unreachable iBeam must produce safe configured status: ${JSON.stringify(configured)}`);
for (const payload of [missing, configured]) {
  const serialized = JSON.stringify(payload);
  for (const forbidden of ['IBKR_USERNAME', 'IBKR_PASSWORD', 'IBKR_ACCOUNT_ID', 'REAL_USERNAME_SHOULD_NOT_LEAK', 'REAL_PASSWORD_SHOULD_NOT_LEAK', 'DU1234567', 'sessionCookie', 'token']) {
    if (serialized.includes(forbidden)) throw new Error(`status payload leaked forbidden value: ${forbidden}`);
  }
  for (const unsafe of ['paperAccountId', 'gatewayUrl', 'username', 'password']) if (Object.hasOwn(payload, unsafe)) throw new Error(`status payload exposed unsafe field: ${unsafe}`);
}
NODE
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

  node - "$smoke_file" <<'NODE'
const fs = require('node:fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (typeof payload.authenticated !== 'boolean' || typeof payload.connected !== 'boolean') throw new Error('real iBeam auth-status smoke response must include boolean authenticated and connected fields');
const serialized = JSON.stringify(payload);
for (const forbidden of ['IBKR_USERNAME', 'IBKR_PASSWORD', 'IBKR_ACCOUNT_ID', 'sessionCookie', 'cookie', 'token']) if (serialized.includes(forbidden)) throw new Error(`real iBeam smoke response included forbidden marker: ${forbidden}`);
NODE
  rm -f "$smoke_file"
}

main() {
  assert_template_is_safe
  assert_apphost_ibeam_manifest_contract
  assert_status_payloads_are_redacted
  assert_optional_real_ibeam_https_smoke
}

main "$@"
