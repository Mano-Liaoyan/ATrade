#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
postgres_image='postgres:17.6'
postgres_password='atrade_paper_capital_test_password'
postgres_db='atrade_paper_capital_test'
postgres_container=''
api_pid=''
api_url=''
temp_dir=''

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  if [[ -n "$postgres_container" ]]; then
    docker rm -f "$postgres_container" >/dev/null 2>&1 || true
  fi

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf "$temp_dir"
  fi
}

trap cleanup EXIT

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s is required for paper-capital-source-tests.sh\n' "$tool" >&2
    return 1
  fi
}

free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

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

  if grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

fail_with_logs() {
  printf '%s\n' "$1" >&2

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    printf '\n=== API log tail ===\n' >&2
    find "$temp_dir" -name 'api-*.log' -print -exec tail -n 120 {} \; >&2 || true
  fi

  if [[ -n "$postgres_container" ]]; then
    printf '\n=== Postgres container logs ===\n' >&2
    docker logs "$postgres_container" 2>&1 | tail -n 120 >&2 || true
  fi

  return 1
}

wait_for_http_200() {
  local url="$1"
  local output_file="$2"
  local code=''

  for _ in $(seq 1 120); do
    code="$(curl --silent --output "$output_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      fail_with_logs "ATrade.Api exited before $url returned HTTP 200."
      return 1
    fi

    sleep 0.5
  done

  fail_with_logs "Expected $url to return HTTP 200, got $code."
}

request_json() {
  local method="$1"
  local path="$2"
  local payload="$3"
  local output_file="$4"
  local expected_code="$5"
  local code

  if [[ -n "$payload" ]]; then
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --request "$method" \
      --header 'Accept: application/json' \
      --header 'Content-Type: application/json' \
      --data "$payload" \
      "$api_url$path")"
  else
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --request "$method" \
      --header 'Accept: application/json' \
      "$api_url$path")"
  fi

  if [[ "$code" != "$expected_code" ]]; then
    printf 'Expected %s %s to return HTTP %s, got %s. Response:\n' "$method" "$path" "$expected_code" "$code" >&2
    cat "$output_file" >&2
    printf '\n' >&2
    fail_with_logs 'Unexpected API response.'
    return 1
  fi
}

start_api() {
  local api_port="$1"
  local postgres_port="${2:-}"
  local api_log
  local health_response

  api_url="http://127.0.0.1:${api_port}"
  api_log="$(mktemp "$temp_dir/api-log-XXXXXX")"
  health_response="$(mktemp "$temp_dir/health-response-XXXXXX")"

  if [[ -n "$postgres_port" ]]; then
    local connection_string="Host=127.0.0.1;Port=${postgres_port};Database=${postgres_db};Username=postgres;Password=${postgres_password};Include Error Detail=true"
    ASPNETCORE_URLS="$api_url" \
      ATRADE_IBKR_INTEGRATION_ENABLED='false' \
      ConnectionStrings__postgres="$connection_string" \
      dotnet run --project "$api_project" >"$api_log" 2>&1 &
  else
    ASPNETCORE_URLS="$api_url" \
      ATRADE_IBKR_INTEGRATION_ENABLED='false' \
      dotnet run --project "$api_project" >"$api_log" 2>&1 &
  fi
  api_pid=$!

  wait_for_http_200 "$api_url/health" "$health_response"
  if [[ "$(cat "$health_response")" != 'ok' ]]; then
    fail_with_logs 'Expected ATrade.Api health endpoint to return ok.'
    return 1
  fi
}

stop_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  api_pid=''
}

wait_for_postgres() {
  for _ in $(seq 1 60); do
    if docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" pg_isready -U postgres -d "$postgres_db" >/dev/null 2>&1; then
      return 0
    fi

    sleep 1
  done

  fail_with_logs 'Timed out waiting for disposable Postgres to accept connections.'
}

start_postgres() {
  local postgres_port="$1"
  postgres_container="atrade-paper-capital-test-$RANDOM-$RANDOM"

  docker run \
    --detach \
    --name "$postgres_container" \
    --pids-limit 2048 \
    --publish "127.0.0.1:${postgres_port}:5432" \
    --env POSTGRES_PASSWORD="$postgres_password" \
    --env POSTGRES_DB="$postgres_db" \
    "$postgres_image" >/dev/null

  wait_for_postgres
}

assert_no_sensitive_response_values() {
  local response_file="$1"
  if grep -Eiq 'PAPER_TEST_ACCOUNT|DU[0-9]{4,}|password|secret|token|cookie|session|https?://' "$response_file"; then
    printf 'paper capital response leaked a sensitive value:\n' >&2
    cat "$response_file" >&2
    return 1
  fi
}

assert_unavailable_payload() {
  local response_file="$1"
  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
assert payload["source"] == "unavailable", payload
assert payload["effectiveCapital"] is None, payload
assert payload["currency"] == "USD", payload
assert payload["ibkrAvailable"]["available"] is False, payload
assert payload["localConfigured"] is False, payload
assert payload["localCapital"] is None, payload
assert any(message["code"] == "paper-capital-source-unavailable" for message in payload["messages"]), payload
PY
  assert_no_sensitive_response_values "$response_file"
}

assert_local_payload() {
  local response_file="$1"
  local expected_amount="$2"
  python3 - "$response_file" "$expected_amount" <<'PY'
import json, sys
from decimal import Decimal
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
expected = Decimal(sys.argv[2])
assert payload["source"] == "local-paper-ledger", payload
assert Decimal(str(payload["effectiveCapital"])) == expected, payload
assert payload["currency"] == "USD", payload
assert payload["localConfigured"] is True, payload
assert Decimal(str(payload["localCapital"])) == expected, payload
assert payload["ibkrAvailable"]["available"] is False, payload
PY
  assert_no_sensitive_response_values "$response_file"
}

assert_error_payload() {
  local response_file="$1"
  local expected_code="$2"
  python3 - "$response_file" "$expected_code" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
assert payload["code"] == sys.argv[2], payload
assert "account" not in payload["error"].lower() or sys.argv[2] == "invalid-paper-capital-payload", payload
assert "PAPER_TEST_ACCOUNT" not in payload["error"], payload
assert "password" not in payload["error"].lower(), payload
assert "token" not in payload["error"].lower(), payload
PY
}

assert_schema_initialized_without_account_columns() {
  local initialized
  local account_columns
  initialized="$(docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" \
    psql -U postgres -d "$postgres_db" -tAc "SELECT to_regclass('atrade_accounts.local_paper_capital') IS NOT NULL;" | tr -d '[:space:]')"

  if [[ "$initialized" != 't' ]]; then
    fail_with_logs 'Expected local paper capital table to exist after first update.'
    return 1
  fi

  account_columns="$(docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" \
    psql -U postgres -d "$postgres_db" -tAc "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'atrade_accounts' AND table_name = 'local_paper_capital' AND column_name ILIKE '%account%';" | tr -d '[:space:]')"

  if [[ "$account_columns" != '0' ]]; then
    fail_with_logs 'Local paper capital table must not persist provider account columns.'
    return 1
  fi
}

validate_source_contract() {
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  assert_file_contains "$api_program" 'builder.Services.AddAccountsModule(builder.Configuration);'
  assert_file_contains "$api_program" 'app.MapGet('
  assert_file_contains "$api_program" '"/api/accounts/paper-capital"'
  assert_file_contains "$api_program" 'app.MapPut('
  assert_file_contains "$api_program" '"/api/accounts/local-paper-capital"'
  assert_file_contains "$api_program" 'ToPaperCapitalIntakeResult'
  assert_file_not_contains "$api_program" 'PaperAccountId'
  assert_file_not_contains "$api_program" 'GatewayBaseUrl'
  assert_file_not_contains "$api_program" 'Password'
  assert_file_contains "$repo_root/src/ATrade.Accounts/AccountsModuleServiceCollectionExtensions.cs" 'IAccountsPostgresDataSourceProvider'
  assert_file_contains "$repo_root/src/ATrade.Accounts/AccountsModuleServiceCollectionExtensions.cs" 'IPaperCapitalService'
  assert_file_contains "$repo_root/src/ATrade.Brokers.Ibkr/IbkrAccountSummaryClient.cs" '/v1/api/portfolio/{0}/summary'
  assert_file_contains "$repo_root/ATrade.slnx" 'tests/ATrade.Accounts.Tests/ATrade.Accounts.Tests.csproj'
}

run_without_postgres_checks() {
  local response
  local api_port

  api_port="$(free_port)"
  start_api "$api_port"

  response="$(mktemp "$temp_dir/paper-capital-unconfigured-XXXXXX")"
  request_json GET '/api/accounts/paper-capital' '' "$response" 200
  assert_unavailable_payload "$response"

  response="$(mktemp "$temp_dir/paper-capital-invalid-XXXXXX")"
  request_json PUT '/api/accounts/local-paper-capital' '{"amount":0,"currency":"USD"}' "$response" 400
  assert_error_payload "$response" 'invalid-paper-capital-amount'

  response="$(mktemp "$temp_dir/paper-capital-sensitive-XXXXXX")"
  request_json PUT '/api/accounts/local-paper-capital' '{"amount":1000,"currency":"USD","accountId":"PAPER_TEST_ACCOUNT"}' "$response" 400
  assert_error_payload "$response" 'invalid-paper-capital-payload'

  response="$(mktemp "$temp_dir/paper-capital-storage-XXXXXX")"
  request_json PUT '/api/accounts/local-paper-capital' '{"amount":1000,"currency":"USD"}' "$response" 503
  assert_error_payload "$response" 'paper-capital-storage-unavailable'

  stop_api
}

run_with_postgres_checks() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping Postgres-backed paper capital persistence check.\n'
    return 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping Postgres-backed paper capital persistence check.\n'
    return 0
  fi

  local postgres_port
  local api_port
  local response

  postgres_port="$(free_port)"
  start_postgres "$postgres_port"

  api_port="$(free_port)"
  start_api "$api_port" "$postgres_port"

  response="$(mktemp "$temp_dir/paper-capital-postgres-unconfigured-XXXXXX")"
  request_json GET '/api/accounts/paper-capital' '' "$response" 200
  assert_unavailable_payload "$response"

  response="$(mktemp "$temp_dir/paper-capital-postgres-put-XXXXXX")"
  request_json PUT '/api/accounts/local-paper-capital' '{"amount":25000.129,"currency":"usd"}' "$response" 200
  assert_local_payload "$response" '25000.13'
  assert_schema_initialized_without_account_columns

  stop_api
  api_port="$(free_port)"
  start_api "$api_port" "$postgres_port"

  response="$(mktemp "$temp_dir/paper-capital-postgres-get-XXXXXX")"
  request_json GET '/api/accounts/paper-capital' '' "$response" 200
  assert_local_payload "$response" '25000.13'
}

main() {
  require_tool curl
  require_tool python3

  temp_dir="$(mktemp -d)"
  validate_source_contract
  dotnet build "$repo_root/ATrade.slnx" --nologo --verbosity minimal >/dev/null
  run_without_postgres_checks
  run_with_postgres_checks
}

main "$@"
