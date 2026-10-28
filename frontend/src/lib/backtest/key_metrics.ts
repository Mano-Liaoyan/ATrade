// The key metric row of a backtest or a forward test (spec #99): the same metrics in the same order with the same
// sign rule on all pages. The max drawdown is a loss, so it shows as a negative percent, for example "-37.71 %".
// The API has no win rate: it comes from the trades here. The API has no Sharpe ratio, so the row has none.
import { formatSignedNumber, MISSING_VALUE } from '#lib/foundation/value_format';
import type { BacktestMetrics } from './backtest_api';
import { formatMaxDrawdown, formatPercent, formatUsd } from './backtest_format';

/** A trade or a fill: backtest trades and forward test fills have these fields. */
export interface TestTrade {
  time_utc: string;
  side: 'BUY' | 'SELL';
  quantity_shares: string;
  price_usd: string;
  commission_usd: string;
}

export interface KeyMetricInput {
  metrics: BacktestMetrics;
  /** The paper capital of a backtest or the start balance of a forward test. Null when not known. */
  startCapitalUsd: string | null;
  trades: readonly TestTrade[];
}

/** One tile of the row. `change` gives the up or down direction (MetricTile); a tile without it has none. */
export interface KeyMetric {
  name: string;
  text: string;
  change?: number | null;
}

const PERCENT = 100;
const WIN_RATE_DECIMAL_PLACES = 1;
// Share quantities are decimal text. A position under this size is 0.
const FLAT_POSITION_SHARES = 1e-9;

// A round trip starts when the position leaves 0 and ends when it is 0 again. A won round trip has a profit after
// the commissions.
function computeWinRate(trades: readonly TestTrade[]): string {
  let positionShares = 0;
  let cashUsd = 0;
  let roundTrips = 0;
  let wins = 0;
  for (const trade of trades) {
    const quantity = Number(trade.quantity_shares);
    const value = quantity * Number(trade.price_usd);
    cashUsd += (trade.side === 'BUY' ? -value : value) - Number(trade.commission_usd);
    positionShares += trade.side === 'BUY' ? quantity : -quantity;
    if (Math.abs(positionShares) < FLAT_POSITION_SHARES) {
      positionShares = 0;
      roundTrips += 1;
      wins += cashUsd > 0 ? 1 : 0;
      cashUsd = 0;
    }
  }
  return roundTrips === 0 ? MISSING_VALUE : `${((wins / roundTrips) * PERCENT).toFixed(WIN_RATE_DECIMAL_PLACES)} %`;
}

export function readKeyMetrics({ metrics, startCapitalUsd, trades }: KeyMetricInput): KeyMetric[] {
  const totalReturn = Number(metrics.total_return_percent);
  const netProfit = startCapitalUsd === null ? null : Number(metrics.final_equity_usd) - Number(startCapitalUsd);
  return [
    { name: 'Total return', text: formatPercent(metrics.total_return_percent), change: totalReturn },
    { name: 'Net profit (USD)', text: formatSignedNumber(netProfit), change: netProfit },
    { name: 'Max drawdown', ...formatMaxDrawdown(metrics.max_drawdown_percent) },
    { name: 'Win rate', text: computeWinRate(trades) },
    { name: 'Trades', text: String(metrics.trade_count) },
    { name: 'Final equity (USD)', text: formatUsd(metrics.final_equity_usd) },
  ];
}
