import { describe, expect, it } from 'vite-plus/test';
import {
  addChartIndicator,
  findFreeColors,
  buildLegendRows,
  findIndicatorSeries,
  findLegendIndex,
  formatLegendName,
  isAddIndicatorShortcut,
  type ChartIndicatorDefinition,
  type ChartPane,
} from './chart_indicators';
import type { IndicatorSeriesResult } from './indicator_series';

function period(defaultValue: number): ChartIndicatorDefinition['parameters'][number] {
  return { name: 'period', value_type: 'int', default: defaultValue, minimum: 1, maximum: 1000, is_in_name: true };
}

const SMA: ChartIndicatorDefinition = {
  key: 'sma',
  name: 'SMA',
  short_name: 'SMA',
  chart_placement: 'price',
  parameters: [period(50)],
  outputs: ['value'],
};
const BOLLINGER_BANDS: ChartIndicatorDefinition = {
  key: 'bollinger_bands',
  name: 'Bollinger Bands',
  short_name: 'BB',
  chart_placement: 'price',
  parameters: [period(20), { name: 'k', value_type: 'float', default: 2, minimum: 0.1, maximum: 10, is_in_name: true }],
  outputs: ['upper', 'middle', 'lower'],
};
const MACD: ChartIndicatorDefinition = {
  key: 'macd',
  name: 'MACD',
  short_name: 'MACD',
  chart_placement: 'own',
  parameters: [
    { ...period(12), name: 'fast_period' },
    { ...period(26), name: 'slow_period' },
    { ...period(9), name: 'signal_period' },
  ],
  outputs: ['value', 'signal', 'histogram'],
};
const REALIZED_VOLATILITY: ChartIndicatorDefinition = {
  key: 'realized_volatility',
  name: 'Realized volatility',
  short_name: 'RV',
  chart_placement: 'own',
  parameters: [period(60), { name: 'bars_per_year', value_type: 'int', default: 252, minimum: 1, maximum: 10000, is_in_name: false }],
  outputs: ['value'],
};
const RSI: ChartIndicatorDefinition = { ...SMA, key: 'rsi', name: 'RSI', short_name: 'RSI', chart_placement: 'own', parameters: [period(14)] };

const EMPTY_CHART: ChartPane[] = [{ indicators: [] }];

describe('chart indicators', () => {
  it('names a legend row with the short name and the parameters that are in the name', () => {
    expect(formatLegendName(SMA, { period: 50 })).toBe('SMA 50');
    expect(formatLegendName(BOLLINGER_BANDS, { period: 20, k: 2 })).toBe('BB 20 2');
    expect(formatLegendName(BOLLINGER_BANDS, { period: 20, k: 2.5 })).toBe('BB 20 2.5');
    expect(formatLegendName(MACD, { fast_period: 12, slow_period: 26, signal_period: 9 })).toBe('MACD 12 26 9');
    expect(formatLegendName(REALIZED_VOLATILITY, { period: 60, bars_per_year: 252 })).toBe('RV 60');
    // A missing parameter shows its default.
    expect(formatLegendName(BOLLINGER_BANDS, {})).toBe('BB 20 2');
  });

  it('adds a new indicator with the catalog defaults, solid lines of width 2, and the first free colors', () => {
    const withSma = addChartIndicator(EMPTY_CHART, SMA);
    const withBands = addChartIndicator(withSma, BOLLINGER_BANDS);

    expect(withBands).toEqual([
      {
        indicators: [
          { indicator: 'sma', parameters: { period: 50 }, hidden: false, lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }] },
          {
            indicator: 'bollinger_bands',
            parameters: { period: 20, k: 2 },
            hidden: false,
            lines: [
              { output: 'upper', color: 2, style: 'solid', width: 2 },
              { output: 'middle', color: 3, style: 'solid', width: 2 },
              { output: 'lower', color: 4, style: 'solid', width: 2 },
            ],
          },
        ],
      },
    ]);
    expect(withSma).toHaveLength(1);
  });

  it('gives the first palette colors that no line uses, in palette order', () => {
    expect(findFreeColors([1, 3], 3)).toEqual([2, 4, 5]);
    expect(findFreeColors([], 1)).toEqual([1]);
  });

  it('starts the palette again when all 14 colors are in use', () => {
    const allColors = Array.from({ length: 14 }, (_, index) => index + 1);
    expect(findFreeColors(allColors, 2)).toEqual([1, 2]);
    expect(findFreeColors([...allColors, 1], 2)).toEqual([2, 3]);
  });

  it('puts a price indicator on the price pane and an own indicator in a new pane, at most 3 own panes', () => {
    let panes = addChartIndicator(EMPTY_CHART, RSI);
    panes = addChartIndicator(panes, SMA);
    panes = addChartIndicator(panes, MACD);
    panes = addChartIndicator(panes, REALIZED_VOLATILITY);
    panes = addChartIndicator(panes, RSI);

    expect(panes.map((pane) => pane.indicators.map((indicator) => indicator.indicator))).toEqual([
      ['sma'],
      ['rsi'],
      ['macd'],
      ['realized_volatility', 'rsi'],
    ]);
  });

  it('shows the values at the crosshair bar, or at the last bar with indicator data', () => {
    const times = [100, 200, 300];

    expect(findLegendIndex(times, 200)).toBe(1);
    expect(findLegendIndex(times, null)).toBe(2);
    // A live bar after the last saved bar has no indicator value.
    expect(findLegendIndex(times, 400)).toBeNull();
    expect(findLegendIndex([], null)).toBeNull();
  });

  it('opens the add dialog with / when the focus is not in a text field, a number field, or the code editor', () => {
    const keys = { key: '/', ctrlKey: false, metaKey: false, altKey: false };
    const page = { tagName: 'BODY', isContentEditable: false };

    expect(isAddIndicatorShortcut({ ...keys, target: page })).toBe(true);
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'BUTTON', isContentEditable: false } })).toBe(true);
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'INPUT', type: 'checkbox', isContentEditable: false } })).toBe(true);
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'INPUT', type: 'text', isContentEditable: false } })).toBe(false);
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'INPUT', type: 'number', isContentEditable: false } })).toBe(false);
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'TEXTAREA', isContentEditable: false } })).toBe(false);
    // The code editor (CodeMirror) is a contenteditable element.
    expect(isAddIndicatorShortcut({ ...keys, target: { tagName: 'DIV', isContentEditable: true } })).toBe(false);
    expect(isAddIndicatorShortcut({ ...keys, ctrlKey: true, target: page })).toBe(false);
    expect(isAddIndicatorShortcut({ ...keys, key: '?', target: page })).toBe(false);
    expect(isAddIndicatorShortcut({ ...keys, target: null })).toBe(true);
  });

  it('builds a legend row for each indicator with the values of the legend bar in the line colors', () => {
    const panes = addChartIndicator(addChartIndicator(EMPTY_CHART, SMA), BOLLINGER_BANDS);
    const result: IndicatorSeriesResult = {
      times: [100, 200],
      series: [
        { indicator: 'bollinger_bands', parameters: { k: 2, period: 20 }, outputs: { upper: [null, 191.2], middle: [null, 185.1], lower: [null, 179] } },
        { indicator: 'sma', parameters: { period: 50 }, outputs: { value: [1234.5, 1240] } },
      ],
    };
    const catalog = [SMA, BOLLINGER_BANDS];

    expect(buildLegendRows(panes[0]?.indicators ?? [], catalog, result, 1, false)).toEqual([
      { name: 'SMA 50', values: [{ text: '1,240.00', color: '#6929c4' }] },
      {
        name: 'BB 20 2',
        values: [
          { text: '191.20', color: '#1192e8' },
          { text: '185.10', color: '#005d5d' },
          { text: '179.00', color: '#9f1853' },
        ],
      },
    ]);
    expect(buildLegendRows(panes[0]?.indicators ?? [], catalog, result, 0, true)[1]?.values).toEqual([
      { text: 'No value', color: '#33b1ff' },
      { text: 'No value', color: '#007d79' },
      { text: 'No value', color: '#ff7eb6' },
    ]);
    // A new indicator without a series answer yet, and a legend bar without indicator data.
    const withEma = addChartIndicator(panes, { ...SMA, key: 'ema', name: 'EMA', short_name: 'EMA', parameters: [period(20)] });
    expect(findIndicatorSeries(result, withEma[0]?.indicators[2])).toBeNull();
    expect(buildLegendRows(withEma[0]?.indicators ?? [], [...catalog, { ...SMA, key: 'ema', short_name: 'EMA', parameters: [period(20)] }], result, null, false)).toEqual([
      { name: 'SMA 50', values: [{ text: 'No value', color: '#6929c4' }] },
      { name: 'BB 20 2', values: [
        { text: 'No value', color: '#1192e8' },
        { text: 'No value', color: '#005d5d' },
        { text: 'No value', color: '#9f1853' },
      ] },
      { name: 'EMA 20', values: [{ text: 'No value', color: '#fa4d56' }] },
    ]);
  });
});
