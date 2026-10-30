import { describe, expect, it } from 'vite-plus/test';
import {
  addCondition,
  groupProblems,
  isDraftChanged,
  nameDefinitionIndicators,
  newCondition,
  readTarget,
  referenceOf,
  removeCondition,
  switchMarket,
  writeTarget,
  type ScreenIndicator,
} from './screen_draft';

const sma = (period: number) => ({ indicator: 'sma', parameters: { period }, output: 'value' });
const definition = {
  start: 'watchlist',
  filters: [{ field: 'still_trading' }, { field: 'exchange', values: ['NASDAQ'] }],
  indicator_conditions: [{ kind: 'rank', indicator: sma(2), end: 'top', percent: 10 }],
  order: { indicator: sma(3), direction: 'descending' },
};

const period = (defaultValue: number) => ({
  name: 'period',
  value_type: 'int' as const,
  default: defaultValue,
  minimum: 1,
  maximum: 1000,
  is_in_name: true,
});
const CATALOG: ScreenIndicator[] = [
  { key: 'sma', name: 'SMA', parameters: [period(50)], outputs: ['value'] },
  { key: 'rsi', name: 'RSI', parameters: [period(14)], outputs: ['value'] },
  {
    key: 'bollinger_bands',
    name: 'Bollinger Bands',
    parameters: [period(20), { name: 'k', value_type: 'float', default: 2, minimum: 0.1, maximum: 10, is_in_name: true }],
    outputs: ['upper', 'middle', 'lower'],
  },
  { key: 'donchian_channel', name: 'Donchian channel', parameters: [period(20)], outputs: ['upper', 'middle', 'lower'] },
];

describe('screen draft', () => {
  it('adds a new filter to the filters and a new indicator condition to the indicator conditions', () => {
    const withClose = addCondition(definition, newCondition('last_price', 'US'));
    expect(withClose.filters).toEqual([...definition.filters, { field: 'last_price', operator: '>=', value: '5' }]);

    const withRsi = addCondition(definition, newCondition('compare', 'US'));
    expect(withRsi.indicator_conditions).toEqual([
      ...definition.indicator_conditions,
      { kind: 'compare', indicator: { indicator: 'rsi', parameters: { period: 14 }, output: 'value' }, operator: '<', value: '30' },
    ]);
  });

  it('a new exchange filter selects all exchanges of the market', () => {
    expect(newCondition('exchange', 'US')).toEqual({ field: 'exchange', values: ['NASDAQ', 'NYSE'] });
    expect(newCondition('exchange', 'HK')).toEqual({ field: 'exchange', values: ['SEHK'] });
  });

  it('reads and writes each part of the definition and keeps the other parts', () => {
    expect(readTarget(definition, { part: 'start' })).toEqual({ start: 'watchlist' });
    expect(readTarget(definition, { part: 'filters', index: 1 })).toEqual({ field: 'exchange', values: ['NASDAQ'] });

    const order = { indicator: sma(5), direction: 'ascending', keep_first: 10 };
    const changed = writeTarget(writeTarget(definition, { part: 'order' }, order), { part: 'start' }, { start: 'all_with_daily_bars' });
    expect(changed).toEqual({ ...definition, start: 'all_with_daily_bars', order });

    const rank = { kind: 'rank', indicator: sma(9), end: 'bottom', percent: 30 };
    expect(writeTarget(definition, { part: 'indicator_conditions', index: 0 }, rank).indicator_conditions).toEqual([rank]);
    expect(definition.indicator_conditions[0]?.percent).toBe(10);
  });

  it('removes one filter or one indicator condition and keeps the rest', () => {
    expect(removeCondition(definition, { part: 'filters', index: 0 }).filters).toEqual([{ field: 'exchange', values: ['NASDAQ'] }]);
    expect(removeCondition(definition, { part: 'indicator_conditions', index: 0 }).indicator_conditions).toEqual([]);
    expect(definition.filters).toHaveLength(2);
  });

  it('a new indicator gets its default parameters and its first output, and a line gets the Donchian upper line', () => {
    expect(referenceOf(CATALOG, 'bollinger_bands', 'compare')).toEqual({
      indicator: 'bollinger_bands',
      parameters: { period: 20, k: 2 },
      output: 'upper',
    });
    expect(referenceOf(CATALOG, 'donchian_channel', 'close_versus_line').output).toBe('upper');
  });

  it('names the indicators of a changed definition as the screen result does', () => {
    const changed = {
      ...definition,
      indicator_conditions: [
        { kind: 'compare', indicator: { indicator: 'bollinger_bands', parameters: { k: 2.5 }, output: 'lower' }, operator: '<', value: '1' },
      ],
    };
    expect(nameDefinitionIndicators(changed, CATALOG)).toEqual({
      indicator_conditions: ['Bollinger Bands(20, 2.5)'],
      order: 'SMA(3)',
    });
  });

  it('gives each problem of a 422 answer to the condition at its location', () => {
    const grouped = groupProblems([
      { location: ['definition', 'filters', 1, 'values'], message: 'The values must be a list of 1 or more exchanges.' },
      { location: ['definition', 'indicator_conditions', 0, 'indicator', 'parameters', 'period'], message: 'Too long.' },
      { location: ['definition', 'order', 'keep_first'], message: 'Too many.' },
      { location: ['definition', 'start'], message: 'Wrong market.' },
      { location: ['name'], message: 'A screen with the name exists.' },
    ]);
    expect(Object.fromEntries(grouped.byTarget)).toEqual({
      'filters.1': ['The values must be a list of 1 or more exchanges.'],
      'indicator_conditions.0': ['Too long.'],
      order: ['Too many.'],
      start: ['Wrong market.'],
    });
    expect(grouped.other).toEqual(['A screen with the name exists.']);
  });

  it('is not changed when only the key order differs, as in a definition that PostgreSQL stored', () => {
    const stored = {
      order: { direction: 'descending', indicator: { output: 'value', indicator: 'sma', parameters: { period: 3 } } },
      start: 'watchlist',
      filters: [{ values: ['NASDAQ'], field: 'exchange' }],
      indicator_conditions: [],
    };
    const shown = {
      start: 'watchlist',
      filters: [{ field: 'exchange', values: ['NASDAQ'] }],
      indicator_conditions: [],
      order: { indicator: sma(3), direction: 'descending' },
    };
    expect(isDraftChanged({ market: 'US', definition: stored }, { market: 'US', definition: shown })).toBe(false);
  });

  it('is changed when the definition or the market differs from the saved screen', () => {
    const saved = { market: 'US', definition };
    expect(isDraftChanged(saved, { market: 'US', definition: structuredClone(definition) })).toBe(false);
    expect(isDraftChanged(saved, { market: 'HK', definition })).toBe(true);
    expect(isDraftChanged(saved, { market: 'US', definition: removeCondition(definition, { part: 'filters', index: 0 }) })).toBe(
      true,
    );
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
