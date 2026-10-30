import { describe, expect, it } from 'vite-plus/test';
import { addIndicatorCondition, changeComparison, isDraftChanged, removeCondition, switchMarket } from './screen_draft';

const sma = (period: number) => ({ indicator: 'sma', parameters: { period }, output: 'value' });
const definition = {
  start: 'watchlist',
  filters: [
    { field: 'still_trading' },
    { field: 'exchange', values: ['NASDAQ'] },
  ],
  indicator_conditions: [{ kind: 'rank', indicator: sma(2), end: 'top', percent: 10 }],
  order: { indicator: sma(3), direction: 'descending' },
};

describe('screen draft', () => {
  it('adds an indicator condition RSI(14) < 30 at the end', () => {
    expect(addIndicatorCondition(definition).indicator_conditions).toEqual([
      ...definition.indicator_conditions,
      {
        kind: 'compare',
        indicator: { indicator: 'rsi', parameters: { period: 14 }, output: 'value' },
        operator: '<',
        value: '30',
      },
    ]);
  });

  it('changes the operator and the value of one comparison', () => {
    const changed = changeComparison(addIndicatorCondition(definition), 'Indicator conditions', 1, '>=', '70');
    expect(changed.indicator_conditions).toEqual([
      definition.indicator_conditions[0],
      expect.objectContaining({ kind: 'compare', operator: '>=', value: '70' }),
    ]);
  });

  it('removes one filter or one indicator condition and keeps the rest', () => {
    expect(removeCondition(definition, 'Filters', 0).filters).toEqual([{ field: 'exchange', values: ['NASDAQ'] }]);
    expect(removeCondition(definition, 'Indicator conditions', 0).indicator_conditions).toEqual([]);
    expect(definition.filters).toHaveLength(2);
  });

  it('is changed when the definition or the market differs from the saved screen', () => {
    const saved = { market: 'US', definition };
    expect(isDraftChanged(saved, { market: 'US', definition: structuredClone(definition) })).toBe(false);
    expect(isDraftChanged(saved, { market: 'HK', definition })).toBe(true);
    expect(isDraftChanged(saved, { market: 'US', definition: removeCondition(definition, 'Filters', 0) })).toBe(true);
  });

  it('a market switch sets the start instruments of the market and removes the exchange filters', () => {
    expect(switchMarket(definition, 'HK')).toEqual({
      ...definition,
      start: 'hk_instrument_list',
      filters: [{ field: 'still_trading' }],
    });
    expect(switchMarket(definition, 'US').start).toBe('quarter_universe');
  });
});
