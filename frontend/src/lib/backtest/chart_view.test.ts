import { describe, expect, it } from 'vite-plus/test';
import { formatChartViewSearch, readChartView } from './chart_view';

describe('readChartView', () => {
  it('reads "bars" from ?chart=bars and gives "equity" for each other value', () => {
    expect(readChartView(new URLSearchParams('chart=bars'))).toBe('bars');
    expect(readChartView(new URLSearchParams('chart=other'))).toBe('equity');
    expect(readChartView(new URLSearchParams(''))).toBe('equity');
  });
});

describe('formatChartViewSearch', () => {
  it('keeps the other search parameters and removes chart for "equity"', () => {
    expect(formatChartViewSearch(new URLSearchParams('a=1'), 'bars')).toBe('?a=1&chart=bars');
    expect(formatChartViewSearch(new URLSearchParams('chart=bars&a=1'), 'equity')).toBe('?a=1');
    expect(formatChartViewSearch(new URLSearchParams('chart=bars'), 'equity')).toBe('');
  });
});
