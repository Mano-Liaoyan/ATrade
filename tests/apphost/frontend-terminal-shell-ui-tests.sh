#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

frontend_pid=''
frontend_log=''
root_response=''
chart_response=''
frontend_url="http://127.0.0.1:${ATRADE_FRONTEND_DIRECT_HTTP_PORT:-0}"

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

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_file_absent() {
  local file_path="$1"

  if [[ -e "$file_path" ]]; then
    printf 'expected retired shell primitive to be absent: %s\n' "$file_path" >&2
    return 1
  fi
}

stop_frontend_lock_owner() {
  local lock_file="$repo_root/frontend/.next/dev/lock"
  local locked_pid=''

  if [[ ! -f "$lock_file" ]]; then
    return 0
  fi

  locked_pid="$(python3 - "$lock_file" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding='utf-8') as handle:
        value = json.load(handle).get('pid', '')
    print(value if isinstance(value, int) else '')
except Exception:
    print('')
PY
)"

  if [[ "$locked_pid" =~ ^[0-9]+$ ]] && kill -0 "$locked_pid" 2>/dev/null; then
    kill "$locked_pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$locked_pid" 2>/dev/null; then
      kill -9 "$locked_pid" 2>/dev/null || true
    fi
  fi

  rm -f "$lock_file" 2>/dev/null || true
}

cleanup() {
  if [[ -n "$frontend_pid" ]]; then
    pkill -TERM -P "$frontend_pid" 2>/dev/null || true
    if kill -0 "$frontend_pid" 2>/dev/null; then
      kill "$frontend_pid" 2>/dev/null || true
      wait "$frontend_pid" 2>/dev/null || true
    fi
    pkill -KILL -P "$frontend_pid" 2>/dev/null || true
  fi

  stop_frontend_lock_owner

  for temp_file in "$frontend_log" "$root_response" "$chart_response"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
}

trap cleanup EXIT

wait_for_http_200() {
  local url="$1"
  local output_file="$2"
  local pid_to_check="$3"
  local log_file="$4"
  local code=''

  for _ in {1..80}; do
    code="$(curl --silent --output "$output_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$pid_to_check" 2>/dev/null; then
      printf 'process exited before %s returned HTTP 200.\n' "$url" >&2
      cat "$log_file" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'expected %s to return HTTP 200, got %s\n' "$url" "$code" >&2
  cat "$log_file" >&2
  return 1
}

assert_terminal_shell_source_contract() {
  local app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local command_input="$repo_root/frontend/components/terminal/TerminalCommandInput.tsx"
  local rail="$repo_root/frontend/components/terminal/TerminalModuleRail.tsx"
  local layout="$repo_root/frontend/components/terminal/TerminalWorkspaceLayout.tsx"
  local status_strip="$repo_root/frontend/components/terminal/TerminalStatusStrip.tsx"
  local help_module="$repo_root/frontend/components/terminal/TerminalHelpModule.tsx"
  local status_module="$repo_root/frontend/components/terminal/TerminalStatusModule.tsx"
  local disabled_module="$repo_root/frontend/components/terminal/TerminalDisabledModule.tsx"
  local css="$repo_root/frontend/app/globals.css"
  local package_json="$repo_root/frontend/package.json"

  assert_file_contains "$app" 'export function ATradeTerminalApp'
  assert_file_contains "$app" '<TerminalCommandInput'
  assert_file_contains "$app" '<TerminalModuleRail'
  assert_file_contains "$app" '<TerminalWorkspaceLayout'
  assert_file_contains "$app" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$app" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$app" 'Paper-only workspace'
  assert_file_contains "$app" 'exact instrument identity'
  assert_file_contains "$app" 'Orders are disabled by the paper-only safety contract.'

  assert_file_contains "$command_input" 'parseTerminalCommand(commandText)'
  assert_file_contains "$command_input" 'data-testid="terminal-command-input"'
  assert_file_contains "$command_input" 'Deterministic local commands only'
  assert_file_contains "$rail" 'data-testid="terminal-module-rail"'
  assert_file_contains "$rail" 'getEnabledTerminalModules'
  assert_file_contains "$rail" 'getDisabledTerminalModules'
  assert_file_contains "$layout" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$layout" 'data-testid="terminal-context-splitter"'
  assert_file_contains "$layout" 'data-testid="terminal-monitor-splitter"'
  assert_file_contains "$layout" 'readTerminalLayoutPreferences'
  assert_file_contains "$layout" 'writeTerminalLayoutPreferences'
  assert_file_contains "$status_strip" 'data-testid="terminal-status-strip"'
  assert_file_contains "$help_module" 'data-testid="terminal-help-module"'
  assert_file_contains "$status_module" 'data-testid="terminal-status-module"'
  assert_file_contains "$disabled_module" 'data-testid={`terminal-disabled-module-${unavailable.module.id.toLowerCase()}`}'

  assert_file_absent "$repo_root/frontend/components/TerminalWorkspaceShell.tsx"
  assert_file_absent "$repo_root/frontend/components/WorkspaceCommandBar.tsx"
  assert_file_absent "$repo_root/frontend/components/WorkspaceNavigation.tsx"
  assert_file_absent "$repo_root/frontend/components/WorkspaceContextPanel.tsx"

  assert_file_contains "$css" '.atrade-terminal-app'
  assert_file_contains "$css" '.terminal-command-input'
  assert_file_contains "$css" '.terminal-module-rail'
  assert_file_contains "$css" '.terminal-workspace-layout__splitter'
  assert_file_contains "$css" '.terminal-status-strip'
  assert_file_contains "$css" ':focus-visible'
  assert_file_contains "$css" '@media (max-width: 1100px)'
  assert_file_contains "$css" '@media (max-width: 720px)'

  assert_file_not_contains "$package_json" '@mui/'
  assert_file_not_contains "$package_json" 'antd'
  assert_file_not_contains "$package_json" 'chakra'

  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E 'Bloomberg|BLOOMBERG|BLP|bbg-terminal|bloomberg-terminal' "$repo_root/frontend"; then
    printf 'frontend terminal shell must not include Bloomberg/proprietary terminal assets or trademarks.\n' >&2
    return 1
  fi
}

start_frontend_and_assert_shell_markers() {
  local port
  port="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
  stop_frontend_lock_owner

  frontend_url="http://127.0.0.1:${port}"
  frontend_log="$(mktemp)"
  root_response="$(mktemp)"
  chart_response="$(mktemp)"

  (
    cd "$repo_root/frontend"
    PORT="$port" NEXT_PUBLIC_ATRADE_API_BASE_URL="http://127.0.0.1:1" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  wait_for_http_200 "$frontend_url/" "$root_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$root_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$root_response" 'data-testid="terminal-command-input"'
  assert_file_contains "$root_response" 'data-testid="terminal-module-rail"'
  assert_file_contains "$root_response" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$root_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$root_response" 'data-testid="terminal-status-strip"'
  assert_file_contains "$root_response" 'ATrade Terminal Shell'
  assert_file_contains "$root_response" 'Paper-only workspace'
  assert_file_contains "$root_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$root_response" 'ATrade Frontend Home'
  assert_file_not_contains "$root_response" 'Next.js Bootstrap Slice'
  assert_file_not_contains "$root_response" 'Bloomberg'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$chart_response" 'data-testid="terminal-command-input"'
  assert_file_contains "$chart_response" 'data-testid="terminal-module-rail"'
  assert_file_contains "$chart_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$chart_response" 'data-testid="terminal-chart-module"'
  assert_file_contains "$chart_response" 'AAPL chart workspace'
  assert_file_contains "$chart_response" 'Chart range lookback controls'
  assert_file_contains "$chart_response" 'Provider-neutral analysis entry point'
  assert_file_contains "$chart_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$chart_response" '← Back to trading workspace'
  assert_file_not_contains "$chart_response" 'Bloomberg'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-terminal-shell-ui-tests.sh\n' >&2
    return 1
  fi

  assert_terminal_shell_source_contract
  start_frontend_and_assert_shell_markers
}

main "$@"
