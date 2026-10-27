// The bars that the equity chart marks grey: the bars of an interruption of a forward test.
import { describe, expect, it } from 'vitest';
import { findInterruptedTimes } from './interruption_marks';

const curve = ['03:05', '03:06', '03:07', '03:08', '03:09'].map((minute) => ({
  time_utc: `2026-01-02T${minute}:00Z`,
  equity_usd: '10000',
}));

describe('findInterruptedTimes', () => {
  it('marks each bar end after the interruption start up to its end', () => {
    const interruptions = [{ start_utc: '2026-01-02T03:06:00Z', end_utc: '2026-01-02T03:08:00Z' }];

    expect(findInterruptedTimes([curve], interruptions)).toEqual(['2026-01-02T03:07:00Z', '2026-01-02T03:08:00Z']);
  });

  it('marks a bar end of two curves only once and in time order', () => {
    const interruptions = [
      { start_utc: '2026-01-02T03:08:00Z', end_utc: '2026-01-02T03:09:00Z' },
      { start_utc: '2026-01-02T03:04:00Z', end_utc: '2026-01-02T03:05:00Z' },
    ];

    expect(findInterruptedTimes([curve, curve], interruptions)).toEqual([
      '2026-01-02T03:05:00Z',
      '2026-01-02T03:09:00Z',
    ]);
  });

  it('marks nothing without interruptions', () => {
    expect(findInterruptedTimes([curve], [])).toEqual([]);
  });
});
