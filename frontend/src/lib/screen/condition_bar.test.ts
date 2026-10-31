// The 4 groups of the condition bar (docs/architecture/screen.md section 24.10.1).
import { describe, expect, it } from 'vite-plus/test';
import { buildConditionGroups } from './condition_bar';

const SUMMARY = { start_count: 500, after_filters_count: 320, after_indicator_conditions_count: 41, result_count: 20 };

describe('buildConditionGroups', () => {
  it('gives the 4 groups in order, each with its funnel count and 3-part tags', () => {
    const groups = buildConditionGroups(
      {
        start: 'quarter_universe',
        filters: [
          { field: 'still_trading' },
          { field: 'last_price', operator: '>', value: '5' },
          { field: 'average_trading_value_20', operator: '>=', value: '5000000' },
          { field: 'exchange', values: ['NASDAQ', 'NYSE'] },
        ],
        indicator_conditions: [
          { kind: 'compare', operator: '<', value: '30' },
          { kind: 'close_versus_line', side: 'above' },
          { kind: 'rank', end: 'top', percent: 20 },
        ],
        order: { direction: 'descending', keep_first: 20 },
      },
      { indicator_conditions: ['RSI(14)', 'SMA(200)', 'Momentum(252, 21)'], order: 'Momentum(252, 21)' },
      SUMMARY,
    );

    expect(groups.map((group) => [group.label, group.count])).toEqual([
      ['Start instruments', 500],
      ['Filters', 320],
      ['Indicator conditions', 41],
      ['Order', 20],
    ]);
    expect(groups.map((group) => group.tags)).toEqual([
      [{ subject: 'Quarter universe', operation: '', value: '' }],
      [
        { subject: 'Still trading', operation: '', value: '' },
        { subject: 'Close', operation: '>', value: '5' },
        { subject: 'Avg trading value (20)', operation: '≥', value: '5,000,000' },
        { subject: 'Exchange', operation: 'in', value: 'NASDAQ, NYSE' },
      ],
      [
        { subject: 'RSI(14)', operation: '<', value: '30' },
        { subject: 'Close', operation: 'above', value: 'SMA(200)' },
        { subject: 'Momentum(252, 21)', operation: 'top', value: '20%' },
      ],
      [{ subject: 'Momentum(252, 21)', operation: 'descending', value: 'first 20' }],
    ]);
  });

  it('names each start and leaves the order value empty without keep_first', () => {
    const names = ['all_with_daily_bars', 'watchlist', 'hk_instrument_list'].map(
      (start) =>
        buildConditionGroups(
          { start, filters: [], indicator_conditions: [], order: { direction: 'ascending' } },
          { indicator_conditions: [], order: 'SMA(50)' },
          SUMMARY,
        )[0]?.tags[0]?.subject,
    );
    const order = buildConditionGroups(
      { start: 'watchlist', filters: [], indicator_conditions: [], order: { direction: 'ascending' } },
      { indicator_conditions: [], order: 'SMA(50)' },
      SUMMARY,
    )[3]?.tags[0];

    expect(names).toEqual(['All with daily bars', 'Watchlist', 'HK instrument list']);
    expect(order).toEqual({ subject: 'SMA(50)', operation: 'ascending', value: '' });
  });

  it('has no funnel counts for a changed definition that has no screen result', () => {
    const groups = buildConditionGroups(
      { start: 'watchlist', filters: [], indicator_conditions: [], order: { direction: 'ascending' } },
      { indicator_conditions: [], order: 'SMA(50)' },
      null,
    );

    expect(groups.map((group) => group.count)).toEqual([null, null, null, null]);
  });
});
