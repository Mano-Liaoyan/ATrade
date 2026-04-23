#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_pid=''
frontend_log=''
manifest_path=''
frontend_url='http://127.0.0.1:3111'

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
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

  if [[ -n "$frontend_log" && -f "$frontend_log" ]]; then
    rm -f "$frontend_log"
  fi

  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
}

trap cleanup EXIT

assert_frontend_contract_files() {
  assert_file_contains "$repo_root/frontend/package.json" '"dev": "next dev --hostname 0.0.0.0"'
  assert_file_contains "$repo_root/frontend/package.json" '"build": "next build"'
  assert_file_contains "$repo_root/frontend/package.json" '"start": "next start"'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'ATrade Frontend Home'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'Next.js Bootstrap Slice'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'Aspire AppHost Frontend Contract'
  assert_file_contains "$repo_root/frontend/app/layout.tsx" "import './globals.css';"
  assert_file_contains "$repo_root/frontend/next-env.d.ts" '/// <reference types="next" />'
  assert_file_contains "$repo_root/frontend/tsconfig.json" '"name": "next"'
}

assert_direct_frontend_startup() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-nextjs-bootstrap-tests.sh\n' >&2
    return 1
  fi

  (cd "$repo_root/frontend" && npm ci --no-fund --no-audit >/dev/null)

  frontend_log="$(mktemp)"
  (
    cd "$repo_root/frontend"
    PORT="${frontend_url##*:}" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  local response_file
  response_file="$(mktemp)"
  local http_code=''
  local attempt

  for attempt in {1..60}; do
    http_code="$(curl --silent --output "$response_file" --write-out '%{http_code}' "$frontend_url/" || true)"
    if [[ "$http_code" == '200' ]]; then
      break
    fi

    if ! kill -0 "$frontend_pid" 2>/dev/null; then
      printf 'frontend exited before serving the home page.\n' >&2
      cat "$frontend_log" >&2
      rm -f "$response_file"
      return 1
    fi

    sleep 0.5
  done

  if [[ "$http_code" != '200' ]]; then
    printf 'expected GET %s/ to return HTTP 200, got %s\n' "$frontend_url" "$http_code" >&2
    cat "$frontend_log" >&2
    rm -f "$response_file"
    return 1
  fi

  assert_file_contains "$response_file" 'ATrade Frontend Home'
  assert_file_contains "$response_file" 'Next.js Bootstrap Slice'
  assert_file_contains "$response_file" 'Aspire AppHost Frontend Contract'
  rm -f "$response_file"
}

assert_apphost_manifest_preserves_frontend_resource() {
  manifest_path="$(mktemp --suffix=.json)"
  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
  assert_file_contains "$manifest_path" '"api"'
  assert_file_contains "$manifest_path" '"frontend"'
  assert_file_contains "$manifest_path" '"targetPort": 3000'
  assert_file_contains "$manifest_path" '"external": true'
  assert_file_contains "$manifest_path" '"PORT": "{frontend.bindings.http.targetPort}"'
}

main() {
  assert_frontend_contract_files
  assert_direct_frontend_startup
  assert_apphost_manifest_preserves_frontend_resource
}

main "$@"
