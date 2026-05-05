#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"

frontend_pid=''
frontend_log=''
root_response=''
help_response=''
status_response=''
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
matches = list(re.finditer(pattern, css))
if not matches:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if not any(needle in match.group('body') for match in matches):
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

  for temp_file in "$frontend_log" "$root_response" "$help_response" "$status_response" "$chart_response"; do
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

assert_removed_top_chrome_source_contract() {
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local css="$frontend_root/app/globals.css"

  assert_no_grep_matches \
    'removed top app header, brand, or global safety-strip source snippet in active frontend source' \
    'atrade-terminal-app__header|atrade-terminal-app__brand|terminal-safety-strip|ATrade Workspace|Paper Trading Workspace' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types"

  assert_file_contains "$app" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$app" '<p className="sr-only" aria-live="polite" role="status">'
  assert_file_contains "$app" '<TerminalModuleRail'
  assert_file_contains "$app" '<TerminalWorkspaceLayout activeModuleId={activeModuleId}>'
  assert_file_contains "$app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />'
  assert_file_contains "$app" '<TerminalStatusModule />'
  assert_file_contains "$app" '<TerminalHelpModule />'
  assert_file_contains "$app" '<TerminalDisabledModule moduleId={disabledModuleId} />'
  assert_file_contains "$app" 'Orders are disabled by the paper-only safety contract.'

  assert_file_not_contains "$css" '.atrade-terminal-app__header'
  assert_file_not_contains "$css" '.atrade-terminal-app__brand'
  assert_file_not_contains "$css" '.terminal-safety-strip'
  assert_file_not_contains "$css" 'grid-template-rows: auto auto minmax(0, 1fr);'
  assert_css_rule_contains '.atrade-terminal-app' 'grid-template-rows: minmax(0, 1fr);'
  assert_css_rule_contains '.atrade-terminal-app' 'height: 100dvh;'
  assert_css_rule_contains '.atrade-terminal-app' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__workspace' 'overflow: hidden;'
}

assert_preserved_boundary_surfaces_source_contract() {
  local help="$frontend_root/components/terminal/TerminalHelpModule.tsx"
  local status="$frontend_root/components/terminal/TerminalStatusModule.tsx"
  local diagnostics="$frontend_root/components/terminal/TerminalProviderDiagnostics.tsx"
  local disabled="$frontend_root/components/terminal/TerminalDisabledModule.tsx"
  local monitor="$frontend_root/components/terminal/TerminalMarketMonitor.tsx"

  assert_file_contains "$help" 'All browser-visible data flows through ATrade.Api'
  assert_file_contains "$help" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$status" 'Browser routes through ATrade.Api only.'
  assert_file_contains "$diagnostics" 'workspace renders no order-entry controls and does not call broker order routes.'
  assert_file_contains "$disabled" 'no fake data, no demo provider responses, and no order-entry controls'
  assert_file_contains "$monitor" 'Backend-owned exact Postgres pins through ATrade.Api.'
  assert_file_contains "$monitor" 'Debounced, minimum-query, capped stock search through ATrade.Api.'
}

assert_compact_filter_source_contract() {
  local filters="$frontend_root/components/terminal/MarketMonitorFilters.tsx"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$filters" 'data-testid="market-monitor-filters"'
  assert_file_contains "$filters" 'aria-label="Market monitor filters"'
  assert_file_contains "$filters" 'Filter rows'
  assert_file_contains "$filters" 'aria-label="Clear all market monitor filters"'
  assert_file_contains "$filters" 'disabled={selectedCount === 0}'
  assert_file_contains "$filters" '<fieldset className="market-monitor-filters__group"'
  assert_file_contains "$filters" '<legend>{MarketMonitorFilterLabels[key]}</legend>'
  assert_file_contains "$filters" 'aria-pressed={active}'
  assert_file_contains "$filters" 'data-monitor-filter-key={key}'
  assert_file_contains "$filters" 'data-monitor-filter-value={option.value}'
  assert_file_contains "$filters" 'aria-label={`${option.count} rows`}'
  assert_file_not_contains "$filters" 'Refine by source, pin state, provider, market, currency, or asset class without fetching more than the capped search payload.'

  assert_css_rule_contains '.market-monitor-filters' 'gap: 0.4rem;'
  assert_css_rule_contains '.market-monitor-filters' 'padding: 0.5rem 0.6rem;'
  assert_css_rule_contains '.market-monitor-filters__header' 'align-items: center;'
  assert_css_rule_contains '.market-monitor-filters__groups' 'display: flex;'
  assert_css_rule_contains '.market-monitor-filters__groups' 'flex-wrap: wrap;'
  assert_css_rule_contains '.market-monitor-filters__group' 'display: flex;'
  assert_css_rule_contains '.market-monitor-filters__group legend' 'font-size: 0.62rem;'
  assert_css_rule_contains '.market-monitor-filters__chips' 'gap: 0.25rem;'
  assert_css_rule_contains '.market-monitor-filters__chip' 'min-height: 1.65rem;'
}

start_frontend_and_assert_markup() {
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
  help_response="$(mktemp)"
  status_response="$(mktemp)"
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
  assert_file_contains "$root_response" 'data-testid="market-monitor-filters"'
  assert_file_contains "$root_response" 'aria-label="Market monitor filters"'
  assert_file_contains "$root_response" 'Filter rows'
  assert_file_contains "$root_response" 'Clear all'
  assert_file_contains "$root_response" 'No live orders'
  assert_file_contains "$root_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$root_response" 'Backend-owned exact Postgres pins through ATrade.Api.'
  assert_file_not_contains "$root_response" 'atrade-terminal-app__header'
  assert_file_not_contains "$root_response" 'atrade-terminal-app__brand'
  assert_file_not_contains "$root_response" 'terminal-safety-strip'
  assert_file_not_contains "$root_response" 'ATrade Workspace'
  assert_file_not_contains "$root_response" 'Paper Trading Workspace'
  assert_file_not_contains "$root_response" 'Refine by source, pin state, provider, market, currency, or asset class without fetching more than the capped search payload.'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'data-testid="terminal-chart-workspace"'
  assert_file_not_contains "$chart_response" 'terminal-safety-strip'
  assert_file_not_contains "$chart_response" 'Paper Trading Workspace'

  wait_for_http_200 "$frontend_url/symbols/AAPL?module=HELP" "$help_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$help_response" 'data-testid="terminal-help-module"'
  assert_file_contains "$help_response" 'All browser-visible data flows through ATrade.Api'
  assert_file_contains "$help_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$help_response" 'terminal-safety-strip'

  wait_for_http_200 "$frontend_url/symbols/AAPL?module=STATUS" "$status_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$status_response" 'data-testid="terminal-status-module"'
  assert_file_contains "$status_response" 'data-testid="terminal-provider-diagnostics"'
  assert_file_contains "$status_response" 'Browser routes through ATrade.Api only.'
  assert_file_contains "$status_response" 'Order placement capability'
  assert_file_not_contains "$status_response" 'terminal-safety-strip'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-top-chrome-filter-density-tests.sh\n' >&2
    return 1
  fi

  assert_removed_top_chrome_source_contract
  assert_preserved_boundary_surfaces_source_contract
  assert_compact_filter_source_contract
  start_frontend_and_assert_markup

  printf 'Top chrome removal and compact filter validation passed.\n'
}

main "$@"
