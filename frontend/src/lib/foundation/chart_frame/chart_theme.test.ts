// The price scale labels of all charts use the number formats of the tables and the metric tiles.
import { describe, expect, it } from 'vite-plus/test';
import { CHART_PERCENT_FORMAT, CHART_PRICE_FORMAT } from './chart_theme';

describe('CHART_PRICE_FORMAT', () => {
  it('shows a price with thousands separators and 2 decimals, like the tables', () => {
    expect(CHART_PRICE_FORMAT.formatter(11000)).toBe('11,000.00');
    expect(CHART_PRICE_FORMAT.formatter(105.256)).toBe('105.26');
  });
});

describe('CHART_PERCENT_FORMAT', () => {
  it('shows a percent with the one sign rule and a space before the percent sign, like the max drawdown tile', () => {
    expect(CHART_PERCENT_FORMAT.formatter(-37.712)).toBe('-37.71 %');
    expect(CHART_PERCENT_FORMAT.formatter(1.5)).toBe('+1.50 %');
  });

  it('shows no sign for zero and for a value that rounds to zero', () => {
    expect(CHART_PERCENT_FORMAT.formatter(-0)).toBe('0.00 %');
    expect(CHART_PERCENT_FORMAT.formatter(-0.001)).toBe('0.00 %');
  });
});
