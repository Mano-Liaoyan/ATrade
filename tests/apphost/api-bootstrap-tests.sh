#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

api_pid=''
api_log=''
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
}

trap cleanup EXIT

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for api-bootstrap-tests.sh\n' >&2
    return 1
  fi

  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local apphost_project="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"
  local apphost_program="$repo_root/src/ATrade.AppHost/Program.cs"

  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Api'
  assert_file_contains "$api_project" 'Microsoft.NET.Sdk.Web'
  assert_file_contains "$api_project" 'ATrade.ServiceDefaults.csproj'
  assert_file_contains "$api_program" 'builder.AddServiceDefaults()'
  assert_file_contains "$api_program" 'app.MapGet("/health", () => Results.Text("ok", "text/plain"));'
  assert_file_contains "$apphost_project" 'ATrade.Api.csproj'
  assert_file_contains "$apphost_program" 'AddProject<Projects.ATrade_Api>("api")'

  dotnet build "$repo_root/ATrade.sln" --nologo --verbosity minimal >/dev/null

  api_log="$(mktemp)"
  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local http_code=''
  local response_file
  response_file="$(mktemp)"

  for attempt in {1..40}; do
    http_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$http_code" == '200' ]]; then
      break
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      rm -f "$response_file"
      return 1
    fi

    sleep 0.5
  done

  if [[ "$http_code" != '200' ]]; then
    printf 'expected GET %s/health to return HTTP 200, got %s\n' "$api_url" "$http_code" >&2
    cat "$api_log" >&2
    rm -f "$response_file"
    return 1
  fi

  local response
  response="$(cat "$response_file")"
  rm -f "$response_file"

  if [[ "$response" != 'ok' ]]; then
    printf 'expected GET %s/health to return ok, got %s\n' "$api_url" "$response" >&2
    return 1
  fi
}

main "$@"
