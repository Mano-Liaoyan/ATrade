// Public entry of the backtest capability: the backtest HTTP client, the key metric row and the equity and drawdown
// chart (for the backtest, strategy, forward test, and comparison pages), the compared key metrics of the comparison
// pages, and the value formats.
export { default as BacktestLimitsForm } from './BacktestLimitsForm.svelte';
export { default as BacktestMetricTable } from './BacktestMetricTable.svelte';
export { default as BacktestTradeTable } from './BacktestTradeTable.svelte';
export { default as ComparedKeyMetrics } from './ComparedKeyMetrics.svelte';
export { default as EquityDrawdownChart, type DrawdownCurve } from './EquityDrawdownChart.svelte';
export { default as KeyMetricRow } from './KeyMetricRow.svelte';
export { type TimeInterval } from './interruption_marks';
export { computeDrawdownCurve, type DrawdownPoint } from './drawdown_curve';
export { readKeyMetrics, type ComparedTest, type KeyMetric, type KeyMetricInput } from './key_metrics';
export { readMetricRows, type MetricTableRow, type MetricTableValue } from './metric_table';
export { checkComparisonSelection, type ComparisonSelection } from './backtest_comparison';
export {
  changeBacktestLimits,
  compareBacktests,
  deleteBacktest,
  listBacktests,
  readBacktestLimits,
  readBacktest,
  readBacktestInstrument,
  readUsUniverseRange,
  startBacktest,
  type Backtest,
  type BacktestComparison,
  type BacktestDetail,
  type BacktestInstrument,
  type BacktestLimits,
  type BacktestMetrics,
  type BacktestRequest,
  type BacktestStatus,
  type BacktestTrade,
  type DeleteBacktestResult,
  type EquityPoint,
  type RequestResult,
  type UniverseInstrument,
  type UsUniverseRange,
} from './backtest_api';
export {
  checkTopN,
  formatPeriodCountHeader,
  formatUniverseLabel,
  formatUniverseRange,
  makeScreenUniverseFields,
  MAX_TOP_N,
  type RebalancePeriod,
  type ScreenSource,
  type ScreenUniverseSource,
} from './backtest_universe';
export { default as UniverseInstrumentTable } from './UniverseInstrumentTable.svelte';
export {
  convertDateToUtcStart,
  convertTimeoutMinutesToSeconds,
  describeBacktestStatus,
  findBacktestStatusKind,
  findErrorSummary,
  formatMaxDrawdown,
  formatPercent,
  formatTimeoutMinutes,
  formatUsd,
  isFinalStatus,
} from './backtest_format';
