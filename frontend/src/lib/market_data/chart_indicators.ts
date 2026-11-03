// Pure functions of the indicators on a bar chart (docs/architecture/indicator.md sections 23.9.2 to 23.9.5): the
// legend name, the placement of a new indicator in the panes, its colors, the legend bar, and the "/" shortcut.
// The JSON form of `ChartPane` is the chart indicator set of section 23.9.7.
import type { components } from '#lib/api';
import { CHART_PALETTE_SIZE, formatIndicatorValue, readPaletteColor } from './chart_indicator_styles';
import type { IndicatorSeriesResult } from './indicator_series';

/** One indicator of `GET /api/market-data/indicators`. */
export type ChartIndicatorDefinition = components['schemas']['IndicatorResponse'];
export type ChartLineStyle = 'solid' | 'dashed' | 'dotted';

/** One line of an indicator. `color` is a palette index from 1 to 14. `width` is 1 to 4 pixels. */
export interface ChartIndicatorLine {
  output: string;
  color: number;
  style: ChartLineStyle;
  width: number;
}

/** An indicator on a chart. `parameters` holds all parameters, with the defaults. */
export interface ChartIndicator {
  indicator: string;
  parameters: Record<string, number>;
  hidden: boolean;
  lines: ChartIndicatorLine[];
}

/** The first pane is the price pane. The others are own panes, in the order on the chart. */
export interface ChartPane {
  indicators: ChartIndicator[];
}

/** One value of a legend row, in the color of its line. */
export interface LegendValue {
  text: string;
  color: string;
}

/** A legend row: the legend name and one value for each line. */
export interface LegendRow {
  name: string;
  values: LegendValue[];
}

/** The OHLC row of the price pane legend, as text. */
export interface LegendBar {
  open: string;
  high: string;
  low: string;
  close: string;
}

/** A chart has the price pane and at most this many own panes (section 23.9.3). */
export const MAX_OWN_PANES = 3;
const NEW_LINE_STYLE: ChartLineStyle = 'solid';
const NEW_LINE_WIDTH = 2;

/** The parameters of the indicator with the catalog defaults for the missing ones, in the catalog order. */
export function withDefaults(definition: ChartIndicatorDefinition, parameters: Record<string, number>): Record<string, number> {
  return Object.fromEntries(definition.parameters.map((parameter) => [parameter.name, parameters[parameter.name] ?? parameter.default]));
}

/** "SMA 50", "BB 20 2", "MACD 12 26 9": the short name and the parameters that are in the name. */
export function formatLegendName(definition: ChartIndicatorDefinition, parameters: Record<string, number>): string {
  const values = withDefaults(definition, parameters);
  const shown = definition.parameters.filter((parameter) => parameter.is_in_name).map((parameter) => String(values[parameter.name]));
  return [definition.short_name, ...shown].join(' ');
}

/** The palette colors of all lines of the chart. */
export function listUsedColors(panes: readonly ChartPane[]): number[] {
  return panes.flatMap((pane) => pane.indicators.flatMap((indicator) => indicator.lines.map((line) => line.color)));
}

/**
 * The first `count` palette colors that no line uses, in palette order. When the palette has fewer free colors, the
 * palette starts again with the colors that are used the fewest times.
 */
export function findFreeColors(usedColors: readonly number[], count: number): number[] {
  const useCounts = Array.from({ length: CHART_PALETTE_SIZE }, (_, index) => usedColors.filter((color) => color === index + 1).length);
  const colors: number[] = [];
  for (let line = 0; line < count; line += 1) {
    const fewestUses = Math.min(...useCounts);
    const index = useCounts.indexOf(fewestUses);
    colors.push(index + 1);
    useCounts[index] = fewestUses + 1;
  }
  return colors;
}

/** A new indicator with the catalog defaults: one line for each output, free colors, solid, width 2. */
export function createChartIndicator(definition: ChartIndicatorDefinition, panes: readonly ChartPane[]): ChartIndicator {
  const colors = findFreeColors(listUsedColors(panes), definition.outputs.length);
  return {
    indicator: definition.key,
    parameters: withDefaults(definition, {}),
    hidden: false,
    lines: definition.outputs.map((output, index) => ({
      output,
      color: colors[index] ?? 1,
      style: NEW_LINE_STYLE,
      width: NEW_LINE_WIDTH,
    })),
  };
}

/**
 * Adds a new indicator. A `price` indicator goes on the price pane. An `own` indicator gets a new pane under the others,
 * or goes into the last pane when the chart has 3 own panes. Returns new panes; the old panes do not change.
 */
export function addChartIndicator(panes: readonly ChartPane[], definition: ChartIndicatorDefinition): ChartPane[] {
  const indicator = createChartIndicator(definition, panes);
  const [pricePane = { indicators: [] }, ...ownPanes] = panes;
  if (definition.chart_placement === 'price') {
    return [{ indicators: [...pricePane.indicators, indicator] }, ...ownPanes];
  }
  if (ownPanes.length < MAX_OWN_PANES) {
    return [pricePane, ...ownPanes, { indicators: [indicator] }];
  }
  const lastPane = ownPanes.at(-1) ?? { indicators: [] };
  return [pricePane, ...ownPanes.slice(0, -1), { indicators: [...lastPane.indicators, indicator] }];
}

/**
 * The index in `times` of the bar that the legend shows: the bar of the crosshair, or the last bar with indicator data
 * when `crosshairTime` is null. Null when that bar has no indicator data (a live bar, or no data).
 */
export function findLegendIndex(times: readonly number[], crosshairTime: number | null): number | null {
  if (times.length === 0) {
    return null;
  }
  if (crosshairTime === null) {
    return times.length - 1;
  }
  let low = 0;
  let high = times.length - 1;
  while (low <= high) {
    const middle = (low + high) >>> 1;
    const time = times[middle] ?? 0;
    if (time === crosshairTime) {
      return middle;
    }
    if (time < crosshairTime) {
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return null;
}

interface ShortcutTarget {
  tagName?: string;
  type?: string;
  isContentEditable?: boolean;
}
type ShortcutKeys = Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey'> & { target: ShortcutTarget | EventTarget | null };

// Input types that take no typed text. A "/" there opens the dialog.
const NON_TEXT_INPUT_TYPES = new Set(['button', 'checkbox', 'color', 'file', 'image', 'radio', 'range', 'reset', 'submit']);

function isTextEntry(target: ShortcutTarget): boolean {
  if (target.isContentEditable === true) {
    return true;
  }
  const tagName = target.tagName?.toUpperCase();
  if (tagName === 'TEXTAREA' || tagName === 'SELECT') {
    return true;
  }
  return tagName === 'INPUT' && !NON_TEXT_INPUT_TYPES.has((target.type ?? 'text').toLowerCase());
}

/** True for "/" when the focus is not in a text field, a number field, or the code editor (section 23.9.5). */
export function isAddIndicatorShortcut(keys: ShortcutKeys): boolean {
  if (keys.key !== '/' || keys.ctrlKey || keys.metaKey || keys.altKey) {
    return false;
  }
  return keys.target === null || !isTextEntry(keys.target as ShortcutTarget);
}

type IndicatorSeries = IndicatorSeriesResult['series'][number];

function formatParametersKey(indicator: string, parameters: Record<string, number>): string {
  const entries = Object.entries(parameters).sort(([first], [second]) => first.localeCompare(second));
  return JSON.stringify([indicator, entries]);
}

/** The series of the answer for the indicator: the same key and parameters. Null while the answer has none. */
export function findIndicatorSeries(
  result: IndicatorSeriesResult | null,
  indicator: Pick<ChartIndicator, 'indicator' | 'parameters'> | undefined,
): IndicatorSeries | null {
  if (result === null || indicator === undefined) {
    return null;
  }
  const key = formatParametersKey(indicator.indicator, indicator.parameters);
  return result.series.find((series) => formatParametersKey(series.indicator, series.parameters) === key) ?? null;
}

/**
 * One legend row for each indicator: the legend name and the value of each line at `legendIndex` (an index in
 * `result.times`, see findLegendIndex), in the line color of the light or the dark palette.
 */
export function buildLegendRows(
  indicators: readonly ChartIndicator[],
  catalog: readonly ChartIndicatorDefinition[],
  result: IndicatorSeriesResult | null,
  legendIndex: number | null,
  dark: boolean,
): LegendRow[] {
  return indicators.flatMap((indicator) => {
    const definition = catalog.find((item) => item.key === indicator.indicator);
    if (definition === undefined) {
      return [];
    }
    const series = findIndicatorSeries(result, indicator);
    return [
      {
        name: formatLegendName(definition, indicator.parameters),
        values: indicator.lines.map((line) => {
          const value = legendIndex === null ? null : (series?.outputs[line.output]?.[legendIndex] ?? null);
          return { text: formatIndicatorValue(indicator.indicator, value), color: readPaletteColor(line.color, dark) };
        }),
      },
    ];
  });
}
