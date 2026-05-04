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

cleanup() {
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

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
  local shell="$repo_root/frontend/components/TerminalWorkspaceShell.tsx"
  local command_bar="$repo_root/frontend/components/WorkspaceCommandBar.tsx"
  local navigation="$repo_root/frontend/components/WorkspaceNavigation.tsx"
  local context_panel="$repo_root/frontend/components/WorkspaceContextPanel.tsx"
  local css="$repo_root/frontend/app/globals.css"
  local package_json="$repo_root/frontend/package.json"

  assert_file_contains "$shell" 'export function TerminalWorkspaceShell'
  assert_file_contains "$shell" '<WorkspaceCommandBar'
  assert_file_contains "$shell" '<WorkspaceNavigation'
  assert_file_contains "$shell" '<main className="terminal-workspace-shell__main"'
  assert_file_contains "$shell" '<aside className="terminal-workspace-shell__context"'
  assert_file_contains "$shell" 'data-testid="terminal-workspace-shell"'
  assert_file_contains "$shell" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$shell" 'Paper-only workspace'
  assert_file_contains "$shell" 'exact instrument identity'
  assert_file_contains "$shell" 'No live broker orders'
  assert_file_contains "$shell" 'no fake market data'
  assert_file_not_contains "$shell" 'Place order'
  assert_file_not_contains "$shell" 'Submit order'
  assert_file_not_contains "$shell" 'mock market data'

  assert_file_contains "$command_bar" 'export function WorkspaceCommandBar'
  assert_file_contains "$command_bar" '<header className="terminal-command-bar"'
  assert_file_contains "$command_bar" 'aria-label="Workspace command controls"'
  assert_file_contains "$command_bar" 'href={command.href}'

  assert_file_contains "$navigation" 'export function WorkspaceNavigation'
  assert_file_contains "$navigation" '<nav className="terminal-navigation"'
  assert_file_contains "$navigation" 'data-testid="workspace-navigation"'
  assert_file_contains "$navigation" 'href={item.href}'
  assert_file_contains "$navigation" 'terminal-navigation__link'

  assert_file_contains "$context_panel" 'export function WorkspaceContextPanel'
  assert_file_contains "$context_panel" 'data-testid="workspace-context-panel"'
  assert_file_contains "$context_panel" 'Workspace context metrics'
  assert_file_contains "$context_panel" 'Workspace context cards'

  assert_file_contains "$css" '.terminal-workspace-shell'
  assert_file_contains "$css" '.terminal-command-bar'
  assert_file_contains "$css" '.terminal-navigation__link'
  assert_file_contains "$css" '.terminal-context-panel'
  assert_file_contains "$css" '.terminal-safety-strip'
  assert_file_contains "$css" ':focus-visible'
  assert_file_contains "$css" '@media (max-width: 1100px)'
  assert_file_contains "$css" '@media (max-width: 720px)'

  assert_file_not_contains "$package_json" '@mui/'
  assert_file_not_contains "$package_json" 'antd'
  assert_file_not_contains "$package_json" 'chakra'
  assert_file_not_contains "$package_json" 'radix-ui'

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
  assert_file_contains "$root_response" 'data-testid="terminal-workspace-shell"'
  assert_file_contains "$root_response" 'data-testid="workspace-command-bar"'
  assert_file_contains "$root_response" 'data-testid="workspace-navigation"'
  assert_file_contains "$root_response" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$root_response" 'href="#workspace-search"'
  assert_file_contains "$root_response" 'href="#workspace-trending"'
  assert_file_contains "$root_response" 'href="#workspace-watchlist"'
  assert_file_contains "$root_response" 'Paper-only workspace'
  assert_file_contains "$root_response" 'exact instrument identity'
  assert_file_contains "$root_response" 'No live broker orders'
  assert_file_not_contains "$root_response" 'Bloomberg'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'data-testid="terminal-workspace-shell"'
  assert_file_contains "$chart_response" 'data-testid="workspace-command-bar"'
  assert_file_contains "$chart_response" 'data-testid="workspace-navigation"'
  assert_file_contains "$chart_response" 'data-testid="terminal-safety-strip"'
  assert_file_contains "$chart_response" 'href="#chart-candles"'
  assert_file_contains "$chart_response" 'href="#chart-range"'
  assert_file_contains "$chart_response" 'href="#chart-analysis"'
  assert_file_contains "$chart_response" 'href="#chart-provider"'
  assert_file_contains "$chart_response" 'Chart range lookback controls'
  assert_file_contains "$chart_response" 'Analysis only'
  assert_file_contains "$chart_response" 'No live broker orders'
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
