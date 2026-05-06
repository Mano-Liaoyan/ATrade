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

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_no_lean_order_tokens() {
  if grep -RIn --exclude-dir=bin --exclude-dir=obj --exclude='LeanAnalysisGuardrails.cs' --exclude='LeanAnalysisEngineTests.cs' -E 'MarketOrder\(|LimitOrder\(|StopMarketOrder\(|StopLimitOrder\(|Liquidate\(|SetBrokerageModel|BrokerageName\.|SetLiveMode|IBrokerage|/api/orders' "$repo_root/src/ATrade.Analysis.Lean"; then
    printf 'generated LEAN strategy support must remain analysis-only and order-free.\n' >&2
    return 1
  fi
}

main() {
  local contracts="$repo_root/src/ATrade.Backtesting/BacktestingContracts.cs"
  local definitions="$repo_root/src/ATrade.Backtesting/BacktestStrategyDefinitions.cs"
  local validator="$repo_root/src/ATrade.Backtesting/BacktestRequestValidation.cs"
  local persistence="$repo_root/src/ATrade.Backtesting/BacktestPersistenceSafety.cs"
  local pipeline="$repo_root/src/ATrade.Backtesting/BacktestRunAnalysisExecutionPipeline.cs"
  local analysis_contracts="$repo_root/src/ATrade.Analysis/AnalysisContracts.cs"
  local frontend_analysis_types="$repo_root/frontend/types/analysis.ts"
  local lean_input="$repo_root/src/ATrade.Analysis.Lean/LeanInputConverter.cs"
  local lean_template="$repo_root/src/ATrade.Analysis.Lean/LeanAlgorithmTemplate.cs"
  local lean_parser="$repo_root/src/ATrade.Analysis.Lean/LeanAnalysisResultParser.cs"
  local backtesting_tests="$repo_root/tests/ATrade.Backtesting.Tests/BacktestRequestValidatorTests.cs"
  local pipeline_tests="$repo_root/tests/ATrade.Backtesting.Tests/BacktestRunAnalysisExecutionPipelineTests.cs"
  local lean_tests="$repo_root/tests/ATrade.Analysis.Lean.Tests/LeanAnalysisEngineTests.cs"

  assert_file_contains "$definitions" 'BacktestStrategyCatalog'
  assert_file_contains "$contracts" 'SmaCrossover = "sma-crossover"'
  assert_file_contains "$contracts" 'RsiMeanReversion = "rsi-mean-reversion"'
  assert_file_contains "$contracts" 'Breakout = "breakout"'
  assert_file_contains "$definitions" 'shortWindow'
  assert_file_contains "$definitions" 'longWindow'
  assert_file_contains "$definitions" 'rsiPeriod'
  assert_file_contains "$definitions" 'oversoldThreshold'
  assert_file_contains "$definitions" 'overboughtThreshold'
  assert_file_contains "$definitions" 'lookbackWindow'

  assert_file_contains "$validator" 'NormalizeStrategyParameterValue'
  assert_file_contains "$validator" 'ValidateStrategyParameterRelationships'
  assert_file_contains "$validator" 'RejectForbiddenPropertyName(key)'
  assert_file_contains "$validator" 'CustomCodeFieldNames'
  assert_file_contains "$validator" 'OrderRoutingFieldNames'
  assert_file_contains "$validator" 'DirectBarFieldNames'
  assert_file_contains "$validator" 'MultiSymbolFieldNames'

  assert_file_contains "$contracts" 'BacktestCompletedResultEnvelope'
  assert_file_contains "$contracts" 'BacktestResultSummaryEnvelope'
  assert_file_contains "$contracts" 'BacktestResultEquityCurvePointEnvelope'
  assert_file_contains "$contracts" 'BacktestResultTradeEnvelope'
  assert_file_contains "$contracts" 'BacktestResultBenchmarkEnvelope'
  assert_file_contains "$contracts" 'BacktestResultAccountingEnvelope'
  assert_file_contains "$contracts" 'public const string Default = BuyAndHold;'
  assert_file_contains "$persistence" 'SafeResultPropertyNames'
  assert_file_contains "$persistence" 'BacktestStrategyParameterNames.BreakoutLookbackWindow'

  assert_file_contains "$analysis_contracts" 'AnalysisBacktestDetails'
  assert_file_contains "$analysis_contracts" 'AnalysisEquityCurvePoint'
  assert_file_contains "$analysis_contracts" 'AnalysisSimulatedTrade'
  assert_file_contains "$analysis_contracts" 'AnalysisBenchmark'
  assert_file_contains "$analysis_contracts" 'AnalysisBacktestAccounting'
  assert_file_contains "$analysis_contracts" 'StrategyParameters'
  assert_file_contains "$analysis_contracts" 'BacktestSettings'
  assert_file_contains "$frontend_analysis_types" 'AnalysisBacktestDetails'
  assert_file_contains "$frontend_analysis_types" 'AnalysisEquityCurvePoint'
  assert_file_contains "$frontend_analysis_types" 'AnalysisSimulatedTrade'
  assert_file_contains "$frontend_analysis_types" 'AnalysisBenchmark'
  assert_file_contains "$frontend_analysis_types" 'AnalysisBacktestAccounting'
  assert_file_contains "$frontend_analysis_types" 'maxDrawdownPercent'
  assert_file_contains "$frontend_analysis_types" 'totalCost'
  assert_file_contains "$frontend_analysis_types" 'strategyParameters?: Record<string, unknown>'
  assert_file_contains "$frontend_analysis_types" 'backtestSettings?: AnalysisBacktestSettings | null'

  assert_file_contains "$lean_input" 'StrategyParameters'
  assert_file_contains "$lean_input" 'CommissionPerTrade'
  assert_file_contains "$lean_template" 'self.strategy_id ='
  assert_file_contains "$lean_template" 'self.strategy_parameters = json.loads'
  assert_file_contains "$lean_template" 'self.commission_per_trade'
  assert_file_contains "$lean_template" 'self.slippage_bps'
  assert_file_contains "$lean_template" 'def _sma_action'
  assert_file_contains "$lean_template" 'def _rsi_action'
  assert_file_contains "$lean_template" 'def _breakout_action'
  assert_file_contains "$lean_template" '"equityCurve"'
  assert_file_contains "$lean_template" '"trades"'
  assert_file_contains "$lean_parser" 'ReadBacktestDetails'
  assert_file_contains "$lean_parser" 'ReadTrades'
  assert_file_contains "$lean_parser" 'ReadAccounting'

  assert_file_contains "$pipeline" 'StrategyParameters: request.Parameters'
  assert_file_contains "$pipeline" 'BacktestSettings: new AnalysisBacktestSettings'
  assert_file_contains "$pipeline" 'tp-061.backtest-result.v1'
  assert_file_contains "$pipeline" 'CreateBuyAndHoldBenchmark'
  assert_file_contains "$pipeline" 'BacktestBenchmarkModes.BuyAndHold'
  assert_file_contains "$pipeline" 'BacktestResultTradeEnvelope'
  assert_file_contains "$pipeline" 'BacktestResultEquityCurvePointEnvelope'

  assert_file_contains "$backtesting_tests" 'PersistedRequestSnapshots_RoundTripBuiltInStrategyDefaults'
  assert_file_contains "$backtesting_tests" 'Validate_RejectsUnknownAndInvalidStrategyParameters'
  assert_file_contains "$backtesting_tests" 'Validate_RejectsInvalidCostAndSlippageInputs'
  assert_file_contains "$pipeline_tests" 'ExecuteAsync_CompletesRichResultsForEachBuiltInStrategy'
  assert_file_contains "$pipeline_tests" 'benchmark'
  assert_file_contains "$pipeline_tests" 'equityCurve'
  assert_file_contains "$pipeline_tests" 'trades'
  assert_file_contains "$lean_tests" 'AlgorithmTemplateStaysAnalysisOnlyAndRejectsTradingCalls'
  assert_file_contains "$lean_tests" 'rsi-mean-reversion'
  assert_file_contains "$lean_tests" 'lookbackWindow'

  assert_file_not_contains "$contracts" 'string? CustomCode'
  assert_file_not_contains "$contracts" 'string? StrategyCode'
  assert_file_not_contains "$contracts" 'OrderType'
  assert_file_not_contains "$contracts" 'AccountId'
  assert_no_lean_order_tokens

  printf 'Backtesting strategy/result source validation passed.\n'
}

main "$@"
