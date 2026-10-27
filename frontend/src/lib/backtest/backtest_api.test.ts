// Calls the backtest HTTP routes and turns each answer into a result that the backtest pages can show.
import { describe, expect, it } from 'vitest';
import { changeBacktestLimits, readBacktestLimits, startBacktest, type BacktestRequest } from './index';

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

describe('backtest limits', () => {
  it('reads the timeout and the concurrency', async () => {
    const limitsFetch: typeof fetch = (path) => {
      expect(path).toBe('/api/backtest-limits');
      return Promise.resolve(new Response(JSON.stringify({ timeout_seconds: 7200, concurrency: 1 }), { status: 200 }));
    };

    const result = await readBacktestLimits(limitsFetch);

    expect(result).toEqual({ kind: 'ok', value: { timeout_seconds: 7200, concurrency: 1 } });
  });

  it('sends the changed limits with PUT', async () => {
    let sentMethod = '';
    let sentBody = '';
    const recordingFetch: typeof fetch = (_path, init) => {
      sentMethod = init?.method ?? '';
      sentBody = typeof init?.body === 'string' ? init.body : '';
      return Promise.resolve(new Response(sentBody, { status: 200 }));
    };

    const result = await changeBacktestLimits(recordingFetch, { timeout_seconds: 600, concurrency: 2 });

    expect(sentMethod).toBe('PUT');
    expect(JSON.parse(sentBody)).toEqual({ timeout_seconds: 600, concurrency: 2 });
    expect(result).toEqual({ kind: 'ok', value: { timeout_seconds: 600, concurrency: 2 } });
  });
});
