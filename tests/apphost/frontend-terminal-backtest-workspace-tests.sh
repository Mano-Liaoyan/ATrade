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

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' --exclude='frontend-terminal-backtest-workspace-tests.sh' "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_backtest_module_registration() {
  assert_file_contains "$frontend_root/types/terminal.ts" '"BACKTEST"'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'id: "BACKTEST"'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'label: "Backtest"'
  assert_file_contains "$frontend_root/lib/terminalModuleRegistry.ts" 'route: "/#terminal-backtest"'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'case "BACKTEST":'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" '<TerminalBacktestWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />'
  assert_file_contains "$frontend_root/components/terminal/ATradeTerminalApp.tsx" 'return "terminal-backtest";'
  assert_file_contains "$frontend_root/app/symbols/[symbol]/page.tsx" "normalizedModule === 'BACKTEST'"
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" 'openBacktestIntent'
  assert_file_contains "$frontend_root/lib/terminalMarketMonitorWorkflow.ts" "params.set('module', moduleId);"
  assert_file_contains "$frontend_root/components/terminal/TerminalMarketMonitor.tsx" 'workflow.openBacktestIntent(row)'
  assert_file_contains "$frontend_root/components/terminal/MarketMonitorTable.tsx" 'Open backtest for'
  assert_file_contains "$frontend_root/components/terminal/MarketMonitorDetailPanel.tsx" 'Open backtest'
}

assert_backtest_api_client_contract() {
  local client="$frontend_root/lib/backtestClient.ts"

  assert_file_contains "$client" "fetchJson<PaperCapitalResponse>('/api/accounts/paper-capital')"
  assert_file_contains "$client" "fetchJson<PaperCapitalResponse>('/api/accounts/local-paper-capital'"
  assert_file_contains "$client" "fetchJson<BacktestRunEnvelope>('/api/backtests'"
  assert_file_contains "$client" 'return fetchJson<BacktestRunEnvelope[]>(`/api/backtests${query ?'
  assert_file_contains "$client" '`/api/backtests/${encodeURIComponent(id)}`'
  assert_file_contains "$client" '`/api/backtests/${encodeURIComponent(id)}/cancel`'
  assert_file_contains "$client" '`/api/backtests/${encodeURIComponent(id)}/retry`'
  assert_file_contains "$client" "withUrl(buildApiUrl('/hubs/backtests'))"
  assert_file_contains "$client" 'BACKTEST_RUN_UPDATE_EVENTS'
  assert_file_contains "$client" 'connection.on(eventName, options.onUpdate)'
  assert_file_contains "$client" 'connection.onreconnecting'
  assert_file_contains "$client" 'connection.onreconnected'
  assert_file_contains "$client" 'connection.onclose'
}

assert_backtest_types_and_workflow_contract() {
  local types="$frontend_root/types/backtesting.ts"
  local workflow="$frontend_root/lib/terminalBacktestWorkflow.ts"

  assert_file_contains "$types" "export type BacktestRunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | string;"
  assert_file_contains "$types" "export type BacktestStrategyId = 'sma-crossover' | 'rsi-mean-reversion' | 'breakout';"
  assert_file_contains "$types" "name: 'shortWindow'"
  assert_file_contains "$types" "name: 'longWindow'"
  assert_file_contains "$types" "name: 'rsiPeriod'"
  assert_file_contains "$types" "name: 'oversoldThreshold'"
  assert_file_contains "$types" "name: 'overboughtThreshold'"
  assert_file_contains "$types" "name: 'lookbackWindow'"
  assert_file_contains "$types" 'export type PaperCapitalResponse = {'
  assert_file_contains "$types" 'export type BacktestCompletedResultEnvelope = {'
  assert_file_contains "$types" 'export type BacktestRunUpdatePayload = {'

  assert_file_contains "$workflow" 'getPaperCapital()'
  assert_file_contains "$workflow" 'updateLocalPaperCapital({ amount, currency: capitalCurrency || DEFAULT_CURRENCY })'
  assert_file_contains "$workflow" 'createBacktestRun(createBacktestCreateRequest'
  assert_file_contains "$workflow" 'cancelBacktestRun(id)'
  assert_file_contains "$workflow" 'retryBacktestRun(id)'
  assert_file_contains "$workflow" 'listBacktestRuns(historyLimit)'
  assert_file_contains "$workflow" 'getBacktestRun(id)'
  assert_file_contains "$workflow" 'connectBacktestRunStream({'
  assert_file_contains "$workflow" "state === 'connected' && reconnectingRef.current"
  assert_file_contains "$workflow" 'fieldErrors.capital'
  assert_file_contains "$workflow" 'source === '\''unavailable'\'''
  assert_file_contains "$workflow" 'setSelectedRunIdState(run.id)'
  assert_file_contains "$workflow" 'setSelectedRunDetail(run)'
  assert_file_contains "$workflow" 'canCancelBacktestRun'
  assert_file_contains "$workflow" 'canRetryBacktestRun'
}

assert_backtest_workspace_surfaces() {
  local workspace="$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"

  assert_file_contains "$workspace" 'data-testid="terminal-backtest-workspace"'
  assert_file_contains "$workspace" 'data-testid="backtest-run-form"'
  assert_file_contains "$workspace" 'data-testid="backtest-symbol-input"'
  assert_file_contains "$workspace" 'data-testid="backtest-chart-range-select"'
  assert_file_contains "$workspace" 'data-testid="backtest-strategy-select"'
  assert_file_contains "$workspace" 'data-testid="backtest-parameter-fields"'
  assert_file_contains "$workspace" 'data-testid={`backtest-parameter-${parameter.name}`}'
  assert_file_contains "$workspace" 'data-testid="backtest-commission-per-trade-input"'
  assert_file_contains "$workspace" 'data-testid="backtest-commission-bps-input"'
  assert_file_contains "$workspace" 'data-testid="backtest-slippage-bps-input"'
  assert_file_contains "$workspace" 'data-testid="backtest-create-run-button"'
  assert_file_contains "$workspace" 'data-testid="backtest-capital-panel"'
  assert_file_contains "$workspace" 'data-testid="backtest-local-capital-form"'
  assert_file_contains "$workspace" 'data-testid="backtest-update-capital-button"'
  assert_file_contains "$workspace" 'data-testid="backtest-stream-state"'
  assert_file_contains "$workspace" 'data-testid="backtest-live-status-panel"'
  assert_file_contains "$workspace" 'data-testid="backtest-cancel-run-button"'
  assert_file_contains "$workspace" 'data-testid="backtest-retry-run-button"'
  assert_file_contains "$workspace" 'Retry as new run'
  assert_file_contains "$workspace" 'data-testid="backtest-run-history"'
  assert_file_contains "$workspace" 'data-testid="backtest-history-row"'
  assert_file_contains "$workspace" 'data-testid="backtest-run-detail"'
  assert_file_contains "$workspace" 'data-testid="backtest-summary-metrics"'
  assert_file_contains "$workspace" 'data-testid="backtest-benchmark-summary"'
  assert_file_contains "$workspace" 'data-testid="backtest-signals-list"'
  assert_file_contains "$workspace" 'data-testid="backtest-trades-list"'
  assert_file_contains "$workspace" 'data-testid="backtest-source-metadata"'
  assert_file_contains "$workspace" 'data-testid="backtest-no-fake-results-note"'
  assert_file_contains "$workspace" 'Analysis engine unavailable:'
  assert_file_contains "$workspace" 'Market-data provider unavailable:'
  assert_file_contains "$workspace" 'No demo runs, fixture strategies, synthetic equity curves, browser-supplied bars, or fabricated trades'
  assert_file_contains "$workspace" 'No account identifiers are shown in the browser.'
  assert_file_not_contains "$workspace" 'type="submit"'
}

assert_no_order_controls_or_direct_runtime_access() {
  local scan_paths=(
    "$frontend_root/app/symbols/[symbol]/page.tsx"
    "$frontend_root/components/terminal/ATradeTerminalApp.tsx"
    "$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"
    "$frontend_root/components/terminal/TerminalMarketMonitor.tsx"
    "$frontend_root/components/terminal/MarketMonitorTable.tsx"
    "$frontend_root/components/terminal/MarketMonitorDetailPanel.tsx"
    "$frontend_root/lib/backtestClient.ts"
    "$frontend_root/lib/terminalBacktestWorkflow.ts"
    "$frontend_root/lib/terminalMarketMonitorWorkflow.ts"
    "$frontend_root/types/backtesting.ts"
  )

  assert_no_grep_matches \
    'order-entry or live-trading control in backtest frontend source' \
    'Place order|Submit order|Preview order|Confirm order|OrderTicket|MarketOrder|LimitOrder|SetBrokerageModel|SetLiveMode|/api/orders|orders/simulate|buy-button|sell-button|type="submit"' \
    "${scan_paths[@]}"

  assert_no_grep_matches \
    'direct provider, database, runtime, secret, or account identifier access in backtest frontend source' \
    'Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|postgres://|redis://|nats://|ibkr-gateway|/iserver/|/hmds/|localhost:5000|127\.0\.0\.1:5000|Client Portal|ATRADE_IBKR|IBKR_USERNAME|IBKR_PASSWORD|ATRADE_LEAN|docker exec|QuantConnect\.Lean|lean-engine|LeanRuntime|DU[0-9]{6,}|U[0-9]{7,}|accountId|accountNumber|token|cookie|sessionid' \
    "${scan_paths[@]}"
}

main() {
  assert_backtest_module_registration
  assert_backtest_api_client_contract
  assert_backtest_types_and_workflow_contract
  assert_backtest_workspace_surfaces
  assert_no_order_controls_or_direct_runtime_access

  printf 'Frontend terminal backtest workspace validation passed.\n'
}

main "$@"
