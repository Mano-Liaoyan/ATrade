// Forward test HTTP calls, the socket message, and the labels.
import { describe, expect, it } from 'vitest';
import {
  canBacktestSamePeriod,
  canStop,
  describeForwardTestStatus,
  formatLocalTime,
  isLiveBarPeriod,
  readEndTimeUtc,
  readForwardTestComparison,
  readForwardTestsMessage,
  startForwardTest,
  startSamePeriodBacktest,
  stopForwardTest,
  type ForwardTest,
  type ForwardTestRequest,
} from './forward_test_api';

const request: ForwardTestRequest = {
  strategy_version_id: 2,
  symbol: 'AAPL',
  exchange: 'NASDAQ',
  currency: 'USD',
  bar_period: '1-MINUTE',
};

const runningForwardTest: ForwardTest = {
  id: 3,
  strategy_version_id: 2,
  strategy_id: 1,
  strategy_name: 'Trend',
  version_number: 2,
  symbol: 'AAPL',
  exchange: 'NASDAQ',
  currency: 'USD',
  bar_period: '1-MINUTE',
  desired_state: 'running',
  status: 'running',
  client_id: 10,
  start_balance_usd: '100000.00',
  error_message: null,
  created_at_utc: '2026-01-02T03:04:05Z',
  stopped_at_utc: null,
  end_time_utc: null,
  crash_count: 0,
  interruptions: [],
};

function makeFetch(status: number, body: unknown, requests: Request[] = []): typeof fetch {
  return (input, init) => {
    requests.push(new Request(new URL(input as string, 'http://test'), init));
    return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }));
  };
}

describe('startForwardTest', () => {
  it('posts the request and returns the new forward test', async () => {
    const requests: Request[] = [];

    const result = await startForwardTest(makeFetch(201, runningForwardTest, requests), request);

    expect(result).toEqual({ kind: 'started', forwardTest: runningForwardTest });
    expect(requests[0]?.method).toBe('POST');
    expect(await requests[0]?.json()).toEqual(request);
  });

  it('shows the limit of running forward tests', async () => {
    const body = { detail: 'limit of running forward tests reached', forward_test_id: null };

    const result = await startForwardTest(makeFetch(409, body), request);

    expect(result).toEqual({ kind: 'failed', message: 'limit of running forward tests reached' });
  });

  it('shows the first field error', async () => {
    const body = { detail: [{ loc: ['body', 'bar_period'], msg: 'Input should be 1-MINUTE', type: 'enum' }] };

    const result = await startForwardTest(makeFetch(422, body), request);

    expect(result).toEqual({ kind: 'failed', message: 'bar_period: Input should be 1-MINUTE' });
  });
});

describe('stopForwardTest', () => {
  it('posts the stop request', async () => {
    const requests: Request[] = [];

    const result = await stopForwardTest(makeFetch(202, null, requests), 3);

    expect(result).toEqual({ kind: 'stop_requested' });
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/forward-tests/3/stop');
  });

  it('reports an unreachable backend', async () => {
    const result = await stopForwardTest(() => Promise.reject(new TypeError('offline')), 3);

    expect(result.kind).toBe('failed');
  });
});

describe('readForwardTestsMessage', () => {
  it('reads the forward tests message', () => {
    expect(readForwardTestsMessage({ type: 'forward_tests', forward_tests: [runningForwardTest] })).toEqual([
      runningForwardTest,
    ]);
  });

  it('ignores other messages', () => {
    expect(readForwardTestsMessage({ type: 'orders', orders: [] })).toBeNull();
  });
});

describe('labels', () => {
  it('allows only the bar periods of IB live bars', () => {
    expect(isLiveBarPeriod('1-MINUTE')).toBe(true);
    expect(isLiveBarPeriod('1-DAY')).toBe(true);
  });

  it('describes the statuses, with the wait for IB Gateway and the failures', () => {
    expect(describeForwardTestStatus('waiting_for_gateway')).toBe('Waiting for IB Gateway');
    expect(describeForwardTestStatus('stop_failed')).toBe('Stop failed');
    expect(describeForwardTestStatus('failed')).toBe('Failed');
  });

  it('offers a stop only while the forward test runs and holds a client ID', () => {
    expect(canStop(runningForwardTest)).toBe(true);
    expect(canStop({ ...runningForwardTest, desired_state: 'stopped' })).toBe(false);
    expect(canStop({ ...runningForwardTest, status: 'failed', client_id: null })).toBe(false);
  });
});

describe('canBacktestSamePeriod', () => {
  it('needs the start balance, because the backtest uses it as the paper capital', () => {
    expect(canBacktestSamePeriod(runningForwardTest)).toBe(true);
    expect(canBacktestSamePeriod({ ...runningForwardTest, start_balance_usd: null })).toBe(false);
  });
});

describe('startSamePeriodBacktest', () => {
  it('posts to the forward test and returns the new backtest ID', async () => {
    const requests: Request[] = [];

    const result = await startSamePeriodBacktest(makeFetch(201, { backtest_id: 7 }, requests), 3);

    expect(result).toEqual({ kind: 'started', backtestId: 7 });
    expect(requests[0]?.method).toBe('POST');
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/forward-tests/3/same-period-backtests');
  });

  it('shows why the backtest was refused', async () => {
    const detail = 'A backtest supports only USD instruments. The instrument currency is EUR.';

    const result = await startSamePeriodBacktest(makeFetch(422, { detail }), 3);

    expect(result).toEqual({ kind: 'failed', message: detail });
  });
});

describe('readForwardTestComparison', () => {
  it('reads the comparison of the forward test with the backtest', async () => {
    const requests: Request[] = [];
    const comparison = { forward_test: runningForwardTest, fills: [], interruptions: [] };

    const result = await readForwardTestComparison(makeFetch(200, comparison, requests), 3, 7);

    expect(result).toEqual({ kind: 'ok', value: comparison });
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/forward-tests/3/comparison/7');
  });

  it('shows why the comparison is not possible', async () => {
    const detail = 'Backtest not found.';

    const result = await readForwardTestComparison(makeFetch(404, { detail }), 3, 7);

    expect(result).toEqual({ kind: 'failed', message: detail });
  });
});

describe('the end time', () => {
  it('turns the local time of the input into UTC', () => {
    expect(readEndTimeUtc('2026-01-03T09:30')).toBe(new Date(2026, 0, 3, 9, 30).toISOString());
  });

  it('is null when the input is empty or not a time', () => {
    expect(readEndTimeUtc('')).toBeNull();
    expect(readEndTimeUtc('not a time')).toBeNull();
  });

  it('shows a UTC time in the local time zone', () => {
    expect(formatLocalTime(new Date(2026, 0, 3, 9, 30).toISOString())).toBe('2026-01-03 09:30');
    expect(formatLocalTime(null)).toBe('');
  });
});
