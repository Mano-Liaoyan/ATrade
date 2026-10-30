// The columns, the sort, and the exclusion reasons of the screen result tables (screen.md section 24.10.2).
import type { components } from '#lib/api';
import type { IndicatorNames, ScreenDefinition } from './condition_bar';

export type ScreenResultRow = components['schemas']['ScreenResultRowResponse'];
export type SortDirection = 'ascending' | 'descending';

export interface ResultColumn {
  key: string;
  header: string;
  isNumber: boolean;
  /** The sort value. Null: the row has no value. */
  read: (row: ScreenResultRow) => number | string | null;
}

const DEFAULT_COLUMNS: ResultColumn[] = [
  { key: 'position', header: '#', isNumber: true, read: (row) => row.position },
  { key: 'symbol', header: 'Symbol', isNumber: false, read: (row) => row.symbol },
  { key: 'exchange', header: 'Exchange', isNumber: false, read: (row) => row.exchange },
  { key: 'close', header: 'Close', isNumber: true, read: (row) => Number(row.last_price) },
  {
    key: 'average-trading-value',
    header: 'Avg trading value (20)',
    isNumber: true,
    read: (row) => row.average_trading_value_20,
  },
];

/** The default columns, one column for each indicator of a condition or of the order, and one Percentile column for
 * each rank condition. */
export function listResultColumns(definition: ScreenDefinition, indicatorNames: IndicatorNames): ResultColumn[] {
  const conditions = Array.isArray(definition.indicator_conditions)
    ? (definition.indicator_conditions as Record<string, unknown>[])
    : [];
  const indicators = [...new Set([...indicatorNames.indicator_conditions, indicatorNames.order])];
  const rankNames = conditions
    .map((condition, index) => (condition['kind'] === 'rank' ? indicatorNames.indicator_conditions[index] : undefined))
    .filter((name): name is string => name !== undefined);
  return [
    ...DEFAULT_COLUMNS,
    ...indicators.map((name) => ({
      key: `indicator:${name}`,
      header: name,
      isNumber: true,
      read: (row: ScreenResultRow) => row.indicator_values[name] ?? null,
    })),
    ...[...new Set(rankNames)].map((name, _index, names) => ({
      key: `percentile:${name}`,
      header: names.length === 1 ? 'Percentile' : `Percentile ${name}`,
      isNumber: true,
      read: (row: ScreenResultRow) => row.percentiles[name] ?? null,
    })),
  ];
}

/** A sorted copy. The rows without a value come last in both directions. */
export function sortResultRows(
  rows: readonly ScreenResultRow[],
  column: ResultColumn,
  direction: SortDirection,
): ScreenResultRow[] {
  const sign = direction === 'ascending' ? 1 : -1;
  return [...rows].sort((first, second) => {
    const firstValue = column.read(first);
    const secondValue = column.read(second);
    if (firstValue === null || secondValue === null) {
      return (firstValue === null ? 1 : 0) - (secondValue === null ? 1 : 0);
    }
    if (typeof firstValue === 'number' && typeof secondValue === 'number') {
      return sign * (firstValue - secondValue);
    }
    return sign * String(firstValue).localeCompare(String(secondValue));
  });
}

/** "filters[0]: Close > 15" gives "Close > 15". "No value: RSI(14)" and "No daily bars" stay. */
export function describeExclusionReason(reason: string): string {
  return reason.replace(/^[a-z_]+\[\d+\]: /, '');
}
