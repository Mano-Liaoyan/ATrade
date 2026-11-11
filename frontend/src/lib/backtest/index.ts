// Public entry of the backtest capability: the backtest HTTP client, the key metric row and the equity and drawdown
// chart (for the backtest, strategy, forward test, and comparison pages), the compared key metrics of the comparison
// pages, the value formats, and the Equity / Bars chart view of the backtest and forward test panels.
export { default as BacktestLimitsForm } from './BacktestLimitsForm.svelte';
export { default as BacktestMetricTable } from './BacktestMetricTable.svelte';
export { default as BacktestTradeTable } from './BacktestTradeTable.svelte';
export { default as ChartInstrumentSelect } from './ChartInstrumentSelect.svelte';
export { default as ChartViewSwitcher } from './ChartViewSwitcher.svelte';
export { default as ComparedKeyMetrics } from './ComparedKeyMetrics.svelte';
export { default as EquityDrawdownChart, type DrawdownCurve } from './EquityDrawdownChart.svelte';
export { default as KeyMetricRow } from './KeyMetricRow.svelte';
export { type TimeInterval } from './interruption_marks';
export { computeDrawdownCurve, type DrawdownPoint } from './drawdown_curve';
export { readKeyMetrics, type ComparedTest, type KeyMetric, type KeyMetricInput } from './key_metrics';
export { readMetricRows, type MetricTableRow, type MetricTableValue } from './metric_table';
export { formatChartViewSearch, readChartView, type ChartView } from './chart_view';
export { checkComparisonSelection, type ComparisonSelection } from './backtest_comparison';
export {
  changeBacktestLimits,
  compareBacktests,
  deleteBacktest,
  BACKTESTS_SOCKET_PATH,
  listBacktests,
  readBacktestLimits,
  readBacktest,
  listChartInstruments,
  readBacktestInstrument,
  readUsUniverseRange,
  rerunBacktest,
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
