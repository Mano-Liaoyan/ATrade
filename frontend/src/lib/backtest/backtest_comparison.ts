// The selection rule of the backtest list: compare only 2 backtests of the same strategy (docs/architecture section 9.5).
// The backend applies the same rule (GET /api/backtests/{first}/comparison/{second}).
import type { Backtest } from './backtest_api';

export type ComparisonSelection =
  | { kind: 'ready'; firstBacktestId: number; secondBacktestId: number }
  | { kind: 'not_ready'; message: string };

const COMPARED_BACKTEST_COUNT = 2;

export function checkComparisonSelection(backtests: Backtest[], selectedIds: number[]): ComparisonSelection {
  if (selectedIds.length > COMPARED_BACKTEST_COUNT) {
    return { kind: 'not_ready', message: 'Select only 2 backtests.' };
  }
  const selected = backtests.filter((backtest) => selectedIds.includes(backtest.id)).sort((a, b) => a.id - b.id);
  const [first, second] = selected;
  if (first === undefined || second === undefined) {
    return { kind: 'not_ready', message: 'Select 2 backtests of the same strategy to compare them.' };
  }
  if (first.strategy_id !== second.strategy_id) {
    return {
      kind: 'not_ready',
      message: `Only backtests of the same strategy can be compared. These backtests use ${first.strategy_name} and ${second.strategy_name}.`,
    };
  }
  return { kind: 'ready', firstBacktestId: first.id, secondBacktestId: second.id };
}
