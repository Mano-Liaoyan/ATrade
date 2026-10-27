// Public entry of forward_test: start and stop forward tests, the list with the actual status, the socket message,
// and the comparison with a backtest of the same period.
export { default as FillComparisonTable } from './FillComparisonTable.svelte';
export { default as ForwardTestList } from './ForwardTestList.svelte';
export {
  canBacktestSamePeriod,
  canStop,
  describeForwardTestStatus,
  FORWARD_TESTS_SOCKET_PATH,
  isLiveBarPeriod,
  readForwardTestComparison,
  readForwardTestsMessage,
  startForwardTest,
  startSamePeriodBacktest,
  stopForwardTest,
  type FillComparison,
  type ForwardTest,
  type ForwardTestComparison,
  type ForwardTestRequest,
  type ForwardTestStatus,
  type Interruption,
} from './forward_test_api';
