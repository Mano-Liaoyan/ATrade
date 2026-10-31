// The key metric row of a backtest or a forward test (spec #99, #137): the same metrics in the same order with the
// same sign rule on all pages. The max drawdown is a loss, so it shows as a negative percent, for example "-37.71 %".
// The Sharpe ratio and the win rate come from the API (docs/architecture/backtest.md section 10.9.2). The API gives a
// metric without a meaning as null: the tile shows "–".
import { formatSignedNumber, MISSING_VALUE } from '#lib/foundation/value_format';
import type { BacktestMetrics } from './backtest_api';
import { formatMaxDrawdown, formatPercent, formatRatio, formatUnsignedPercent, formatUsd } from './backtest_format';

/** The metrics that the row shows. */
export type KeyMetricValues = Pick<
  BacktestMetrics,
  'final_equity_usd' | 'total_return_percent' | 'max_drawdown_percent' | 'trade_count' | 'sharpe_ratio' | 'win_rate_percent'
>;

export interface KeyMetricInput {
  /** Null for a test without a result (for example a backtest that runs): all tiles show a dash. */
  metrics: KeyMetricValues | null;
  /** The paper capital of a backtest or the start balance of a forward test. Null when not known. */
  startCapitalUsd: string | null;
}

/** One test of a comparison page (ComparedKeyMetrics): its name, its page, and its key metric input. */
export interface ComparedTest extends KeyMetricInput {
  name: string;
  /** The resolved path of the backtest or forward test page. */
  href: string;
}

/** One tile of the row. `change` gives the up or down direction (MetricTile); a tile without it has none. */
export interface KeyMetric {
  name: string;
  text: string;
  change?: number | null;
}

const KEY_METRIC_NAMES = [
  'Total return',
  'Net profit (USD)',
  'Max drawdown',
  'Sharpe ratio',
  'Win rate',
  'Trades',
  'Final equity (USD)',
];

export function readKeyMetrics({ metrics, startCapitalUsd }: KeyMetricInput): KeyMetric[] {
  if (metrics === null) {
    return KEY_METRIC_NAMES.map((name) => ({ name, text: MISSING_VALUE }));
  }
  const totalReturn = Number(metrics.total_return_percent);
  const netProfit = startCapitalUsd === null ? null : Number(metrics.final_equity_usd) - Number(startCapitalUsd);
  return [
    { name: 'Total return', text: formatPercent(metrics.total_return_percent), change: totalReturn },
    { name: 'Net profit (USD)', text: formatSignedNumber(netProfit), change: netProfit },
    { name: 'Max drawdown', ...formatMaxDrawdown(metrics.max_drawdown_percent) },
    { name: 'Sharpe ratio', text: formatRatio(metrics.sharpe_ratio) },
    { name: 'Win rate', text: formatUnsignedPercent(metrics.win_rate_percent) },
    { name: 'Trades', text: String(metrics.trade_count) },
    { name: 'Final equity (USD)', text: formatUsd(metrics.final_equity_usd) },
  ];
}
