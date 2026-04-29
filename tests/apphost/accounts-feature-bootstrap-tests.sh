#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"

export ATRADE_API_HTTP_PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
atrade_load_local_port_contract "$repo_root"

api_pid=''
api_log=''
health_file=''
overview_file=''
api_url="http://127.0.0.1:${ATRADE_API_HTTP_PORT}"

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

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  if [[ -n "$api_log" && -f "$api_log" ]]; then
    rm -f "$api_log"
  fi

  if [[ -n "$health_file" && -f "$health_file" ]]; then
    rm -f "$health_file"
  fi

  if [[ -n "$overview_file" && -f "$overview_file" ]]; then
    rm -f "$overview_file"
  fi
}

trap cleanup EXIT

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for accounts-feature-bootstrap-tests.sh\n' >&2
    return 1
  fi

  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local accounts_project="$repo_root/src/ATrade.Accounts/ATrade.Accounts.csproj"
  local accounts_service="$repo_root/src/ATrade.Accounts/AccountOverviewService.cs"

  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Accounts'
  assert_file_contains "$api_project" 'ATrade.Accounts.csproj'
  assert_file_contains "$api_program" 'builder.Services.AddAccountsModule();'
  assert_file_contains "$api_program" 'app.MapGet("/api/accounts/overview"'
  assert_file_contains "$accounts_project" 'Microsoft.AspNetCore.App'
  assert_file_contains "$accounts_service" 'AccountOverview.Bootstrap'

  dotnet build "$repo_root/ATrade.sln" --nologo --verbosity minimal >/dev/null

  api_log="$(mktemp)"
  health_file="$(mktemp)"
  overview_file="$(mktemp)"

  # Start the API directly, without AppHost-managed infrastructure or broker/data services.
  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local health_code=''
  local overview_code=''

  for attempt in {1..40}; do
    health_code="$(curl --silent --show-error --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$health_code" == '200' ]]; then
      break
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  if [[ "$health_code" != '200' ]]; then
    printf 'expected GET %s/health to return HTTP 200, got %s\n' "$api_url" "$health_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  if [[ "$(cat "$health_file")" != 'ok' ]]; then
    printf 'expected GET %s/health to return ok, got %s\n' "$api_url" "$(cat "$health_file")" >&2
    return 1
  fi

  overview_code="$(curl --silent --show-error --output "$overview_file" --write-out '%{http_code}' "$api_url/api/accounts/overview")"

  if [[ "$overview_code" != '200' ]]; then
    printf 'expected GET %s/api/accounts/overview to return HTTP 200, got %s\n' "$api_url" "$overview_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$overview_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
expected = {
    "module": "accounts",
    "status": "bootstrap",
    "brokerConnection": "not-configured",
    "accounts": [],
}
if payload != expected:
    raise SystemExit(f"unexpected payload: {payload!r}")
PY
}

main "$@"
