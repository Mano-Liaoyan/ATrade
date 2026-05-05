#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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
    printf 'expected path to be removed: %s\n' "$path" >&2
    return 1
  fi
}

assert_terminal_chart_workflow_contract() {
  local symbol_workflow="$repo_root/frontend/lib/symbolChartWorkflow.ts"
  local terminal_workflow="$repo_root/frontend/lib/terminalChartWorkspaceWorkflow.ts"
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"
  local stream_client="$repo_root/frontend/lib/marketDataStream.ts"
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local terminal_workspace="$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx"
  local instrument_header="$repo_root/frontend/components/terminal/TerminalInstrumentHeader.tsx"
  local candlestick_chart="$repo_root/frontend/components/CandlestickChart.tsx"

  assert_file_contains "$symbol_workflow" 'chartRange: ChartRange'
  assert_file_contains "$symbol_workflow" 'getCandles(normalizedSymbol, chartRange, chartIdentity)'
  assert_file_contains "$symbol_workflow" 'getIndicators(normalizedSymbol, chartRange, chartIdentity)'
  assert_file_contains "$symbol_workflow" 'connectMarketDataStream'
  assert_file_contains "$symbol_workflow" 'fallbackTimer = window.setInterval(() => void refreshChartData(false)'
  assert_file_contains "$symbol_workflow" 'applyMarketDataUpdate(current, update)'

  assert_file_contains "$terminal_workflow" 'useSymbolChartWorkflow(options)'
  assert_file_contains "$terminal_workflow" 'SUPPORTED_CHART_RANGES'
  assert_file_contains "$terminal_workflow" 'TERMINAL_CHART_RANGE_HELP_COPY'
  assert_file_contains "$terminal_workflow" 'TERMINAL_CHART_HTTP_FALLBACK_COPY'
  assert_file_contains "$terminal_workflow" 'getMarketDataIdentity'
  assert_file_contains "$terminal_workflow" 'formatTerminalChartIdentitySummary'
  assert_file_contains "$terminal_workflow" 'ChartPollingFallbackMs'
  assert_file_contains "$terminal_workflow" 'hasCandleData: Boolean(chart.candles && chart.candles.candles.length > 0)'
  assert_file_contains "$terminal_workflow" 'isEmpty: !hasCandleData'

  assert_file_contains "$market_client" 'new URLSearchParams({ range: chartRange })'
  assert_file_contains "$market_client" 'appendIdentityQueryParams(params, identity)'
  assert_file_contains "$stream_client" "connection.invoke('Subscribe', options.symbol.toUpperCase(), options.chartRange)"
  assert_file_contains "$stream_client" "connection.invoke('Unsubscribe', options.symbol.toUpperCase(), options.chartRange)"

  assert_file_contains "$terminal_app" 'useTerminalChartWorkspaceWorkflow({ symbol, identity, initialChartRange })'
  assert_file_contains "$terminal_app" '<TerminalChartWorkspace chart={chart} identity={identity} />'
  assert_file_contains "$terminal_workspace" 'chart.view.fallbackCopy'
  assert_file_contains "$terminal_workspace" 'chart.view.identitySummary'
  assert_file_contains "$terminal_workspace" 'chart.view.noOrderCopy'
  assert_file_contains "$terminal_workspace" 'chart.candles && chart.view.hasCandleData'
  assert_file_contains "$terminal_workspace" '!chart.candles || !chart.view.hasCandleData'
  assert_file_contains "$terminal_workspace" '<CandlestickChart candles={chart.candles} indicators={chart.indicators} />'
  assert_file_contains "$terminal_workspace" 'no synthetic chart data is shown'
  assert_file_contains "$candlestick_chart" 'autoSize: false'
  assert_file_contains "$candlestick_chart" 'measureChartContainer(container)'
  assert_file_contains "$candlestick_chart" 'ResizeObserver'
  assert_file_contains "$candlestick_chart" 'chart.resize(nextSize.width, nextSize.height, true)'
  assert_file_contains "$candlestick_chart" 'chart.unsubscribeCrosshairMove(handleCrosshairMove)'
  assert_file_contains "$instrument_header" 'data-testid="terminal-instrument-header"'
  assert_file_contains "$instrument_header" 'data-testid="chart-range-controls"'
  assert_file_contains "$instrument_header" 'chart.view.rangeHelpCopy'
  assert_file_contains "$instrument_header" 'chart.view.supportedRanges.map'
  assert_file_contains "$instrument_header" 'CHART_RANGE_LABELS[chartRange]'
  assert_file_not_contains "$terminal_app" 'connectMarketDataStream'
  assert_file_not_contains "$terminal_app" 'getCandles('
  assert_file_not_contains "$terminal_app" 'getIndicators('
}

assert_exact_identity_chart_and_analysis_handoff() {
  local monitor_workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local symbol_page="$repo_root/frontend/app/symbols/[symbol]/page.tsx"
  local identity="$repo_root/frontend/lib/instrumentIdentity.ts"

  assert_file_contains "$identity" 'providerSymbolId=${encodeSegment(normalized.providerSymbolId)}'
  assert_file_contains "$identity" "params.set('providerSymbolId', identity.providerSymbolId);"
  assert_file_contains "$monitor_workflow" 'createSymbolChartHref(identity)'
  assert_file_contains "$monitor_workflow" "params.set('module', 'ANALYSIS');"
  assert_file_contains "$monitor_workflow" 'identity: row.exactIdentity'
  assert_file_contains "$monitor_workflow" "route: moduleId === 'ANALYSIS' ? row.analysisHref : row.chartHref"
  assert_file_contains "$monitor_workflow" "chartRange: '1D'"
  assert_file_contains "$terminal_app" 'setActiveSymbol(intent.symbol.toUpperCase())'
  assert_file_contains "$terminal_app" 'setActiveIdentity(intent.identity ?? null)'
  assert_file_contains "$terminal_app" 'identity={activeIdentity}'
  assert_file_contains "$terminal_app" 'symbol={activeSymbol}'
  assert_file_contains "$symbol_page" 'createQueryIdentity(normalizedSymbol, resolvedSearchParams)'
  assert_file_contains "$symbol_page" 'initialModuleId={initialModuleId}'
  assert_file_contains "$symbol_page" 'initialIdentity={identity}'
}

assert_retired_old_chart_shell_components() {
  local retired_components=(
    "$repo_root/frontend/components/TimeframeSelector.tsx"
    "$repo_root/frontend/components/IndicatorPanel.tsx"
    "$repo_root/frontend/components/AnalysisPanel.tsx"
    "$repo_root/frontend/components/BrokerPaperStatus.tsx"
  )

  for retired in "${retired_components[@]}"; do
    if [[ -e "$retired" ]]; then
      printf 'expected retired chart shell/control component to be removed: %s\n' "$retired" >&2
      return 1
    fi
  done

  assert_path_missing "$repo_root/frontend/components/SymbolChartView.tsx"
  assert_file_contains "$repo_root/frontend/app/symbols/[symbol]/page.tsx" '<ATradeTerminalApp initialChartRange={initialChartRange} initialIdentity={identity} initialModuleId={initialModuleId} initialSymbol={normalizedSymbol} />'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'TerminalChartWorkspace'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalInstrumentHeader.tsx" 'TerminalInstrumentHeader'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalIndicatorGrid.tsx" 'TerminalIndicatorGrid'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'TerminalAnalysisWorkspace'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalProviderDiagnostics.tsx" 'TerminalProviderDiagnostics'
}

assert_provider_neutral_analysis_contract() {
  local analysis_workflow="$repo_root/frontend/lib/terminalAnalysisWorkflow.ts"
  local analysis_client="$repo_root/frontend/lib/analysisClient.ts"
  local analysis_panel="$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx"
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"

  assert_file_contains "$analysis_client" '/api/analysis/engines'
  assert_file_contains "$analysis_client" '/api/analysis/run'
  assert_file_contains "$analysis_client" 'analysis-engine-not-configured'
  assert_file_contains "$analysis_client" 'analysis-engine-unavailable'
  assert_file_contains "$analysis_workflow" 'getAnalysisEngines()'
  assert_file_contains "$analysis_workflow" 'runProviderNeutralAnalysis(createTerminalAnalysisRunRequest'
  assert_file_contains "$analysis_workflow" 'createTerminalAnalysisRunRequest'
  assert_file_contains "$analysis_workflow" 'symbol: identity'
  assert_file_contains "$analysis_workflow" 'symbolCode: symbol'
  assert_file_contains "$analysis_workflow" 'TERMINAL_ANALYSIS_NO_ORDER_COPY'
  assert_file_contains "$analysis_workflow" 'TERMINAL_ANALYSIS_PROVIDER_NEUTRAL_COPY'
  assert_file_contains "$analysis_panel" 'useTerminalAnalysisWorkflow'
  assert_file_contains "$analysis_panel" 'data-testid="terminal-analysis-workspace"'
  assert_file_contains "$analysis_panel" 'data-testid="analysis-panel"'
  assert_file_contains "$analysis_panel" 'data-testid="analysis-unavailable"'
  assert_file_contains "$analysis_panel" 'data-testid="analysis-run-button"'
  assert_file_contains "$analysis_panel" 'data-testid="analysis-no-automation-note"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx" '<TerminalAnalysisWorkspace symbol={chart.normalizedSymbol} chartRange={chart.chartRange} candleSource={chart.candles?.source} identity={chart.view.identity ?? identity} />'
  assert_file_contains "$terminal_app" '<TerminalAnalysisWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />'
}

assert_disabled_portfolio_orders_and_no_order_entry_ui() {
  local module_registry="$repo_root/frontend/lib/terminalModuleRegistry.ts"
  local disabled_component="$repo_root/frontend/components/terminal/TerminalDisabledModule.tsx"
  local help_component="$repo_root/frontend/components/terminal/TerminalHelpModule.tsx"

  assert_file_contains "$module_registry" 'id: "PORTFOLIO"'
  assert_file_contains "$module_registry" 'No durable positions or portfolio P/L workspace exists beyond current paper account status contracts.'
  assert_file_contains "$module_registry" 'id: "ORDERS"'
  assert_file_contains "$module_registry" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$module_registry" 'does not provide order tickets, buy/sell buttons, staged submissions, previews, or confirmations'
  assert_file_contains "$disabled_component" 'no fake data, no demo provider responses, and no order-entry controls'
  assert_file_contains "$help_component" 'no order tickets, buy/sell controls, previews, or submit actions'

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules 'Place order|Submit order|/api/orders|orders/simulate|MarketOrder|SetBrokerageModel|SetLiveMode' "$repo_root/frontend/components" "$repo_root/frontend/lib"; then
    printf 'frontend workspace must not include order-entry UI, order API calls, or live-trading runtime tokens.\n' >&2
    return 1
  fi
}

assert_no_direct_provider_database_or_order_access() {
  local forbidden_pattern='Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|redis://|nats://|ibkr-gateway|iserver/secdef|iserver/scanner|Client Portal|ATRADE_IBKR|IBKR_USERNAME|IBKR_PASSWORD|ATRADE_LEAN|docker exec|QuantConnect\.Lean|lean-engine|LeanRuntime|/api/orders|orders/simulate'
  local scan_paths=(
    "$repo_root/frontend/app/symbols"
    "$repo_root/frontend/components/terminal"
    "$repo_root/frontend/lib/analysisClient.ts"
    "$repo_root/frontend/lib/marketDataClient.ts"
    "$repo_root/frontend/lib/marketDataStream.ts"
    "$repo_root/frontend/lib/symbolChartWorkflow.ts"
    "$repo_root/frontend/lib/terminalAnalysisWorkflow.ts"
    "$repo_root/frontend/lib/terminalChartWorkspaceWorkflow.ts"
  )

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' "$forbidden_pattern" "${scan_paths[@]}"; then
    printf 'terminal chart/analysis frontend must not directly access provider runtimes, databases, LEAN runtime internals, or broker order routes.\n' >&2
    return 1
  fi
}

main() {
  assert_terminal_chart_workflow_contract
  assert_exact_identity_chart_and_analysis_handoff
  assert_retired_old_chart_shell_components
  assert_provider_neutral_analysis_contract
  assert_disabled_portfolio_orders_and_no_order_entry_ui
  assert_no_direct_provider_database_or_order_access
}

main "$@"
