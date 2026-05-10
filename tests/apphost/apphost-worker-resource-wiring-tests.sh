#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest_path=''
enabled_manifest_path=''
missing_credentials_manifest_path=''
compose_manifest_path=''

cleanup() {
  for path in "$manifest_path" "$enabled_manifest_path" "$missing_credentials_manifest_path" "$compose_manifest_path"; do
    if [[ -n "$path" && -f "$path" ]]; then
      rm -f "$path"
    fi
  done
}

trap cleanup EXIT

publish_apphost_manifest() {
  local output_path="$1"
  local integration_enabled="$2"
  local username="$3"
  local password="$4"
  local gateway_url="${5:-https://127.0.0.1:5000}"
  local gateway_port="${6:-5000}"
  local infrastructure_mode="${7:-compose}"

  ATRADE_INFRASTRUCTURE_MODE="$infrastructure_mode" \
  ATRADE_API_HTTP_PORT=5181 \
  ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES=30 \
  ATRADE_BROKER_INTEGRATION_ENABLED="$integration_enabled" \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL="$gateway_url" \
  ATRADE_IBKR_GATEWAY_PORT="$gateway_port" \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=15 \
  ATRADE_IBKR_USERNAME="$username" \
  ATRADE_IBKR_PASSWORD="$password" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID=IBKR_ACCOUNT_ID \
  ATRADE_POSTGRES_PORT=15432 \
  ATRADE_TIMESCALEDB_PORT=15433 \
  ATRADE_REDIS_PORT=16379 \
  ATRADE_NATS_PORT=14222 \
  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$output_path" >/dev/null
}

assert_secret_parameters_are_redacted() {
  node - <<'NODE' "$1"
const fs = require('fs');
const manifestPath = process.argv[2];
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const resources = manifest.resources ?? {};
for (const resourceName of ['ibkr-username', 'ibkr-password', 'ibkr-paper-account-id']) {
  const resource = resources[resourceName];
  if (!resource) throw new Error(`missing secret parameter resource: ${resourceName}`);
  if (resource.type !== 'parameter.v0') throw new Error(`${resourceName} should be a parameter resource`);
  if (resource.inputs?.value?.secret !== true) throw new Error(`${resourceName} parameter must be marked secret`);
}
NODE
}

assert_manifest_wires_worker_and_application_resources() {
  manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$manifest_path" false IBKR_USERNAME IBKR_PASSWORD
  assert_secret_parameters_are_redacted "$manifest_path"

  node - <<'NODE' "$manifest_path"
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resources = manifest.resources ?? {};
const requiredResourceTypes = {
  api: 'project.v0',
  'ibkr-worker': 'project.v0',
  frontend: 'container.v1',
};
for (const resourceName of ['postgres', 'timescaledb', 'redis', 'nats', 'ibkr-gateway', 'lean-engine']) {
  if (resources[resourceName]) throw new Error(`default Compose mode must not declare ${resourceName}`);
}
for (const [resourceName, expectedType] of Object.entries(requiredResourceTypes)) {
  const resource = resources[resourceName];
  if (!resource) throw new Error(`missing resource: ${resourceName}`);
  if (resource.type !== expectedType) throw new Error(`resource ${resourceName} expected type ${expectedType}, found ${resource.type}`);
}
const apiEnv = resources.api.env ?? {};
const workerEnv = resources['ibkr-worker'].env ?? {};
const expectedApiEnv = {
  ConnectionStrings__postgres: 'Host=127.0.0.1;Port=15432;Username=postgres;Password={postgres-password.value};Database=postgres',
  ConnectionStrings__timescaledb: 'Host=127.0.0.1;Port=15433;Username=postgres;Password={timescaledb-password.value};Database=postgres',
  ConnectionStrings__redis: '127.0.0.1:16379',
  ConnectionStrings__nats: 'nats://127.0.0.1:14222',
  ATRADE_API_HTTP_PORT: '5181',
  ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES: '30',
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_BROKER_ACCOUNT_MODE: 'Paper',
  ATRADE_IBKR_GATEWAY_URL: 'https://127.0.0.1:5000',
  ATRADE_IBKR_GATEWAY_PORT: '5000',
  ATRADE_IBKR_GATEWAY_IMAGE: 'voyz/ibeam:latest',
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS: '15',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: '{ibkr-paper-account-id.value}',
  ATRADE_IBKR_USERNAME: '{ibkr-username.value}',
  ATRADE_IBKR_PASSWORD: '{ibkr-password.value}',
};
const expectedWorkerEnv = {
  ConnectionStrings__postgres: expectedApiEnv.ConnectionStrings__postgres,
  ConnectionStrings__redis: expectedApiEnv.ConnectionStrings__redis,
  ConnectionStrings__nats: expectedApiEnv.ConnectionStrings__nats,
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_BROKER_ACCOUNT_MODE: 'Paper',
  ATRADE_IBKR_GATEWAY_URL: 'https://127.0.0.1:5000',
  ATRADE_IBKR_GATEWAY_PORT: '5000',
  ATRADE_IBKR_GATEWAY_IMAGE: 'voyz/ibeam:latest',
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS: '15',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: '{ibkr-paper-account-id.value}',
  ATRADE_IBKR_USERNAME: '{ibkr-username.value}',
  ATRADE_IBKR_PASSWORD: '{ibkr-password.value}',
};
for (const [key, expected] of Object.entries(expectedApiEnv)) {
  if (apiEnv[key] !== expected) throw new Error(`api env ${key} expected ${expected}, found ${apiEnv[key]}`);
}
for (const [key, expected] of Object.entries(expectedWorkerEnv)) {
  if (workerEnv[key] !== expected) throw new Error(`ibkr-worker env ${key} expected ${expected}, found ${workerEnv[key]}`);
}
if (workerEnv.ConnectionStrings__timescaledb || Object.keys(workerEnv).some((key) => key.startsWith('TIMESCALEDB_'))) {
  throw new Error('ibkr-worker should not receive TimescaleDB wiring in this slice');
}
NODE
}

assert_compose_mode_wires_external_infrastructure_without_secret_values() {
  compose_manifest_path="$(mktemp --suffix=.json)"
  ATRADE_POSTGRES_PASSWORD=REAL_POSTGRES_PASSWORD_SHOULD_NOT_SURFACE \
  ATRADE_TIMESCALEDB_PASSWORD=REAL_TIMESCALE_PASSWORD_SHOULD_NOT_SURFACE \
    publish_apphost_manifest "$compose_manifest_path" false IBKR_USERNAME IBKR_PASSWORD https://127.0.0.1:5000 5000 compose
  assert_secret_parameters_are_redacted "$compose_manifest_path"

  node - <<'NODE' "$compose_manifest_path"
const fs = require('fs');
const manifestPath = process.argv[2];
const text = fs.readFileSync(manifestPath, 'utf8');
for (const forbidden of ['REAL_POSTGRES_PASSWORD_SHOULD_NOT_SURFACE', 'REAL_TIMESCALE_PASSWORD_SHOULD_NOT_SURFACE']) {
  if (text.includes(forbidden)) throw new Error(`manifest exposed raw database secret value: ${forbidden}`);
}
const manifest = JSON.parse(text);
const resources = manifest.resources ?? {};
for (const resourceName of ['postgres', 'timescaledb', 'redis', 'nats', 'ibkr-gateway', 'lean-engine']) {
  if (resources[resourceName]) throw new Error(`Compose mode must not declare ${resourceName}`);
}
for (const resourceName of ['api', 'ibkr-worker', 'frontend']) {
  if (!resources[resourceName]) throw new Error(`Compose mode must keep ${resourceName}`);
}
const apiEnv = resources.api.env ?? {};
const workerEnv = resources['ibkr-worker'].env ?? {};
const expectedApi = {
  ConnectionStrings__postgres: 'Host=127.0.0.1;Port=15432;Username=postgres;Password={postgres-password.value};Database=postgres',
  ConnectionStrings__timescaledb: 'Host=127.0.0.1;Port=15433;Username=postgres;Password={timescaledb-password.value};Database=postgres',
  ConnectionStrings__redis: '127.0.0.1:16379',
  ConnectionStrings__nats: 'nats://127.0.0.1:14222',
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_IBKR_USERNAME: '{ibkr-username.value}',
  ATRADE_IBKR_PASSWORD: '{ibkr-password.value}',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: '{ibkr-paper-account-id.value}',
};
const expectedWorker = {
  ConnectionStrings__postgres: expectedApi.ConnectionStrings__postgres,
  ConnectionStrings__redis: expectedApi.ConnectionStrings__redis,
  ConnectionStrings__nats: expectedApi.ConnectionStrings__nats,
  ATRADE_BROKER_INTEGRATION_ENABLED: 'false',
  ATRADE_IBKR_USERNAME: '{ibkr-username.value}',
  ATRADE_IBKR_PASSWORD: '{ibkr-password.value}',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: '{ibkr-paper-account-id.value}',
};
for (const [key, expected] of Object.entries(expectedApi)) {
  if (apiEnv[key] !== expected) throw new Error(`api env ${key} expected ${expected}, found ${apiEnv[key]}`);
}
for (const [key, expected] of Object.entries(expectedWorker)) {
  if (workerEnv[key] !== expected) throw new Error(`ibkr-worker env ${key} expected ${expected}, found ${workerEnv[key]}`);
}
if (workerEnv.ConnectionStrings__timescaledb || Object.keys(workerEnv).some((key) => key.startsWith('TIMESCALEDB_'))) {
  throw new Error('ibkr-worker should not receive TimescaleDB wiring in Compose mode');
}
NODE
}

assert_manifest_does_not_start_ibeam_with_placeholder_credentials() {
  missing_credentials_manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$missing_credentials_manifest_path" true IBKR_USERNAME IBKR_PASSWORD
  assert_secret_parameters_are_redacted "$missing_credentials_manifest_path"

  node - <<'NODE' "$missing_credentials_manifest_path"
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resources = manifest.resources ?? {};
if (resources['ibkr-gateway']) throw new Error('ibkr-gateway must not start when enabled config still contains fake IBKR credential placeholders');
for (const resourceName of ['api', 'ibkr-worker']) {
  const env = resources[resourceName].env ?? {};
  if (env.ATRADE_BROKER_INTEGRATION_ENABLED !== 'true') throw new Error(`${resourceName} should still receive the enabled integration flag`);
  if (env.ATRADE_IBKR_PAPER_ACCOUNT_ID !== '{ibkr-paper-account-id.value}') throw new Error(`${resourceName} paper account id env must stay a secret parameter reference`);
  if (env.ATRADE_IBKR_USERNAME !== '{ibkr-username.value}') throw new Error(`${resourceName} username env must stay a secret parameter reference`);
  if (env.ATRADE_IBKR_PASSWORD !== '{ibkr-password.value}') throw new Error(`${resourceName} password env must stay a secret parameter reference`);
}
NODE
}

assert_manifest_wires_ibeam_container_when_enabled() {
  enabled_manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$enabled_manifest_path" true REAL_IBKR_USERNAME_SHOULD_NOT_SURFACE REAL_IBKR_PASSWORD_SHOULD_NOT_SURFACE https://127.0.0.1:5000 5000 apphost
  assert_secret_parameters_are_redacted "$enabled_manifest_path"

  node - <<'NODE' "$enabled_manifest_path"
const fs = require('fs');
const manifestPath = process.argv[2];
const text = fs.readFileSync(manifestPath, 'utf8');
for (const forbidden of ['REAL_IBKR_USERNAME_SHOULD_NOT_SURFACE', 'REAL_IBKR_PASSWORD_SHOULD_NOT_SURFACE', 'IBKR_ACCOUNT_ID']) {
  if (text.includes(forbidden)) throw new Error(`manifest exposed raw IBKR credential value: ${forbidden}`);
}
const manifest = JSON.parse(text);
const resources = manifest.resources ?? {};
const container = resources['ibkr-gateway'];
if (!container) throw new Error('ibkr-gateway container must be present when integration and credentials are configured');
if (container.type !== 'container.v0') throw new Error(`ibkr-gateway should be a container resource, found ${container.type}`);
if (container.image !== 'voyz/ibeam:latest') throw new Error(`ibkr-gateway must use voyz/ibeam:latest, found ${container.image}`);
const containerEnv = container.env ?? {};
if (JSON.stringify(containerEnv) !== JSON.stringify({ IBEAM_ACCOUNT: '{ibkr-username.value}', IBEAM_PASSWORD: '{ibkr-password.value}' })) {
  throw new Error(`ibkr-gateway should receive only required iBeam env vars: ${JSON.stringify(containerEnv)}`);
}
const bindMounts = container.bindMounts ?? [];
if (!bindMounts.some((mount) => mount.target === '/srv/inputs' && mount.readOnly === true && String(mount.source ?? '').includes('ibeam-inputs'))) {
  throw new Error(`ibkr-gateway must mount the repo-local iBeam inputs directory read-only: ${JSON.stringify(bindMounts)}`);
}
const httpsBinding = container.bindings?.https ?? {};
if (httpsBinding.scheme !== 'https' || httpsBinding.targetPort !== 5000) throw new Error(`ibkr-gateway HTTPS target port should be 5000, found ${JSON.stringify(httpsBinding)}`);
for (const resourceName of ['api', 'ibkr-worker']) {
  const env = resources[resourceName].env ?? {};
  if (env.ATRADE_IBKR_PAPER_ACCOUNT_ID !== '{ibkr-paper-account-id.value}') throw new Error(`${resourceName} paper account id env must be a secret parameter reference`);
  if (env.ATRADE_IBKR_USERNAME !== '{ibkr-username.value}') throw new Error(`${resourceName} username env must be a secret parameter reference`);
  if (env.ATRADE_IBKR_PASSWORD !== '{ibkr-password.value}') throw new Error(`${resourceName} password env must be a secret parameter reference`);
}
NODE
}

assert_manifest_maps_custom_ibeam_host_port_to_client_port() {
  enabled_manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$enabled_manifest_path" true REAL_IBKR_USERNAME_SHOULD_NOT_SURFACE REAL_IBKR_PASSWORD_SHOULD_NOT_SURFACE https://127.0.0.1:15000 15000 apphost
  assert_secret_parameters_are_redacted "$enabled_manifest_path"

  node - <<'NODE' "$enabled_manifest_path"
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const resources = manifest.resources ?? {};
const container = resources['ibkr-gateway'];
if (!container) throw new Error('custom-port manifest must include ibkr-gateway');
const bindMounts = container.bindMounts ?? [];
if (!bindMounts.some((mount) => mount.target === '/srv/inputs' && mount.readOnly === true && String(mount.source ?? '').includes('ibeam-inputs'))) {
  throw new Error(`custom-port ibkr-gateway must mount iBeam inputs read-only: ${JSON.stringify(bindMounts)}`);
}
const httpsBinding = container.bindings?.https ?? {};
if (httpsBinding.scheme !== 'https' || httpsBinding.targetPort !== 5000) throw new Error(`custom host gateway port must still map to iBeam Client Portal target port 5000: ${JSON.stringify(httpsBinding)}`);
for (const resourceName of ['api', 'ibkr-worker']) {
  const env = resources[resourceName].env ?? {};
  if (env.ATRADE_IBKR_GATEWAY_URL !== 'https://127.0.0.1:15000') throw new Error(`${resourceName} must receive the configured custom host gateway URL`);
  if (env.ATRADE_IBKR_GATEWAY_PORT !== '15000') throw new Error(`${resourceName} must receive the configured custom host gateway port`);
}
NODE
}

main() {
  assert_manifest_wires_worker_and_application_resources
  assert_compose_mode_wires_external_infrastructure_without_secret_values
  assert_manifest_does_not_start_ibeam_with_placeholder_credentials
  assert_manifest_wires_ibeam_container_when_enabled
  assert_manifest_maps_custom_ibeam_host_port_to_client_port
}

main "$@"
