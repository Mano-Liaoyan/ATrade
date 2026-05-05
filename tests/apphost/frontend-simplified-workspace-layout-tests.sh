#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"

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

  if [[ -f "$file_path" ]] && grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_path_missing() {
  local path="$1"

  if [[ -e "$path" ]]; then
    printf 'expected simplified workspace to remove path: %s\n' "$path" >&2
    return 1
  fi
}

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_css_rule_contains() {
  local selector="$1"
  local needle="$2"
  local css_file="$frontend_root/app/globals.css"

  python3 - "$css_file" "$selector" "$needle" <<'PY'
import re
import sys
from pathlib import Path

css_path = Path(sys.argv[1])
selector = sys.argv[2]
needle = sys.argv[3]
css = css_path.read_text(encoding='utf-8')
pattern = re.escape(selector) + r"\s*\{(?P<body>[^{}]*)\}"
match = re.search(pattern, css)
if not match:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if needle not in match.group('body'):
    print(f"expected CSS selector {selector!r} to contain {needle!r}", file=sys.stderr)
    sys.exit(1)
PY
}

stop_frontend_lock_owner() {
  local lock_file="$frontend_root/.next/dev/lock"
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

assert_simplified_workspace_source_contract() {
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local layout="$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx"
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"
  local help="$frontend_root/components/terminal/TerminalHelpModule.tsx"
  local status="$frontend_root/components/terminal/TerminalStatusModule.tsx"
  local diagnostics="$frontend_root/components/terminal/TerminalProviderDiagnostics.tsx"
  local disabled="$frontend_root/components/terminal/TerminalDisabledModule.tsx"
  local css="$frontend_root/app/globals.css"
  local terminal_types="$frontend_root/types/terminal.ts"

  assert_file_contains "$app" '<TerminalModuleRail'
  assert_file_contains "$app" '<TerminalWorkspaceLayout activeModuleId={activeModuleId}>'
  assert_file_contains "$app" '<p className="sr-only" aria-live="polite" role="status">'
  assert_file_not_contains "$app" 'data-testid="terminal-safety-strip"'
  assert_file_not_contains "$app" 'Paper Trading Workspace'
  assert_file_contains "$app" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />'
  assert_file_contains "$app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title={searchQuery ? `Search monitor · ${searchQuery}` : "Search market monitor"} />'
  assert_file_contains "$app" '<TerminalMarketMonitor onOpenIntent={onOpenIntent} title="Watchlist market monitor" />'
  assert_file_contains "$app" '<TerminalChartWorkspace chart={chart} identity={identity} />'
  assert_file_contains "$app" '<TerminalAnalysisWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />'
  assert_file_contains "$app" '<TerminalStatusModule />'
  assert_file_contains "$app" '<TerminalHelpModule />'
  assert_file_contains "$app" '<TerminalDisabledModule moduleId={disabledModuleId} />'
  assert_file_contains "$rail" 'data-testid="terminal-module-rail"'
  assert_file_contains "$rail" 'getDisabledTerminalModules'
  assert_file_contains "$help" 'All browser-visible data flows through ATrade.Api'
  assert_file_contains "$status" '<TerminalProviderDiagnostics />'
  assert_file_contains "$diagnostics" 'data-testid="terminal-provider-diagnostics"'
  assert_file_contains "$disabled" 'data-testid={`terminal-disabled-module-${unavailable.module.id.toLowerCase()}`}'
  assert_file_contains "$disabled" 'no fake data, no demo provider responses, and no order-entry controls'

  assert_file_contains "$layout" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$layout" 'data-layout-region="primary"'
  assert_file_not_contains "$layout" 'data-layout-region="context"'
  assert_file_not_contains "$layout" 'data-layout-region="monitor"'
  assert_file_not_contains "$layout" 'data-testid="terminal-context-splitter"'
  assert_file_not_contains "$layout" 'data-testid="terminal-monitor-splitter"'
  assert_file_not_contains "$layout" 'data-testid="terminal-layout-reset"'
  assert_file_not_contains "$layout" 'PointerEvent'
  assert_file_not_contains "$layout" 'readTerminalLayoutPreferences'
  assert_file_not_contains "$layout" 'writeTerminalLayoutPreferences'
  assert_file_not_contains "$layout" 'resetTerminalLayoutPreferences'
  assert_file_not_contains "$layout" '--terminal-context-size'
  assert_file_not_contains "$layout" '--terminal-monitor-size'

  assert_path_missing "$frontend_root/components/terminal/TerminalStatusStrip.tsx"
  assert_path_missing "$frontend_root/lib/terminalLayoutPersistence.ts"
  assert_file_not_contains "$terminal_types" 'TerminalLayoutRegion'
  assert_file_not_contains "$terminal_types" 'TerminalLayoutSizes'
  assert_file_not_contains "$terminal_types" 'TerminalLayoutPreferences'

  assert_no_grep_matches \
    'removed context panel, monitor strip, footer strip, splitter, reset, or layout persistence token in active frontend source' \
    'TerminalContextSummary|TerminalMonitorPanel|TerminalStatusStrip|terminal-workspace-layout__context|terminal-context-summary|terminal-workspace-layout__monitor|terminal-monitor-panel|terminal-status-strip|terminal-context-splitter|terminal-monitor-splitter|terminal-layout-reset|terminal-workspace-layout__splitter|terminal-workspace-layout__reset|terminalLayoutPersistence|TerminalLayoutPreferences|--terminal-context-size|--terminal-monitor-size|--terminal-primary-size' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types"

  assert_file_contains "$css" '.atrade-terminal-app'
  assert_file_contains "$css" '.terminal-workspace-layout__primary'
  assert_file_not_contains "$css" 'terminal-workspace-layout__context'
  assert_file_not_contains "$css" 'terminal-workspace-layout__monitor'
  assert_file_not_contains "$css" 'terminal-workspace-layout__splitter'
  assert_file_not_contains "$css" 'terminal-workspace-layout__reset'
  assert_file_not_contains "$css" 'terminal-status-strip'
  assert_file_not_contains "$css" 'terminal-context-summary'
  assert_file_not_contains "$css" 'terminal-monitor-panel'
  assert_file_not_contains "$css" '--terminal-grid'
  assert_file_not_contains "$css" '--terminal-grid-line'
  assert_file_not_contains "$css" 'background-size: 40px 40px'
  assert_file_not_contains "$css" 'linear-gradient(90deg'
  assert_file_not_contains "$css" 'width: min(100%, 1680px)'
  assert_file_not_contains "$css" 'margin: 0 auto'
  assert_file_not_contains "$css" 'overflow-x: hidden'

  assert_css_rule_contains 'html' 'overflow: hidden;'
  assert_css_rule_contains 'body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app' 'width: 100%;'
  assert_css_rule_contains '.atrade-terminal-app' 'height: 100dvh;'
  assert_css_rule_contains '.atrade-terminal-app' 'margin: 0;'
  assert_css_rule_contains '.atrade-terminal-app' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__workspace' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-workspace-layout' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-workspace-layout__primary' 'overflow: auto;'
  assert_css_rule_contains '.terminal-chart-workspace' 'min-height: min(44rem, calc(100dvh - 4rem));'
  assert_css_rule_contains '.terminal-chart-workspace__market-grid' 'min-height: min(42rem, 72dvh);'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'grid-template-rows: auto minmax(26rem, 1fr) auto;'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'overflow: auto;'
  assert_css_rule_contains '.chart-shell' 'min-height: 30rem;'
  assert_css_rule_contains '.chart-container' 'height: clamp(420px, 56dvh, 680px);'
  assert_css_rule_contains '.chart-container' 'min-width: 1px;'
}

start_frontend_and_assert_simplified_markup() {
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
    cd "$frontend_root"
    PORT="$port" NEXT_PUBLIC_ATRADE_API_BASE_URL="http://127.0.0.1:1" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  wait_for_http_200 "$frontend_url/" "$root_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$root_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$root_response" 'data-testid="terminal-module-rail"'
  assert_file_contains "$root_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$root_response" 'data-layout-region="primary"'
  assert_file_contains "$root_response" 'data-testid="terminal-market-monitor"'
  assert_file_contains "$root_response" 'Paper workspace home'
  assert_file_not_contains "$root_response" 'terminal-safety-strip'
  assert_file_not_contains "$root_response" 'Paper Trading Workspace'
  assert_file_contains "$root_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$root_response" 'terminal-workspace-layout__context'
  assert_file_not_contains "$root_response" 'terminal-context-summary'
  assert_file_not_contains "$root_response" 'terminal-workspace-layout__monitor'
  assert_file_not_contains "$root_response" 'terminal-monitor-panel'
  assert_file_not_contains "$root_response" 'terminal-status-strip'
  assert_file_not_contains "$root_response" 'terminal-context-splitter'
  assert_file_not_contains "$root_response" 'terminal-monitor-splitter'
  assert_file_not_contains "$root_response" 'terminal-layout-reset'
  assert_file_not_contains "$root_response" 'Reset layout'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$chart_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$chart_response" 'data-layout-region="primary"'
  assert_file_contains "$chart_response" 'data-testid="terminal-chart-workspace"'
  assert_file_contains "$chart_response" 'Provider-neutral analysis entry point'
  assert_file_not_contains "$chart_response" 'terminal-safety-strip'
  assert_file_not_contains "$chart_response" 'Paper Trading Workspace'
  assert_file_contains "$chart_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$chart_response" 'terminal-workspace-layout__context'
  assert_file_not_contains "$chart_response" 'terminal-context-summary'
  assert_file_not_contains "$chart_response" 'terminal-workspace-layout__monitor'
  assert_file_not_contains "$chart_response" 'terminal-monitor-panel'
  assert_file_not_contains "$chart_response" 'terminal-status-strip'
  assert_file_not_contains "$chart_response" 'terminal-context-splitter'
  assert_file_not_contains "$chart_response" 'terminal-monitor-splitter'
  assert_file_not_contains "$chart_response" 'terminal-layout-reset'
  assert_file_not_contains "$chart_response" 'Reset layout'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-simplified-workspace-layout-tests.sh\n' >&2
    return 1
  fi

  assert_simplified_workspace_source_contract
  start_frontend_and_assert_simplified_markup

  printf 'Simplified workspace layout validation passed.\n'
}

main "$@"
