#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"
script_name="$(basename "${BASH_SOURCE[0]}")"

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

assert_path_exists() {
  local path="$1"

  if [[ ! -e "$path" ]]; then
    printf 'expected path to exist: %s\n' "$path" >&2
    return 1
  fi
}

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE \
    --exclude-dir=.next \
    --exclude-dir=node_modules \
    --exclude='package-lock.json' \
    --exclude="$script_name" \
    "$pattern" "$@"; then
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

assert_chart_route_uses_landing_module() {
  local chart_page="$frontend_root/app/chart/page.tsx"
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local landing="$frontend_root/components/terminal/TerminalChartLandingModule.tsx"

  assert_path_exists "$chart_page"
  assert_path_exists "$landing"
  assert_file_contains "$chart_page" 'moduleId="CHART"'
  assert_file_contains "$app" 'TerminalChartLandingModule'
  assert_file_contains "$app" '<TerminalChartLandingModule initialChartRange={chartRange} onOpenIntent={onOpenIntent} />'
  assert_file_contains "$landing" 'data-testid="terminal-chart-landing-module"'
  assert_file_contains "$landing" 'title="Stored stocks"'
  assert_file_contains "$landing" 'data-testid="stored-stocks-selector"'
  assert_file_contains "$landing" 'data-testid="stored-stock-chart-region"'
}

assert_backend_watchlist_workflow_and_default_selection() {
  local landing="$frontend_root/components/terminal/TerminalChartLandingModule.tsx"
  local watchlist_workflow="$frontend_root/lib/watchlistWorkflow.ts"

  assert_file_contains "$landing" 'useWatchlistWorkflow()'
  assert_file_contains "$landing" 'watchlist.symbols.map'
  assert_file_contains "$watchlist_workflow" 'getWatchlist()'
  assert_file_contains "$watchlist_workflow" "setWatchlistSource('backend')"
  assert_file_contains "$landing" 'return candidates[0].id;'
  assert_file_contains "$landing" 'Default chart candidate'
  assert_file_contains "$landing" 'data-testid="stored-stock-default-candidate"'
  assert_file_contains "$landing" 'data-testid="stored-stock-default-chart"'
  assert_file_contains "$landing" 'useTerminalChartWorkspaceWorkflow({'
  assert_file_contains "$landing" 'identity: candidate.identity'
  assert_file_contains "$landing" 'includeAnalysis={false}'
}

assert_exact_identity_and_canonical_handoff() {
  local landing="$frontend_root/components/terminal/TerminalChartLandingModule.tsx"
  local routes="$frontend_root/lib/terminalRoutes.ts"
  local identity="$frontend_root/lib/instrumentIdentity.ts"
  local terminal_types="$frontend_root/types/terminal.ts"

  assert_file_contains "$landing" 'providerSymbolId: symbol.providerSymbolId'
  assert_file_contains "$landing" 'ibkrConid: symbol.ibkrConid'
  assert_file_contains "$landing" 'routeIdentity: toRouteIdentity(identity)'
  assert_file_contains "$landing" "chartHref: createTerminalSymbolRoute('CHART', identity, { chartRange })"
  assert_file_contains "$landing" "analysisHref: createTerminalSymbolRoute('ANALYSIS', identity, { chartRange })"
  assert_file_contains "$landing" "backtestHref: createTerminalSymbolRoute('BACKTEST', identity, { chartRange })"
  assert_file_contains "$landing" 'data-testid="stored-stock-route-handoff"'
  assert_file_contains "$landing" 'data-chart-href={candidate.chartHref}'
  assert_file_contains "$landing" 'data-analysis-href={candidate.analysisHref}'
  assert_file_contains "$landing" 'data-backtest-href={candidate.backtestHref}'
  assert_file_not_contains "$routes" 'firstTerminalQueryValue(searchParams.ibkrConid)'
  assert_file_not_contains "$routes" 'ibkrConid,'
  assert_file_not_contains "$identity" "params.set('ibkrConid', String(identity.ibkrConid));"
  assert_file_contains "$terminal_types" 'identity?: InstrumentIdentityInput | null'
}

assert_empty_unavailable_and_cached_fallback_states() {
  local landing="$frontend_root/components/terminal/TerminalChartLandingModule.tsx"

  assert_file_contains "$landing" 'Loading stored stocks.'
  assert_file_contains "$landing" 'Cached fallback shown.'
  assert_file_contains "$landing" 'Stored stocks unavailable'
  assert_file_contains "$landing" 'No stored stocks'
  assert_file_contains "$landing" 'data-testid={unavailable ? '\''stored-stocks-unavailable-state'\'' : '\''stored-stocks-empty-state'\''}'
  assert_file_contains "$landing" "createTerminalModuleRoute('SEARCH')"
  assert_file_contains "$landing" "createTerminalModuleRoute('WATCHLIST')"
  assert_file_contains "$landing" 'Stored stocks unavailable.'
  assert_file_contains "$landing" 'empty candles stay visible'
}

assert_scroll_and_no_clipping_contract() {
  local css="$frontend_root/app/globals.css"

  assert_css_rule_contains '.terminal-chart-landing__body' 'grid-template-columns: minmax(18rem, 24rem) minmax(0, 1fr);'
  assert_css_rule_contains '.terminal-chart-landing__body' 'min-height: min(42rem, 72dvh);'
  assert_css_rule_contains '.terminal-chart-landing__selector' 'overflow: auto;'
  assert_css_rule_contains '.terminal-chart-landing__selector' 'max-height: min(42rem, 72dvh);'
  assert_css_rule_contains '.terminal-chart-landing__chart-region' 'overflow: auto;'
  assert_css_rule_contains '.terminal-chart-landing__chart-region' 'min-height: 32rem;'
  assert_file_contains "$css" '.terminal-chart-landing__body,'
  assert_file_contains "$css" '.terminal-chart-landing__chart-region,'
}

assert_no_hard_coded_demo_default_symbol() {
  assert_no_grep_matches \
    'hard-coded demo/default stock symbol in chart landing source' \
    '\b(AAPL|MSFT|GOOG|GOOGL|TSLA|NVDA|SPY|QQQ)\b' \
    "$frontend_root/app/chart" \
    "$frontend_root/components/terminal/TerminalChartLandingModule.tsx"

  assert_file_not_contains "$frontend_root/components/terminal/TerminalChartLandingModule.tsx" 'Math.random'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalChartLandingModule.tsx" 'sampleCandles'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalChartLandingModule.tsx" 'mockCandles'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalChartLandingModule.tsx" 'fakeCandles'
}

assert_provider_runtime_independent_validation() {
  local api_base_token="NEXT_PUBLIC_ATRADE_API""_BASE""_URL"
  local curl_token="cu""rl "
  local frontend_build_token="npm ""run"" build"
  local dotnet_token="dot""net "
  local ibkr_env_token="ATRADE_""IBKR"
  local ibkr_password_token="IBKR_""PASSWORD"

  assert_file_not_contains "${BASH_SOURCE[0]}" "$api_base_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$curl_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$frontend_build_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$dotnet_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$ibkr_env_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$ibkr_password_token"
}

main() {
  assert_chart_route_uses_landing_module
  assert_backend_watchlist_workflow_and_default_selection
  assert_exact_identity_and_canonical_handoff
  assert_empty_unavailable_and_cached_fallback_states
  assert_scroll_and_no_clipping_contract
  assert_no_hard_coded_demo_default_symbol
  assert_provider_runtime_independent_validation

  printf 'frontend chart watchlist default validation passed.\n'
}

main "$@"
