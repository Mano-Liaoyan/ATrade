// The comparison of two backtests: the selection rule of the list, and the HTTP client of the comparison route.
import { describe, expect, it } from 'vite-plus/test';
import { checkComparisonSelection, compareBacktests, type Backtest } from './index';

function makeBacktest(id: number, strategyId: number, strategyName: string): Backtest {
  return {
    id,
    strategy_version_id: id * 10,
    strategy_id: strategyId,
    strategy_name: strategyName,
    version_number: id,
    symbol: 'AAPL',
    exchange: 'NASDAQ',
    currency: 'USD',
    bar_period: '1-DAY',
    start_utc: '2025-01-01T00:00:00Z',
    end_utc: '2026-01-01T00:00:00Z',
    paper_capital_usd: '10000',
    status: 'finished',
    error_message: null,
    created_at_utc: '2026-01-02T00:00:00Z',
    started_at_utc: null,
    ended_at_utc: null,
    metrics: null,
    source_order: ['ibkr', 'databento'],
    bar_count_by_source: null,
    survivorship_bias: false,
  };
}

const BACKTESTS = [makeBacktest(1, 5, 'Trend'), makeBacktest(2, 5, 'Trend'), makeBacktest(3, 6, 'Mean reversion')];

describe('checkComparisonSelection', () => {
  it('is ready for two backtests of the same strategy, the older backtest first', () => {
    expect(checkComparisonSelection(BACKTESTS, [2, 1])).toEqual({
      kind: 'ready',
      firstBacktestId: 1,
      secondBacktestId: 2,
    });
  });

  it('asks for two backtests while fewer are selected', () => {
    expect(checkComparisonSelection(BACKTESTS, [1])).toEqual({
      kind: 'not_ready',
      message: 'Select 2 backtests of the same strategy to compare them.',
    });
  });

  it('rejects backtests of different strategies', () => {
    expect(checkComparisonSelection(BACKTESTS, [1, 3])).toEqual({
      kind: 'not_ready',
      message: 'Only backtests of the same strategy can be compared. These backtests use Trend and Mean reversion.',
    });
  });

  it('rejects more than two backtests', () => {
    expect(checkComparisonSelection(BACKTESTS, [1, 2, 3])).toEqual({
      kind: 'not_ready',
      message: 'Select only 2 backtests.',
    });
  });
});

describe('compareBacktests', () => {
  it('reads the comparison route of the two backtests', async () => {
    let requestedPath = '';
    const recordingFetch: typeof fetch = (path) => {
      requestedPath = typeof path === 'string' ? path : '';
      return Promise.resolve(new Response(JSON.stringify({ strategy_id: 5 }), { status: 200 }));
    };

    const result = await compareBacktests(recordingFetch, 1, 2);

    expect(requestedPath).toBe('/api/backtests/1/comparison/2');
    expect(result).toEqual({ kind: 'ok', value: { strategy_id: 5 } });
  });
});
