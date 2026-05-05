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

assert_terminal_workflows_reachable() {
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "HOME":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "SEARCH":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "WATCHLIST":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "CHART":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "ANALYSIS":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "STATUS":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "HELP":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title={searchQuery ? `Search monitor · ${searchQuery}` : "Search market monitor"} />'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalMarketMonitor onOpenIntent={onOpenIntent} title="Watchlist market monitor" />'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalChartWorkspace chart={chart} identity={identity} />'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalAnalysisWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />'
  assert_file_contains "$frontend_root/components/terminal/TerminalMarketMonitor.tsx" 'workflow.openChartIntent(row)'
  assert_file_contains "$frontend_root/components/terminal/TerminalMarketMonitor.tsx" 'workflow.openAnalysisIntent(row)'
  assert_file_contains "$frontend_root/components/terminal/TerminalMarketMonitor.tsx" 'workflow.toggleRowPin(row)'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'getTrendingSymbols()'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'useSymbolSearchWorkflow({'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'useWatchlistWorkflow()'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'toggleSearchPin(row.searchResult)'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'removePin(row.watchlistSymbol)'
  assert_file_contains "$frontend_root/components/terminal/TerminalInstrumentHeader.tsx" 'data-testid="chart-range-controls"'
  assert_file_contains "$frontend_root/components/terminal/TerminalInstrumentHeader.tsx" 'chart.view.supportedRanges.map((chartRange)'
  assert_file_contains "$frontend_root/lib/terminalChartWorkspaceWorkflow.ts" 'SignalR applies market-data updates when /hubs/market-data is reachable; if streaming is unavailable the view falls back to HTTP polling without synthetic data.'
  assert_file_contains "$frontend_root/lib/terminalAnalysisWorkflow.ts" 'getAnalysisEngines()'
  assert_file_contains "$frontend_root/lib/terminalAnalysisWorkflow.ts" 'runProviderNeutralAnalysis(createTerminalAnalysisRunRequest'
  assert_file_contains "$frontend_root/components/terminal/TerminalStatusModule.tsx" '<TerminalProviderDiagnostics />'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'const disabledModules = getDisabledTerminalModules()'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'onDisabledModule?.(module.id)'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'data-testid={`terminal-disabled-module-${unavailable.module.id.toLowerCase()}`}'
}

assert_resizable_layout_persistence_and_responsive_fallback() {
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-testid="terminal-context-splitter"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-testid="terminal-monitor-splitter"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-testid="terminal-layout-reset"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'window.addEventListener("pointermove", handlePointerMove, { passive: false })'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'setPointerCapture?.(event.pointerId)'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'readTerminalLayoutPreferences()'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'writeTerminalLayoutPreferences(preferences)'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'resetTerminalLayoutPreferences()'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" '--terminal-primary-size'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" '--terminal-context-size'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" '--terminal-monitor-size'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'TERMINAL_LAYOUT_STORAGE_KEY = "atrade.terminal.layout.v1"'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'const MIN_CONTEXT_PERCENT = 20'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'const MAX_CONTEXT_PERCENT = 44'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'const MIN_MONITOR_PERCENT = 16'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'const MAX_MONITOR_PERCENT = 42'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'typeof window === "undefined"'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'window.localStorage.setItem(probeKey, "1")'
  assert_file_contains "$frontend_root/lib/terminalLayoutPersistence.ts" 'Math.min(Math.max(value, min), max)'
  assert_file_contains "$frontend_root/app/globals.css" '@media (max-width: 1100px)'
  assert_file_contains "$frontend_root/app/globals.css" 'grid-template-areas:'
  assert_file_contains "$frontend_root/app/globals.css" 'grid-template-columns: 1fr;'
  assert_file_contains "$frontend_root/app/globals.css" 'height: auto;'
  assert_file_contains "$frontend_root/app/globals.css" '.terminal-workspace-layout__splitter {'
  assert_file_contains "$frontend_root/app/globals.css" 'display: none;'
  assert_file_contains "$frontend_root/app/globals.css" '@media (max-width: 720px)'
}

assert_disabled_future_modules_visible_and_honest() {
  for disabled in NEWS PORTFOLIO RESEARCH SCREENER ECON AI NODE ORDERS; do
    assert_file_contains "$frontend_root/types/terminal.ts" "\"$disabled\""
    assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" "id: \"$disabled\""
    assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'availability: "disabled"'
  done

  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'aria-label="Future disabled modules"'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'aria-disabled="true"'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'tabIndex={-1}'
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'title={`${unavailable.title}: ${unavailable.message}`}'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'Visible-disabled module'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'Not available'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'unavailable.details.map((detail)'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'no fake data, no demo provider responses, and no order-entry controls'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'Type HELP for enabled commands.'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'The terminal does not show scraped headlines, stale fixture stories, or invented market narratives.'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'The terminal does not synthesize holdings, balances, or account identifiers.'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'The terminal does not display fake factor tables or prebuilt demo screens.'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'The terminal does not display demo assistant output or generated market commentary.'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'This terminal shell does not provide order tickets, buy/sell buttons, staged submissions, previews, or confirmations.'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'Place order'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'Submit order'
  assert_file_not_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'type="submit"'
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
  assert_terminal_workflows_reachable
  assert_disabled_future_modules_visible_and_honest
  assert_resizable_layout_persistence_and_responsive_fallback
  assert_terminal_markers_present

  printf 'ATrade Terminal cutover validation passed.\n'
}

main "$@"
