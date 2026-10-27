// Public entry of the backtest capability: the backtest HTTP client, the result view, the comparison view (also for
// forward tests), and the value formats.
export { default as BacktestResult } from './BacktestResult.svelte';
export { default as ComparisonView, type ComparedCode, type ComparedRun } from './ComparisonView.svelte';
export { default as EquityChart, type EquityCurve } from './EquityChart.svelte';
export { checkComparisonSelection, type ComparisonSelection } from './backtest_comparison';
export {
  compareBacktests,
  listBacktests,
  readBacktest,
  startBacktest,
  type Backtest,
  type BacktestComparison,
  type BacktestDetail,
  type BacktestMetrics,
  type BacktestRequest,
  type BacktestStatus,
  type BacktestTrade,
  type EquityPoint,
  type RequestResult,
} from './backtest_api';
export { convertDateToUtcStart, describeBacktestStatus, formatPercent, formatUsd, isFinalStatus } from './backtest_format';
