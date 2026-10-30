// The 4 groups of the condition bar (docs/architecture/screen.md section 24.10.1). Each condition is a tag with 3
// text parts: the subject, the operation, and the value. Each group ends with its funnel count.

/** The definition JSON of a screen (screen.md section 24.4.1), read loosely: the backend checks it. */
export interface ScreenDefinition {
  start?: unknown;
  filters?: unknown;
  indicator_conditions?: unknown;
  order?: unknown;
}

/** The UI names of the indicators of the definition (the `indicator_names` of the screen result answer). */
export interface IndicatorNames {
  indicator_conditions: string[];
  order: string;
}

export interface FunnelCounts {
  start_count: number;
  after_filters_count: number;
  after_indicator_conditions_count: number;
  result_count: number;
}

export interface ConditionTag {
  subject: string;
  operation: string;
  value: string;
}

export interface ConditionGroup {
  label: string;
  tags: ConditionTag[];
  count: number;
}

type Item = Record<string, unknown>;

const START_NAMES: Record<string, string> = {
  quarter_universe: 'Quarter universe',
  all_with_daily_bars: 'All with daily bars',
  watchlist: 'Watchlist',
  hk_instrument_list: 'HK instrument list',
};
const OPERATORS: Record<string, string> = { '<': '<', '<=': '≤', '>': '>', '>=': '≥' };
const NUMBER_FORMAT = new Intl.NumberFormat('en-US', { maximumFractionDigits: 6 });

function readItems(value: unknown): Item[] {
  return Array.isArray(value) ? (value as Item[]) : [];
}

function text(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

function formatNumber(value: unknown): string {
  const number = Number(value);
  return Number.isFinite(number) ? NUMBER_FORMAT.format(number) : text(value);
}

function describeFilter(filter: Item): ConditionTag {
  const operation = OPERATORS[text(filter['operator'])] ?? '';
  switch (filter['field']) {
    case 'still_trading':
      return { subject: 'Still trading', operation: '', value: '' };
    case 'exchange':
      return { subject: 'Exchange', operation: 'in', value: readItems(filter['values']).map(text).join(', ') };
    case 'last_price':
      return { subject: 'Close', operation, value: formatNumber(filter['value']) };
    default:
      return { subject: 'Avg trading value (20)', operation, value: formatNumber(filter['value']) };
  }
}

function describeCondition(condition: Item, name: string): ConditionTag {
  switch (condition['kind']) {
    case 'close_versus_line':
      return { subject: 'Close', operation: text(condition['side']), value: name };
    case 'rank':
      return { subject: name, operation: text(condition['end']), value: `${text(condition['percent'])}%` };
    default:
      return {
        subject: name,
        operation: OPERATORS[text(condition['operator'])] ?? '',
        value: formatNumber(condition['value']),
      };
  }
}

function describeOrder(order: Item, name: string): ConditionTag {
  const keepFirst = order['keep_first'];
  return {
    subject: name,
    operation: text(order['direction']),
    value: typeof keepFirst === 'number' ? `first ${String(keepFirst)}` : '',
  };
}

export function buildConditionGroups(
  definition: ScreenDefinition,
  indicatorNames: IndicatorNames,
  counts: FunnelCounts,
): ConditionGroup[] {
  const start = text(definition.start);
  const order = (definition.order ?? {}) as Item;
  return [
    {
      label: 'Start instruments',
      tags: [{ subject: START_NAMES[start] ?? start, operation: '', value: '' }],
      count: counts.start_count,
    },
    { label: 'Filters', tags: readItems(definition.filters).map(describeFilter), count: counts.after_filters_count },
    {
      label: 'Indicator conditions',
      tags: readItems(definition.indicator_conditions).map((condition, index) =>
        describeCondition(condition, indicatorNames.indicator_conditions[index] ?? ''),
      ),
      count: counts.after_indicator_conditions_count,
    },
    { label: 'Order', tags: [describeOrder(order, indicatorNames.order)], count: counts.result_count },
  ];
}
