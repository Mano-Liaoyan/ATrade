// The events of the Logs tab of the forward test page.
import { describe, expect, it } from 'vite-plus/test';
import type { ForwardTest } from './forward_test_api';
import { listForwardTestEvents } from './forward_test_events';

const forwardTest: ForwardTest = {
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

describe('listForwardTestEvents', () => {
  it('lists only the start of a new forward test', () => {
    expect(listForwardTestEvents(forwardTest)).toEqual([{ timeUtc: '2026-01-02T03:04:05Z', text: 'Started' }]);
  });

  it('lists the interruptions and the stop, oldest first', () => {
    const events = listForwardTestEvents({
      ...forwardTest,
      status: 'stopped',
      stopped_at_utc: '2026-01-05T00:00:00Z',
      end_time_utc: '2026-01-09T00:00:00Z',
      interruptions: [
        { reason: 'worker_restart', started_at_utc: '2026-01-04T00:00:00Z', ended_at_utc: null },
        { reason: 'gateway', started_at_utc: '2026-01-03T00:00:00Z', ended_at_utc: '2026-01-03T01:00:00Z' },
      ],
    });

    expect(events).toEqual([
      { timeUtc: '2026-01-02T03:04:05Z', text: 'Started' },
      { timeUtc: '2026-01-03T00:00:00Z', text: 'Interrupted: IB Gateway not reachable' },
      { timeUtc: '2026-01-03T01:00:00Z', text: 'Continued' },
      { timeUtc: '2026-01-04T00:00:00Z', text: 'Interrupted: Worker restart' },
      { timeUtc: '2026-01-05T00:00:00Z', text: 'Stopped' },
    ]);
  });

  it('lists the end time of a forward test that is not stopped as the planned stop', () => {
    const events = listForwardTestEvents({ ...forwardTest, end_time_utc: '2026-01-09T00:00:00Z' });

    expect(events.at(-1)).toEqual({ timeUtc: '2026-01-09T00:00:00Z', text: 'Planned stop' });
  });
});
