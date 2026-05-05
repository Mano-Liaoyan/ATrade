#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"

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
    printf 'expected obsolete path to be removed: %s\n' "$path" >&2
    return 1
  fi
}

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='frontend-terminal-cutover-tests.sh' "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_active_routes_use_terminal_app() {
  local home_page="$frontend_root/app/page.tsx"
  local symbol_page="$frontend_root/app/symbols/[symbol]/page.tsx"

  assert_file_contains "$home_page" "import { ATradeTerminalApp } from '@/components/terminal/ATradeTerminalApp';"
  assert_file_contains "$home_page" '<ATradeTerminalApp initialModuleId="HOME" />'
  assert_file_contains "$symbol_page" "import { ATradeTerminalApp } from '@/components/terminal/ATradeTerminalApp';"
  assert_file_contains "$symbol_page" 'initialChartRange={initialChartRange}'
  assert_file_contains "$symbol_page" 'initialIdentity={identity}'
  assert_file_contains "$symbol_page" 'initialModuleId={initialModuleId}'
  assert_file_contains "$symbol_page" 'initialSymbol={normalizedSymbol}'

  assert_no_grep_matches \
    'old route wrapper import or JSX usage in active app routes' \
    "<(TradingWorkspace|SymbolChartView)([[:space:]>])|from [\"'][^\"']*/(TradingWorkspace|SymbolChartView)[\"']" \
    "$frontend_root/app"
}

assert_obsolete_renderers_removed() {
  local obsolete_components=(
    "$frontend_root/components/TradingWorkspace.tsx"
    "$frontend_root/components/SymbolChartView.tsx"
    "$frontend_root/components/SymbolSearch.tsx"
    "$frontend_root/components/TrendingList.tsx"
    "$frontend_root/components/Watchlist.tsx"
    "$frontend_root/components/MarketLogo.tsx"
    "$frontend_root/components/TimeframeSelector.tsx"
    "$frontend_root/components/IndicatorPanel.tsx"
    "$frontend_root/components/AnalysisPanel.tsx"
    "$frontend_root/components/BrokerPaperStatus.tsx"
  )

  for obsolete in "${obsolete_components[@]}"; do
    assert_path_missing "$obsolete"
  done

  assert_no_grep_matches \
    'obsolete rendering component import or JSX usage in active frontend source' \
    "<(TradingWorkspace|SymbolChartView|SymbolSearch|TrendingList|Watchlist|MarketLogo|TimeframeSelector|IndicatorPanel|AnalysisPanel|BrokerPaperStatus)([[:space:]>])|from [\"'][^\"']*/(TradingWorkspace|SymbolChartView|SymbolSearch|TrendingList|Watchlist|MarketLogo|TimeframeSelector|IndicatorPanel|AnalysisPanel|BrokerPaperStatus)[\"']" \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib"
}

assert_old_copy_and_shell_css_removed() {
  assert_no_grep_matches \
    'obsolete homepage/back-link copy in active frontend source or apphost tests' \
    'Next\.js Bootstrap Slice|ATrade Frontend Home|Back to trading workspace|← Back to trading workspace' \
    "$frontend_root" "$repo_root/tests/apphost"

  assert_no_grep_matches \
    'old shell/list/chart CSS marker in active frontend stylesheet' \
    'workspace-shell|terminal-workspace-shell|symbol-search-|market-logo|pin-button|watchlist-panel|broker-status-panel|timeframe-selector|timeframe-button|indicator-panel|analysis-panel' \
    "$frontend_root/app/globals.css"
}

assert_terminal_markers_present() {
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-home-module"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-search-module"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-watchlist-module"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-chart-module"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'data-testid="terminal-analysis-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalCommandInput.tsx" 'data-testid="terminal-command-input"'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'data-testid="terminal-module-rail"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-testid="terminal-layout-reset"'
  assert_file_contains "$frontend_root/components/terminal/TerminalMarketMonitor.tsx" 'data-testid="terminal-market-monitor"'
  assert_file_contains "$frontend_root/components/terminal/TerminalChartWorkspace.tsx" 'data-testid="terminal-chart-workspace"'
  assert_file_contains "$frontend_root/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="terminal-analysis-workspace"'
  assert_file_contains "$frontend_root/components/terminal/TerminalProviderDiagnostics.tsx" 'data-testid="terminal-provider-diagnostics"'
  assert_file_contains "$frontend_root/components/terminal/TerminalStatusModule.tsx" 'data-testid="terminal-status-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalHelpModule.tsx" 'data-testid="terminal-help-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalStatusStrip.tsx" 'data-testid="terminal-status-strip"'
}

main() {
  assert_active_routes_use_terminal_app
  assert_obsolete_renderers_removed
  assert_old_copy_and_shell_css_removed
  assert_terminal_markers_present

  printf 'ATrade Terminal cutover validation passed.\n'
}

main "$@"
