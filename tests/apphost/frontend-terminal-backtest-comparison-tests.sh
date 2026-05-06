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

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' --exclude='frontend-terminal-backtest-comparison-tests.sh' "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_comparison_workflow_helpers() {
  local workflow="$frontend_root/lib/terminalBacktestWorkflow.ts"

  assert_file_contains "$workflow" 'TERMINAL_BACKTEST_COMPARISON_COPY'
  assert_file_contains "$workflow" 'TerminalBacktestComparisonViewModel'
  assert_file_contains "$workflow" 'comparisonSelectedRunIds'
  assert_file_contains "$workflow" 'toggleComparisonRunSelection'
  assert_file_contains "$workflow" 'removeComparisonRunSelection'
  assert_file_contains "$workflow" 'clearComparisonSelection'
  assert_file_contains "$workflow" 'canCompareBacktestRun'
  assert_file_contains "$workflow" "isBacktestStatus(run.status, 'completed')"
  assert_file_contains "$workflow" 'run.result?.backtest'
  assert_file_contains "$workflow" 'normalizeBacktestEquitySeries(run.result.equityCurve'
  assert_file_contains "$workflow" 'pruneBacktestComparisonSelection'
  assert_file_contains "$workflow" 'buildBacktestComparisonViewModel'
  assert_file_contains "$workflow" 'createBacktestComparisonRunSummary'
  assert_file_contains "$workflow" 'getBacktestComparisonEligibilityCopy'
}

assert_comparison_color_and_normalization_helpers() {
  local workflow="$frontend_root/lib/terminalBacktestWorkflow.ts"

  assert_file_contains "$workflow" 'BACKTEST_COMPARISON_STRATEGY_COLORS'
  assert_file_contains "$workflow" 'BACKTEST_COMPARISON_BENCHMARK_COLORS'
  assert_file_contains "$workflow" 'getBacktestComparisonCurveColor'
  assert_file_contains "$workflow" 'formatBacktestComparisonCurveLabel'
  assert_file_contains "$workflow" 'hashBacktestComparisonKey'
  assert_file_contains "$workflow" 'normalizedReturnPercent'
  assert_file_contains "$workflow" 'fallbackInitialEquity'
  assert_file_contains "$workflow" "kind === 'strategy'"
  assert_file_contains "$workflow" "kind === 'benchmark'"
  assert_file_contains "$workflow" 'buy-and-hold'
}

assert_comparison_workspace_surface() {
  local workspace="$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"
  local panel="$frontend_root/components/terminal/BacktestComparisonPanel.tsx"
  local workflow="$frontend_root/lib/terminalBacktestWorkflow.ts"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$workspace" '<BacktestComparisonPanel workflow={workflow} />'
  assert_file_contains "$workspace" 'data-testid="backtest-comparison-select-run"'
  assert_file_contains "$workspace" 'disabled={!comparable}'
  assert_file_contains "$workspace" 'Completed result required'
  assert_file_contains "$workspace" 'getBacktestComparisonEligibilityCopy(run)'

  assert_file_contains "$panel" 'data-testid="backtest-comparison-panel"'
  assert_file_contains "$panel" 'data-testid="backtest-comparison-selected-cards"'
  assert_file_contains "$panel" 'data-testid="backtest-comparison-metrics"'
  assert_file_contains "$panel" 'Strategy</th>'
  assert_file_contains "$panel" 'Symbol</th>'
  assert_file_contains "$panel" 'Range</th>'
  assert_file_contains "$panel" 'Capital source</th>'
  assert_file_contains "$panel" 'Return</th>'
  assert_file_contains "$panel" 'Max drawdown</th>'
  assert_file_contains "$panel" 'Win rate</th>'
  assert_file_contains "$panel" 'Trades</th>'
  assert_file_contains "$panel" 'Final equity</th>'
  assert_file_contains "$panel" 'Benchmark return</th>'
  assert_file_contains "$panel" 'Status/source</th>'
  assert_file_contains "$panel" 'data-testid="backtest-equity-overlay"'
  assert_file_contains "$panel" 'role="img"'
  assert_file_contains "$panel" 'Strategy equity and buy-and-hold benchmark overlay'
  assert_file_contains "$panel" 'data-testid="backtest-comparison-legend"'
  assert_file_contains "$panel" 'Strategy equity'
  assert_file_contains "$panel" 'Buy-and-hold benchmark'
  assert_file_contains "$panel" 'No persisted equity curve points to draw.'
  assert_file_contains "$panel" 'no synthetic benchmark is generated in the browser'
  assert_file_contains "$workflow" 'Select at least two completed saved runs'

  assert_file_contains "$css" '.terminal-backtest-comparison'
  assert_file_contains "$css" '.terminal-backtest-comparison__svg'
  assert_file_contains "$css" '.terminal-backtest-comparison__table-wrap'
  assert_file_contains "$css" '.terminal-backtest-history__compare'
  assert_file_contains "$css" '.terminal-backtest-comparison__legend'
}

assert_no_export_fake_data_or_new_chart_dependency() {
  local panel="$frontend_root/components/terminal/BacktestComparisonPanel.tsx"
  local workspace="$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"
  local workflow="$frontend_root/lib/terminalBacktestWorkflow.ts"
  local package_json="$frontend_root/package.json"

  assert_file_not_contains "$panel" 'Export'
  assert_file_not_contains "$panel" 'Download'
  assert_file_not_contains "$panel" 'CSV'
  assert_file_not_contains "$workspace" 'Export comparison'
  assert_file_not_contains "$package_json" 'recharts'
  assert_file_not_contains "$package_json" 'chart.js'
  assert_file_not_contains "$package_json" '@visx'

  assert_no_grep_matches \
    'fake comparison/demo result source' \
    'mockBacktest|sampleBacktest|fixtureComparison|demoComparison|fakeComparison|hardcodedEquity|syntheticEquity' \
    "$panel" "$workspace" "$workflow"
}

assert_no_order_controls_or_direct_runtime_access() {
  local scan_paths=(
    "$frontend_root/components/terminal/BacktestComparisonPanel.tsx"
    "$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"
    "$frontend_root/lib/terminalBacktestWorkflow.ts"
    "$frontend_root/lib/backtestClient.ts"
    "$frontend_root/types/backtesting.ts"
  )

  assert_no_grep_matches \
    'export, order-entry, or live-trading control in backtest comparison frontend source' \
    'Export comparison|Download CSV|Place order|Submit order|Preview order|Confirm order|OrderTicket|MarketOrder|LimitOrder|SetBrokerageModel|SetLiveMode|/api/orders|orders/simulate|buy-button|sell-button|type="submit"' \
    "${scan_paths[@]}"

  assert_no_grep_matches \
    'direct provider, database, runtime, secret, or account identifier access in backtest comparison frontend source' \
    'Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|postgres://|redis://|nats://|ibkr-gateway|/iserver/|/hmds/|localhost:5000|127\.0\.0\.1:5000|Client Portal|ATRADE_IBKR|IBKR_USERNAME|IBKR_PASSWORD|ATRADE_LEAN|docker exec|QuantConnect\.Lean|lean-engine|LeanRuntime|DU[0-9]{6,}|U[0-9]{7,}|accountId|accountNumber|token|cookie|sessionid' \
    "${scan_paths[@]}"
}

main() {
  assert_comparison_workflow_helpers
  assert_comparison_color_and_normalization_helpers
  assert_comparison_workspace_surface
  assert_no_export_fake_data_or_new_chart_dependency
  assert_no_order_controls_or_direct_runtime_access

  printf 'Frontend terminal backtest comparison validation passed.\n'
}

main "$@"
