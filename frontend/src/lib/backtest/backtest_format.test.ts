// Labels and values that the backtest pages show.
import { describe, expect, it } from 'vitest';
import {
  convertDateToUtcStart,
  convertTimeoutMinutesToSeconds,
  describeBacktestStatus,
  formatPercent,
  formatTimeoutMinutes,
  isFinalStatus,
} from './index';

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

describe('formatTimeoutMinutes', () => {
  it('shows the stored timeout in minutes', () => {
    expect(formatTimeoutMinutes(7200)).toBe('120');
    expect(formatTimeoutMinutes(90)).toBe('1.5');
  });
});

describe('convertTimeoutMinutesToSeconds', () => {
  it('converts whole minutes to seconds', () => {
    expect(convertTimeoutMinutesToSeconds('120')).toBe(7200);
    expect(convertTimeoutMinutesToSeconds(' 5 ')).toBe(300);
  });

  it('is null for a value that is not a whole number of minutes above 0', () => {
    expect(convertTimeoutMinutesToSeconds('0')).toBeNull();
    expect(convertTimeoutMinutesToSeconds('1.5')).toBeNull();
    expect(convertTimeoutMinutesToSeconds('')).toBeNull();
    expect(convertTimeoutMinutesToSeconds('ten')).toBeNull();
  });
});
