// Bar periods and amounts as the tables show them.
import { describe, expect, it } from 'vite-plus/test';
import { findChangeDirection, formatAmount, formatBarPeriod, formatPrice, formatSignedNumber, formatSignedPercent } from './index';

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

describe('formatSignedNumber', () => {
  it('shows the sign of a change and 2 decimal places', () => {
    expect(formatSignedNumber(1.256)).toBe('+1.26');
    expect(formatSignedNumber(-1234.5)).toBe('-1,234.50');
    expect(formatSignedNumber(0)).toBe('0.00');
  });

  it('shows a dash for a missing value', () => {
    expect(formatSignedNumber(null)).toBe('–');
  });
});

describe('formatSignedPercent', () => {
  it('shows a percent change with the sign rule and a space before the percent sign, on all pages', () => {
    expect(formatSignedPercent(0.974)).toBe('+0.97 %');
    expect(formatSignedPercent(-37.71)).toBe('-37.71 %');
    expect(formatSignedPercent(0)).toBe('0.00 %');
  });

  it('shows a dash for a missing value', () => {
    expect(formatSignedPercent(null)).toBe('–');
  });
});

describe('formatPrice', () => {
  it('shows 2 decimal places and a dash for a missing price', () => {
    expect(formatPrice(1234.5)).toBe('1,234.50');
    expect(formatPrice(null)).toBe('–');
  });
});

describe('findChangeDirection', () => {
  it('finds up, down, and flat', () => {
    expect(findChangeDirection(0.5)).toBe('up');
    expect(findChangeDirection(-0.5)).toBe('down');
    expect(findChangeDirection(0)).toBe('flat');
    expect(findChangeDirection(null)).toBe('flat');
  });
});
