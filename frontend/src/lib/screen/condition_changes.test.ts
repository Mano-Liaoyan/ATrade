// The change marks of the condition card (docs/architecture/assistant.md 25.12.4).
import { describe, expect, it } from 'vite-plus/test';
import { buildConditionGroups, type ScreenDefinition } from './condition_bar';
import { markConditionChanges } from './condition_changes';

const NAMES = { indicator_conditions: ['Momentum(252, 21)', 'SMA(200)'], order: 'Momentum(252, 21)' };
const COUNTS = { start_count: 500, after_filters_count: 371, after_indicator_conditions_count: 58, result_count: 20 };
const SOURCE: ScreenDefinition = {
  start: 'quarter_universe',
  filters: [{ field: 'still_trading' }, { field: 'last_price', operator: '>=', value: '10' }],
  indicator_conditions: [
    { kind: 'rank', end: 'top', percent: 50 },
    { kind: 'close_versus_line', side: 'above' },
  ],
  order: { direction: 'descending', keep_first: 20 },
};
const CHANGED: ScreenDefinition = {
  ...SOURCE,
  filters: [{ field: 'still_trading' }, { field: 'last_price', operator: '>=', value: '20' }],
  indicator_conditions: [
    { kind: 'rank', end: 'top', percent: 50 },
    { kind: 'compare', operator: '<', value: '40' },
  ],
};
const CHANGED_NAMES = { indicator_conditions: ['Momentum(252, 21)', 'Realized volatility(60)'], order: 'Momentum(252, 21)' };

describe('markConditionChanges', () => {
  it('marks a changed value, a removed condition in its old place, and an added condition', () => {
    const groups = markConditionChanges(
      buildConditionGroups(SOURCE, NAMES, null),
      buildConditionGroups(CHANGED, CHANGED_NAMES, COUNTS),
    );

    expect(groups.map((group) => group.count)).toEqual([500, 371, 58, 20]);
    expect(groups.map((group) => group.tags.map((tag) => [tag.change, tag.subject, tag.value, tag.previous?.value ?? null]))).toEqual([
      [['same', 'Quarter universe', '', null]],
      [
        ['same', 'Still trading', '', null],
        ['changed', 'Close', '20', '10'],
      ],
      [
        ['same', 'Momentum(252, 21)', '50%', null],
        ['removed', 'Close', 'SMA(200)', null],
        ['added', 'Realized volatility(60)', '40', null],
      ],
      [['same', 'Momentum(252, 21)', 'first 20', null]],
    ]);
  });

  it('marks a changed start and a changed order as changed values', () => {
    const groups = markConditionChanges(
      buildConditionGroups(SOURCE, NAMES, null),
      buildConditionGroups({ ...SOURCE, start: 'watchlist', order: { direction: 'ascending' } }, NAMES, null),
    );

    expect(groups[0]?.tags).toEqual([
      {
        subject: 'Watchlist',
        operation: '',
        value: '',
        change: 'changed',
        previous: { subject: 'Quarter universe', operation: '', value: '' },
      },
    ]);
    expect(groups[3]?.tags[0]).toMatchObject({ change: 'changed', operation: 'ascending', previous: { operation: 'descending', value: 'first 20' } });
  });

  it('marks nothing without a definition to compare with', () => {
    const groups = markConditionChanges(null, buildConditionGroups(CHANGED, CHANGED_NAMES, COUNTS));

    expect(groups.flatMap((group) => group.tags.map((tag) => tag.change))).toEqual(Array(6).fill('same'));
  });
});
