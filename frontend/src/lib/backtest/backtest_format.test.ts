// Labels and values that the backtest pages show.
import { describe, expect, it } from 'vitest';
import { convertDateToUtcStart, describeBacktestStatus, formatPercent, isFinalStatus } from './index';

describe('describeBacktestStatus', () => {
  it('names each status in words', () => {
    expect(describeBacktestStatus('queued')).toBe('Queued');
    expect(describeBacktestStatus('running')).toBe('Running');
    expect(describeBacktestStatus('finished')).toBe('Finished');
    expect(describeBacktestStatus('failed')).toBe('Failed');
    expect(describeBacktestStatus('timed_out')).toBe('Timed out');
  });
});

describe('isFinalStatus', () => {
  it('is true only when the backtest status cannot change again', () => {
    expect(isFinalStatus('queued')).toBe(false);
    expect(isFinalStatus('running')).toBe(false);
    expect(isFinalStatus('finished')).toBe(true);
    expect(isFinalStatus('failed')).toBe(true);
    expect(isFinalStatus('timed_out')).toBe(true);
  });
});

describe('convertDateToUtcStart', () => {
  it('turns a date of the date input into the start of that day in UTC', () => {
    expect(convertDateToUtcStart('2025-01-31')).toBe('2025-01-31T00:00:00Z');
  });
});

describe('formatPercent', () => {
  it('shows the sign and 2 decimal places', () => {
    expect(formatPercent('1.6')).toBe('+1.60 %');
    expect(formatPercent('-1.02')).toBe('-1.02 %');
    expect(formatPercent('0')).toBe('0.00 %');
  });
});
