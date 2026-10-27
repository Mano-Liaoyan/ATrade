// Calls the backtest HTTP routes and turns each answer into a result that the backtest pages can show.
import { describe, expect, it } from 'vitest';
import { startBacktest, type BacktestRequest } from './index';

const REQUEST: BacktestRequest = {
  strategy_version_id: 7,
  symbol: 'AAPL',
  exchange: 'NASDAQ',
  currency: 'USD',
  bar_period: '1-DAY',
  start_utc: '2025-01-01T00:00:00Z',
  end_utc: '2026-01-01T00:00:00Z',
  paper_capital_usd: '10000',
};

describe('startBacktest', () => {
  it('sends the request as JSON and returns the queued backtest', async () => {
    let sentBody = '';
    const recordingFetch: typeof fetch = (_path, init) => {
      sentBody = typeof init?.body === 'string' ? init.body : '';
      return Promise.resolve(new Response(JSON.stringify({ id: 3, status: 'queued' }), { status: 201 }));
    };

    const result = await startBacktest(recordingFetch, REQUEST);

    expect(JSON.parse(sentBody)).toEqual(REQUEST);
    expect(result).toEqual({ kind: 'ok', value: { id: 3, status: 'queued' } });
  });

  it('shows the reason when the backend refuses the request', async () => {
    const refusingFetch: typeof fetch = () =>
      Promise.resolve(new Response(JSON.stringify({ detail: 'The time range must end after it starts.' }), { status: 422 }));

    const result = await startBacktest(refusingFetch, REQUEST);

    expect(result).toEqual({ kind: 'failed', message: 'The time range must end after it starts.' });
  });

  it('shows the first field error of a request that does not validate', async () => {
    const detail = [{ loc: ['body', 'paper_capital_usd'], msg: 'Input should be greater than 0', type: 'greater_than' }];
    const refusingFetch: typeof fetch = () => Promise.resolve(new Response(JSON.stringify({ detail }), { status: 422 }));

    const result = await startBacktest(refusingFetch, REQUEST);

    expect(result).toEqual({ kind: 'failed', message: 'paper_capital_usd: Input should be greater than 0' });
  });

  it('reports a failure when the backend is not reachable', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const result = await startBacktest(failingFetch, REQUEST);

    expect(result).toEqual({ kind: 'failed', message: 'The backend is not reachable.' });
  });
});
