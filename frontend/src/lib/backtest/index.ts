// Public entry of the backtest capability: the backtest HTTP client, the result view, and the value formats.
export { default as BacktestResult } from './BacktestResult.svelte';
export {
  listBacktests,
  readBacktest,
  startBacktest,
  type Backtest,
  type BacktestDetail,
  type BacktestMetrics,
  type BacktestRequest,
  type BacktestStatus,
  type BacktestTrade,
  type EquityPoint,
  type RequestResult,
} from './backtest_api';
export { convertDateToUtcStart, describeBacktestStatus, formatPercent, formatUsd, isFinalStatus } from './backtest_format';
