#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$repo_root/compose.yaml"
env_template_path="$repo_root/.env.template"
unix_helper="$repo_root/scripts/compose-infra.sh"
ps_helper="$repo_root/scripts/compose-infra.ps1"

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

assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'expected output to contain %s\noutput: %s\n' "$needle" "$haystack" >&2
    return 1
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" == *"$needle"* ]]; then
    printf 'expected output to not contain %s\noutput: %s\n' "$needle" "$haystack" >&2
    return 1
  fi
}

run_unix_helper() {
  env \
    ATRADE_COMPOSE_DRY_RUN=true \
    ATRADE_COMPOSE_COMMAND="${ATRADE_TEST_COMPOSE_COMMAND-}" \
    ATRADE_COMPOSE_PROJECT_NAME="${ATRADE_TEST_COMPOSE_PROJECT_NAME-atrade}" \
    ATRADE_BROKER_INTEGRATION_ENABLED="${ATRADE_TEST_BROKER_ENABLED-false}" \
    ATRADE_IBKR_USERNAME="${ATRADE_TEST_IBKR_USERNAME-IBKR_USERNAME}" \
    ATRADE_IBKR_PASSWORD="${ATRADE_TEST_IBKR_PASSWORD-IBKR_PASSWORD}" \
    ATRADE_ANALYSIS_ENGINE="${ATRADE_TEST_ANALYSIS_ENGINE-none}" \
    ATRADE_LEAN_RUNTIME_MODE="${ATRADE_TEST_LEAN_RUNTIME_MODE-cli}" \
    "$unix_helper" "$@"
}

assert_command_selection() {
  local output=''
  output="$(ATRADE_TEST_COMPOSE_COMMAND='' run_unix_helper config)"
  assert_contains "$output" 'podman compose '
  assert_contains "$output" " -f $compose_file --project-name atrade config"

  output="$(ATRADE_TEST_COMPOSE_COMMAND='custom compose' run_unix_helper config)"
  assert_contains "$output" 'custom compose '
  assert_not_contains "$output" 'podman compose'
  assert_contains "$output" " -f $compose_file --project-name atrade config"

  local tmp_dir=''
  tmp_dir="$(mktemp -d)"
  cat >"$tmp_dir/docker" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
  chmod +x "$tmp_dir/docker"
  output="$(PATH="$tmp_dir:/usr/bin:/bin" ATRADE_TEST_COMPOSE_COMMAND='' run_unix_helper config)"
  rm -rf "$tmp_dir"
  assert_contains "$output" 'docker compose '
  assert_not_contains "$output" 'podman compose'
}

assert_profile_selection() {
  local output=''
  output="$(ATRADE_TEST_COMPOSE_COMMAND='custom compose' run_unix_helper up)"
  assert_not_contains "$output" '--profile ibkr'
  assert_not_contains "$output" '--profile lean'
  assert_contains "$output" ' up -d'

  output="$(ATRADE_TEST_COMPOSE_COMMAND='custom compose' ATRADE_TEST_BROKER_ENABLED=true ATRADE_TEST_IBKR_USERNAME=paper-user ATRADE_TEST_IBKR_PASSWORD=paper-password run_unix_helper up)"
  assert_contains "$output" '--profile ibkr'
  assert_not_contains "$output" 'paper-user'
  assert_not_contains "$output" 'paper-password'

  output="$(ATRADE_TEST_COMPOSE_COMMAND='custom compose' ATRADE_TEST_ANALYSIS_ENGINE=Lean ATRADE_TEST_LEAN_RUNTIME_MODE=docker run_unix_helper up)"
  assert_contains "$output" '--profile lean'
}

assert_powershell_helper_matches_core_behavior_when_available() {
  local shell_command=''
  if command -v pwsh >/dev/null 2>&1; then
    shell_command='pwsh'
  elif command -v powershell >/dev/null 2>&1; then
    shell_command='powershell'
  else
    printf 'SKIP: PowerShell not available; Unix helper coverage remains authoritative here.\n'
    return 0
  fi

  local output=''
  output="$(env ATRADE_COMPOSE_DRY_RUN=true ATRADE_COMPOSE_COMMAND='custom compose' ATRADE_BROKER_INTEGRATION_ENABLED=true ATRADE_IBKR_USERNAME=paper-user ATRADE_IBKR_PASSWORD=paper-password ATRADE_ANALYSIS_ENGINE=Lean ATRADE_LEAN_RUNTIME_MODE=docker "$shell_command" -NoProfile -ExecutionPolicy Bypass -File "$ps_helper" up)"
  assert_contains "$output" 'custom compose '
  assert_contains "$output" '--profile ibkr'
  assert_contains "$output" '--profile lean'
  assert_not_contains "$output" 'paper-user'
  assert_not_contains "$output" 'paper-password'
}

assert_compose_static_contract() {
  assert_file_contains "$compose_file" 'name: "${ATRADE_COMPOSE_PROJECT_NAME:-atrade}"'
  assert_file_contains "$compose_file" '  postgres:'
  assert_file_contains "$compose_file" '  timescaledb:'
  assert_file_contains "$compose_file" '  redis:'
  assert_file_contains "$compose_file" '  nats:'
  assert_file_contains "$compose_file" '127.0.0.1:${ATRADE_POSTGRES_PORT:-5432}:5432'
  assert_file_contains "$compose_file" '127.0.0.1:${ATRADE_TIMESCALEDB_PORT:-5433}:5432'
  assert_file_contains "$compose_file" '127.0.0.1:${ATRADE_REDIS_PORT:-6379}:6379'
  assert_file_contains "$compose_file" '127.0.0.1:${ATRADE_NATS_PORT:-4222}:4222'
  assert_file_contains "$compose_file" 'name: "${ATRADE_POSTGRES_DATA_VOLUME:-atrade-postgres-data}"'
  assert_file_contains "$compose_file" 'name: "${ATRADE_TIMESCALEDB_DATA_VOLUME:-atrade-timescaledb-data}"'
  assert_file_contains "$compose_file" 'target: /var/lib/postgresql/data'
  assert_file_contains "$compose_file" 'pids_limit: 2048'
  assert_file_contains "$compose_file" 'TS_TUNE_MEMORY: 512MB'
  assert_file_contains "$compose_file" 'TS_TUNE_NUM_CPUS: "2"'
  assert_file_contains "$compose_file" '  ibkr-gateway:'
  assert_file_contains "$compose_file" '      - ibkr'
  assert_file_contains "$compose_file" 'IBEAM_ACCOUNT: "${ATRADE_IBKR_USERNAME:-IBKR_USERNAME}"'
  assert_file_contains "$compose_file" 'IBEAM_PASSWORD: "${ATRADE_IBKR_PASSWORD:-IBKR_PASSWORD}"'
  assert_file_contains "$compose_file" 'source: ./src/ATrade.AppHost/ibeam-inputs'
  assert_file_contains "$compose_file" '  lean-engine:'
  assert_file_contains "$compose_file" '      - lean'
  assert_file_contains "$compose_file" 'container_name: "${ATRADE_LEAN_MANAGED_CONTAINER_NAME:-atrade-lean-engine}"'
  assert_file_contains "$compose_file" 'target: "${ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT:-/workspace}"'

  local pids_count=''
  pids_count="$(grep -F 'pids_limit: 2048' "$compose_file" | wc -l | tr -d '[:space:]')"
  if [[ "$pids_count" -lt 4 ]]; then
    printf 'expected at least 4 pids_limit entries, found %s\n' "$pids_count" >&2
    return 1
  fi
}

assert_env_and_committed_files_are_safe() {
  node - <<'JS' "$env_template_path" "$compose_file" "$unix_helper" "$ps_helper"
const fs = require('fs');
const [envPath, composePath, unixHelperPath, psHelperPath] = process.argv.slice(2);
const values = new Map();
for (const raw of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
  const line = raw.trim();
  if (!line || line.startsWith('#')) continue;
  const index = line.indexOf('=');
  if (index <= 0) continue;
  values.set(line.slice(0, index).trim(), line.slice(index + 1).trim().replace(/^['"]|['"]$/g, ''));
}
const expected = {
  ATRADE_COMPOSE_COMMAND: '',
  ATRADE_COMPOSE_PROJECT_NAME: 'atrade',
  ATRADE_POSTGRES_PORT: '5432',
  ATRADE_TIMESCALEDB_PORT: '5433',
  ATRADE_REDIS_PORT: '6379',
  ATRADE_NATS_PORT: '4222',
  ATRADE_IBKR_USERNAME: 'IBKR_USERNAME',
  ATRADE_IBKR_PASSWORD: 'IBKR_PASSWORD',
  ATRADE_IBKR_PAPER_ACCOUNT_ID: 'IBKR_ACCOUNT_ID',
};
for (const [key, expectedValue] of Object.entries(expected)) {
  if (!values.has(key)) throw new Error(`${key} missing from .env.template`);
  if (values.get(key) !== expectedValue) throw new Error(`${key} expected ${JSON.stringify(expectedValue)}, found ${JSON.stringify(values.get(key))}`);
}
for (const [key, value] of values) {
  if (/^(DU|U)\d+$/i.test(value)) throw new Error(`${key} contains a real-looking broker account id`);
  if (/(TOKEN|COOKIE|SESSION)/i.test(key)) throw new Error(`${key} token/session/cookie-bearing key must not be committed`);
  if (key !== 'ATRADE_BROKER_ACCOUNT_MODE' && value.toLowerCase() === 'live') throw new Error(`${key} must not default to live mode`);
}
for (const path of [composePath, unixHelperPath, psHelperPath]) {
  const text = fs.readFileSync(path, 'utf8');
  if (/(DU|U)\d{4,}/i.test(text)) throw new Error(`${path} contains a real-looking broker account id`);
  if (/paper-password-secret/i.test(text)) throw new Error(`${path} contains a test secret sentinel`);
}
JS
}

assert_optional_live_compose_config_skips_or_passes() {
  if podman compose version >/dev/null 2>&1; then
    ATRADE_COMPOSE_COMMAND='podman compose' "$unix_helper" config >/dev/null
    printf 'Live Podman Compose config check passed.\n'
    return 0
  fi

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ATRADE_COMPOSE_COMMAND='docker compose' "$unix_helper" config >/dev/null
    printf 'Live Docker Compose config check passed.\n'
    return 0
  fi

  printf 'SKIP: no runnable Podman Compose or Docker Compose engine detected; static Compose contract checks passed.\n'
}

main() {
  assert_command_selection
  assert_profile_selection
  assert_powershell_helper_matches_core_behavior_when_available
  assert_compose_static_contract
  assert_env_and_committed_files_are_safe
  assert_optional_live_compose_config_skips_or_passes
}

main "$@"
