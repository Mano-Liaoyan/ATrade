// Bar periods and amounts as the tables show them.
import { describe, expect, it } from 'vite-plus/test';
import { formatAmount, formatBarPeriod } from './index';

describe('formatBarPeriod', () => {
  it.each([
    ['1-SECOND', '1 sec'],
    ['1-MINUTE', '1 min'],
    ['15-MINUTE', '15 min'],
    ['1-HOUR', '1 hour'],
    ['2-HOUR', '2 hours'],
    ['1-DAY', '1 day'],
    ['1-WEEK', '1 week'],
    ['1-MONTH', '1 month'],
  ])('shows %s as %s', (barPeriod, text) => {
    expect(formatBarPeriod(barPeriod)).toBe(text);
  });

  it('keeps an unknown value', () => {
    expect(formatBarPeriod('1-TICK')).toBe('1-TICK');
    expect(formatBarPeriod('daily')).toBe('daily');
  });
});

describe('formatAmount', () => {
  it('adds thousands separators and 2 decimal places', () => {
    expect(formatAmount('98765.4')).toBe('98,765.40');
    expect(formatAmount('1234567')).toBe('1,234,567.00');
    expect(formatAmount('-5.125')).toBe('-5.13');
  });
});
