#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

frontend_pid=''
frontend_log=''
apphost_pid=''
apphost_log=''
apphost_frontend_log=''
manifest_path=''
root_lock_created=0
frontend_url="http://127.0.0.1:${ATRADE_FRONTEND_DIRECT_HTTP_PORT}"
apphost_frontend_url="http://127.0.0.1:${ATRADE_APPHOST_FRONTEND_HTTP_PORT}"

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
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_process_environment_contains() {
  local pid="$1"
  local needle="$2"

  if [[ ! -r "/proc/$pid/environ" ]]; then
    printf 'skipping process environment check for %s because /proc environ is not readable on this platform.\n' "$needle"
    return 0
  fi

  if ! tr '\0' '\n' </proc/"$pid"/environ | grep -Fqx -- "$needle"; then
    printf 'expected process %s environment to contain %s\n' "$pid" "$needle" >&2
    tr '\0' '\n' </proc/"$pid"/environ >&2
    return 1
  fi
}

stop_frontend_dev_processes() {
  local pids=''

  pids="$(ps -eo pid=,args= | awk '/next dev --hostname 0.0.0.0|npm run dev/ && !/awk/ { print $1 }')"
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
    sleep 1
  fi
}

wait_for_http_200() {
  local url="$1"
  local response_file="$2"
  local monitored_pid="$3"
  local log_file="$4"
  local http_code=''
  local attempt

  for attempt in {1..60}; do
    http_code="$(curl --silent --output "$response_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$http_code" == '200' ]]; then
      return 0
    fi

    if [[ -n "$monitored_pid" ]] && ! kill -0 "$monitored_pid" 2>/dev/null; then
      printf 'process %s exited before serving %s\n' "$monitored_pid" "$url" >&2
      if [[ -n "$log_file" && -f "$log_file" ]]; then
        cat "$log_file" >&2
      fi
      return 1
    fi

    sleep 0.5
  done

  printf 'expected GET %s to return HTTP 200, got %s\n' "$url" "$http_code" >&2
  if [[ -n "$log_file" && -f "$log_file" ]]; then
    cat "$log_file" >&2
  fi
  return 1
}

cleanup() {
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

  if [[ -n "$apphost_pid" ]] && kill -0 "$apphost_pid" 2>/dev/null; then
    kill "$apphost_pid" 2>/dev/null || true
    wait "$apphost_pid" 2>/dev/null || true
  fi

  stop_frontend_dev_processes

  if [[ -n "$frontend_log" && -f "$frontend_log" ]]; then
    rm -f "$frontend_log"
  fi

  if [[ -n "$apphost_log" && -f "$apphost_log" ]]; then
    rm -f "$apphost_log"
  fi

  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi

  if [[ "$root_lock_created" == '1' ]]; then
    rm -f "$repo_root/package-lock.json"
  fi
}

trap cleanup EXIT

assert_frontend_contract_files() {
  assert_file_contains "$repo_root/frontend/package.json" '"dev": "next dev --hostname 0.0.0.0"'
  assert_file_contains "$repo_root/frontend/package.json" '"build": "next build"'
  assert_file_contains "$repo_root/frontend/package.json" '"start": "next start"'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'ATradeTerminalApp'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'ATrade Terminal Shell'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'Command-first paper workspace'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$repo_root/frontend/app/layout.tsx" "import './globals.css';"
  assert_file_contains "$repo_root/frontend/next-env.d.ts" '/// <reference types="next" />'
  assert_file_contains "$repo_root/frontend/tsconfig.json" '"name": "next"'
  assert_file_contains "$repo_root/frontend/next.config.ts" 'turbopack:'
  assert_file_contains "$repo_root/frontend/next.config.ts" 'root: frontendRoot'
}

assert_direct_frontend_startup() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-nextjs-bootstrap-tests.sh\n' >&2
    return 1
  fi

  stop_frontend_dev_processes
  (cd "$repo_root/frontend" && npm ci --no-fund --no-audit >/dev/null)

  frontend_log="$(mktemp)"
  (
    cd "$repo_root/frontend"
    PORT="${frontend_url##*:}" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  local response_file
  response_file="$(mktemp)"

  wait_for_http_200 "$frontend_url/" "$response_file" "$frontend_pid" "$frontend_log"
  assert_file_contains "$response_file" 'ATrade Terminal Shell'
  assert_file_contains "$response_file" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$response_file" 'data-testid="terminal-command-input"'
  assert_file_contains "$response_file" 'Orders are disabled by the paper-only safety contract.'
  rm -f "$response_file"
}

assert_apphost_manifest_preserves_frontend_resource() {
  manifest_path="$(mktemp "${TMPDIR:-/tmp}/atrade-apphost-manifest.XXXXXX.json")"
  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
  assert_file_contains "$manifest_path" '"api"'
  assert_file_contains "$manifest_path" '"frontend"'
  assert_file_contains "$manifest_path" '"NODE_ENV": "development"'
  assert_file_contains "$manifest_path" "\"ATRADE_FRONTEND_API_BASE_URL\": \"http://127.0.0.1:$ATRADE_API_HTTP_PORT\""
  assert_file_contains "$manifest_path" "\"NEXT_PUBLIC_ATRADE_API_BASE_URL\": \"http://127.0.0.1:$ATRADE_API_HTTP_PORT\""
  assert_file_contains "$manifest_path" "\"targetPort\": $ATRADE_APPHOST_FRONTEND_HTTP_PORT"
  assert_file_contains "$manifest_path" '"external": true'
  assert_file_contains "$manifest_path" '"PORT": "{frontend.bindings.http.targetPort}"'
}

assert_apphost_frontend_runtime_is_warning_free() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-nextjs-bootstrap-tests.sh\n' >&2
    return 1
  fi

  stop_frontend_dev_processes

  if [[ ! -f "$repo_root/package-lock.json" ]]; then
    printf '{"name":"atrade-root","lockfileVersion":3,"requires":true,"packages":{}}\n' > "$repo_root/package-lock.json"
    root_lock_created=1
  fi

  apphost_log="$(mktemp)"
  (
    cd "$repo_root"
    DCP_PRESERVE_EXECUTABLE_LOGS=true dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" >"$apphost_log" 2>&1
  ) &
  apphost_pid=$!

  local session_folder=''
  local session_folder_candidate=''
  local attempt

  for attempt in {1..120}; do
    session_folder_candidate="$(grep -oE '/[^"[:space:]]*aspire-dcp[^"[:space:]]+/kubeconfig' "$apphost_log" | tail -n 1 | sed 's#/kubeconfig$##' || true)"
    if [[ -n "$session_folder_candidate" && -d "$session_folder_candidate" ]]; then
      session_folder="$session_folder_candidate"
      break
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      printf 'AppHost exited before DCP session folder was available.\n' >&2
      cat "$apphost_log" >&2
      return 1
    fi

    sleep 0.5
  done

  if [[ -z "$session_folder" || ! -d "$session_folder" ]]; then
    printf 'failed to resolve DCP session folder for AppHost runtime verification.\n' >&2
    cat "$apphost_log" >&2
    return 1
  fi

  for attempt in {1..120}; do
    apphost_frontend_log="$(find "$session_folder" -maxdepth 1 -type f -name 'frontend-*_out_*' ! -name 'frontend-installer-*' | sort | tail -n 1)"
    if [[ -n "$apphost_frontend_log" ]]; then
      break
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      printf 'AppHost exited before the frontend runtime log was preserved.\n' >&2
      cat "$apphost_log" >&2
      return 1
    fi

    sleep 0.5
  done

  if [[ -z "$apphost_frontend_log" || ! -f "$apphost_frontend_log" ]]; then
    printf 'failed to locate the preserved AppHost frontend runtime log.\n' >&2
    find "$session_folder" -maxdepth 2 -type f | sort >&2 || true
    return 1
  fi

  local response_file
  response_file="$(mktemp)"
  wait_for_http_200 "$apphost_frontend_url/" "$response_file" "$apphost_pid" "$apphost_log"
  assert_file_contains "$response_file" 'ATrade Terminal Shell'
  assert_file_contains "$response_file" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$response_file" 'data-testid="terminal-command-input"'
  assert_file_contains "$response_file" 'Orders are disabled by the paper-only safety contract.'
  rm -f "$response_file"

  for attempt in {1..120}; do
    if grep -Eq 'Ready in|ready' "$apphost_frontend_log"; then
      break
    fi
    sleep 0.25
  done

  local next_pid=''
  for attempt in {1..40}; do
    next_pid="$(ps -eo pid=,args= | awk '/next dev --hostname 0.0.0.0/ && !/awk/ && found == 0 { print $1; found=1 }')"
    if [[ -n "$next_pid" ]]; then
      break
    fi
    sleep 0.25
  done

  if [[ -z "$next_pid" ]]; then
    printf 'expected AppHost to launch the Next.js dev process.\n' >&2
    cat "$apphost_log" >&2
    return 1
  fi

  assert_process_environment_contains "$next_pid" 'NODE_ENV=development'
  assert_process_environment_contains "$next_pid" "PORT=$ATRADE_APPHOST_FRONTEND_HTTP_PORT"
  assert_process_environment_contains "$next_pid" "PWD=$repo_root/frontend"
  assert_process_environment_contains "$next_pid" "INIT_CWD=$repo_root/frontend"
  assert_file_contains "$apphost_frontend_log" 'next dev --hostname 0.0.0.0'
  assert_file_contains "$apphost_frontend_log" "http://localhost:$ATRADE_APPHOST_FRONTEND_HTTP_PORT"
  assert_file_not_contains "$apphost_frontend_log" 'non-standard "NODE_ENV"'
  assert_file_not_contains "$apphost_frontend_log" 'inferred your workspace root'
  assert_file_not_contains "$apphost_frontend_log" 'Detected multiple lockfiles'
}

main() {
  assert_frontend_contract_files
  assert_direct_frontend_startup
  assert_apphost_manifest_preserves_frontend_resource
  assert_apphost_frontend_runtime_is_warning_free
}

main "$@"
