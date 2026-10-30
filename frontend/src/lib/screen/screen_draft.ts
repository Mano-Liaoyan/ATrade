// The changed, unsaved screen of the screen page (docs/architecture/screen.md section 24.13). The page runs the draft
// at once after each change; the saved screen changes only on "Save screen" or "Save as new screen".
import type { components } from '#lib/api';
import type { IndicatorNames, ScreenDefinition } from './condition_bar';

export type ScreenMarket = 'US' | 'HK';
export type ScreenIndicator = components['schemas']['ScreenIndicatorResponse'];
export type ScreenProblem = components['schemas']['ScreenProblemResponse'];
type Item = Record<string, unknown>;

/** One tag of the condition bar: the start instruments, one filter, one indicator condition, or the order. */
export type ConditionTarget =
  | { part: 'start' }
  | { part: 'filters'; index: number }
  | { part: 'indicator_conditions'; index: number }
  | { part: 'order' };
export type ListPart = 'filters' | 'indicator_conditions';

export type FilterKind = 'last_price' | 'average_trading_value_20' | 'exchange' | 'still_trading';
export type IndicatorConditionKind = 'compare' | 'close_versus_line' | 'rank';
export type ConditionKind = FilterKind | IndicatorConditionKind;

export interface ScreenDraft {
  market: string;
  definition: ScreenDefinition;
}

// The start instruments of each market (section 24.2). The first one is the default and the market switch sets it.
export const START_CHOICES: Record<ScreenMarket, { value: string; label: string }[]> = {
  US: [
    { value: 'quarter_universe', label: 'Quarter universe' },
    { value: 'all_with_daily_bars', label: 'All with daily bars' },
    { value: 'watchlist', label: 'Watchlist' },
  ],
  HK: [
    { value: 'hk_instrument_list', label: 'HK instrument list' },
    { value: 'watchlist', label: 'Watchlist' },
  ],
};
// The exchanges that the exchange filter shows for each market (#145 prototype).
export const MARKET_EXCHANGES: Record<ScreenMarket, string[]> = { US: ['NASDAQ', 'NYSE'], HK: ['SEHK'] };
// The lines of "Close above or below a line" (section 24.4.1): the catalog key and its output.
export const LINE_OUTPUTS: Record<string, string> = { sma: 'value', ema: 'value', donchian_channel: 'upper' };

const FILTER_KINDS: readonly string[] = ['last_price', 'average_trading_value_20', 'exchange', 'still_trading'];

function items(value: unknown): Item[] {
  return Array.isArray(value) ? (value as Item[]) : [];
}

function reference(indicator: string, parameters: Record<string, number>): Item {
  return { indicator, parameters, output: 'value' };
}

/** The new condition of the "Add condition" menu, with the values of the #145 prototype. */
export function newCondition(kind: ConditionKind, market: ScreenMarket): Item {
  switch (kind) {
    case 'still_trading':
      return { field: 'still_trading' };
    case 'last_price':
      return { field: 'last_price', operator: '>=', value: '5' };
    case 'average_trading_value_20':
      return { field: 'average_trading_value_20', operator: '>=', value: '20000000' };
    case 'exchange':
      return { field: 'exchange', values: [...MARKET_EXCHANGES[market]] };
    case 'compare':
      return { kind: 'compare', indicator: reference('rsi', { period: 14 }), operator: '<', value: '30' };
    case 'close_versus_line':
      return { kind: 'close_versus_line', indicator: reference('sma', { period: 200 }), side: 'above' };
    case 'rank':
      return { kind: 'rank', indicator: reference('momentum_12_1', { look_back: 252, skip: 21 }), end: 'top', percent: 20 };
  }
}

export function isFilter(item: Item): boolean {
  return FILTER_KINDS.includes(String(item['field']));
}

export function addCondition(definition: ScreenDefinition, item: Item): ScreenDefinition {
  const key: ListPart = isFilter(item) ? 'filters' : 'indicator_conditions';
  return { ...definition, [key]: [...items(definition[key]), item] };
}

export function readTarget(definition: ScreenDefinition, target: ConditionTarget): Item {
  switch (target.part) {
    case 'start':
      return { start: definition.start };
    case 'order':
      return { ...((definition.order ?? {}) as Item) };
    default:
      return { ...(items(definition[target.part])[target.index] ?? {}) };
  }
}

export function writeTarget(definition: ScreenDefinition, target: ConditionTarget, item: Item): ScreenDefinition {
  switch (target.part) {
    case 'start':
      return { ...definition, start: item['start'] };
    case 'order':
      return { ...definition, order: item };
    default:
      return {
        ...definition,
        [target.part]: items(definition[target.part]).map((old, index) => (index === target.index ? item : old)),
      };
  }
}

export function removeCondition(
  definition: ScreenDefinition,
  target: { part: ListPart; index: number },
): ScreenDefinition {
  return { ...definition, [target.part]: items(definition[target.part]).filter((_, index) => index !== target.index) };
}

/** The reference of a newly selected indicator: its default parameters and its first output (a line: its line). */
export function referenceOf(catalog: ScreenIndicator[], key: string, kind: IndicatorConditionKind | 'order'): Item {
  const indicator = catalog.find((candidate) => candidate.key === key);
  const parameters = Object.fromEntries((indicator?.parameters ?? []).map((parameter) => [parameter.name, parameter.default]));
  const output = kind === 'close_versus_line' ? (LINE_OUTPUTS[key] ?? 'value') : (indicator?.outputs[0] ?? 'value');
  return { indicator: key, parameters, output };
}

function formatParameter(value: unknown): string {
  return typeof value === 'number' || typeof value === 'string' ? String(value) : '';
}

/** The UI name of an indicator reference, as the backend makes it (indicator.md section 23.3), for example RSI(14). */
export function nameIndicator(catalog: ScreenIndicator[], value: unknown): string {
  const indicatorReference = (value ?? {}) as Item;
  const indicator = catalog.find((candidate) => candidate.key === indicatorReference['indicator']);
  if (indicator === undefined) {
    return formatParameter(indicatorReference['indicator']);
  }
  const parameters = (indicatorReference['parameters'] ?? {}) as Item;
  const shown = indicator.parameters
    .filter((parameter) => parameter.is_in_name)
    .map((parameter) => formatParameter(parameters[parameter.name] ?? parameter.default));
  return `${indicator.name}(${shown.join(', ')})`;
}

/** The names of the indicators of a definition that has no screen result yet. */
export function nameDefinitionIndicators(definition: ScreenDefinition, catalog: ScreenIndicator[]): IndicatorNames {
  return {
    indicator_conditions: items(definition.indicator_conditions).map((condition) => nameIndicator(catalog, condition['indicator'])),
    order: nameIndicator(catalog, ((definition.order ?? {}) as Item)['indicator']),
  };
}

/** The key of a target, for example "filters.1". The problems of a 422 answer use the same keys. */
export function targetKey(target: ConditionTarget): string {
  return target.part === 'start' || target.part === 'order' ? target.part : `${target.part}.${String(target.index)}`;
}

function problemKey(location: ScreenProblem['location']): string | null {
  const [root, part, index] = location;
  if (root !== 'definition') {
    return null;
  }
  if (part === 'start' || part === 'order') {
    return part;
  }
  const isListPart = part === 'filters' || part === 'indicator_conditions';
  return isListPart && typeof index === 'number' ? `${part}.${String(index)}` : null;
}

/** Gives each problem of a 422 answer (section 24.6) to the tag at its location. The rest goes to `other`. */
export function groupProblems(problems: ScreenProblem[]): { byTarget: Map<string, string[]>; other: string[] } {
  const byTarget = new Map<string, string[]>();
  const other: string[] = [];
  for (const problem of problems) {
    const key = problemKey(problem.location);
    if (key === null) {
      other.push(problem.message);
    } else {
      byTarget.set(key, [...(byTarget.get(key) ?? []), problem.message]);
    }
  }
  return { byTarget, other };
}

/** The exchanges of one market do not apply to the other market, so the switch removes the exchange filters. */
export function switchMarket(definition: ScreenDefinition, market: ScreenMarket): ScreenDefinition {
  return {
    ...definition,
    start: START_CHOICES[market][0]?.value,
    filters: items(definition.filters).filter((filter) => filter['field'] !== 'exchange'),
  };
}

// PostgreSQL stores the definition as jsonb, which changes the key order. The comparison sorts the keys.
function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([first], [second]) => first.localeCompare(second))
        .map(([key, item]) => [key, sortKeys(item)]),
    );
  }
  return value;
}

export function isDraftChanged(saved: ScreenDraft, draft: ScreenDraft): boolean {
  return (
    saved.market !== draft.market || JSON.stringify(sortKeys(saved.definition)) !== JSON.stringify(sortKeys(draft.definition))
  );
}
