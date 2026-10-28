// Public entry of the backtest capability: the backtest HTTP client, the key metric row and the equity and drawdown
// chart (for the backtest page, and later for the strategy and forward test pages), the comparison view (also for
// forward tests), and the value formats.
export { default as BacktestLimitsForm } from './BacktestLimitsForm.svelte';
export { default as BacktestTradeTable } from './BacktestTradeTable.svelte';
export { default as ComparisonView, type ComparedCode, type ComparedRun } from './ComparisonView.svelte';
export { default as EquityChart, type EquityCurve } from './EquityChart.svelte';
export { default as EquityDrawdownChart, type DrawdownCurve } from './EquityDrawdownChart.svelte';
export { default as KeyMetricRow } from './KeyMetricRow.svelte';
export { type TimeInterval } from './interruption_marks';
export { computeDrawdownCurve, type DrawdownPoint } from './drawdown_curve';
export { readKeyMetrics, type KeyMetric, type KeyMetricInput, type TestTrade } from './key_metrics';
export { checkComparisonSelection, type ComparisonSelection } from './backtest_comparison';
export {
  changeBacktestLimits,
  compareBacktests,
  listBacktests,
  readBacktestLimits,
  readBacktest,
  startBacktest,
  type Backtest,
  type BacktestComparison,
  type BacktestDetail,
  type BacktestLimits,
  type BacktestMetrics,
  type BacktestRequest,
  type BacktestStatus,
  type BacktestTrade,
  type EquityPoint,
  type RequestResult,
} from './backtest_api';
export {
  convertDateToUtcStart,
  convertTimeoutMinutesToSeconds,
  describeBacktestStatus,
  findBacktestStatusKind,
  formatMaxDrawdown,
  formatPercent,
  formatTimeoutMinutes,
  formatUsd,
  isFinalStatus,
} from './backtest_format';
