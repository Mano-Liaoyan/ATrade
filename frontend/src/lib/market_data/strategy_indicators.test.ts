import { describe, expect, it } from 'vite-plus/test';
import type { ChartIndicatorDefinition } from './chart_indicators';
import { placeStrategyIndicators } from './strategy_indicators';

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
  value_description: '',
};
const BOLLINGER_BANDS: ChartIndicatorDefinition = {
  key: 'bollinger_bands',
  name: 'Bollinger Bands',
  short_name: 'BB',
  chart_placement: 'price',
  parameters: [period(20), { name: 'k', value_type: 'float', default: 2, minimum: 0.1, maximum: 10, is_in_name: true }],
  outputs: ['upper', 'middle', 'lower'],
  value_description: '',
};
const RSI: ChartIndicatorDefinition = { ...SMA, key: 'rsi', name: 'RSI', short_name: 'RSI', chart_placement: 'own', parameters: [period(14)] };
const CATALOG = [SMA, BOLLINGER_BANDS, RSI];

describe('placeStrategyIndicators', () => {
  it('places each strategy indicator as a new indicator: price pane, own panes, and the next free colors', () => {
    const panes = placeStrategyIndicators(
      [
        { indicator: 'sma', parameters: { period: 30 } },
        { indicator: 'rsi', parameters: {} },
        { indicator: 'bollinger_bands', parameters: { k: 2.5 } },
      ],
      CATALOG,
    );

    expect(panes).toEqual([
      {
        indicators: [
          { indicator: 'sma', parameters: { period: 30 }, hidden: false, lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }] },
          {
            indicator: 'bollinger_bands',
            parameters: { period: 20, k: 2.5 },
            hidden: false,
            lines: [
              { output: 'upper', color: 3, style: 'solid', width: 2 },
              { output: 'middle', color: 4, style: 'solid', width: 2 },
              { output: 'lower', color: 5, style: 'solid', width: 2 },
            ],
          },
        ],
      },
      {
        indicators: [{ indicator: 'rsi', parameters: { period: 14 }, hidden: false, lines: [{ output: 'value', color: 2, style: 'solid', width: 2 }] }],
      },
    ]);
  });

  it('leaves out an indicator that is not in the catalog and gives only the price pane without indicators', () => {
    expect(placeStrategyIndicators([{ indicator: 'missing', parameters: {} }], CATALOG)).toEqual([{ indicators: [] }]);
    expect(placeStrategyIndicators([], CATALOG)).toEqual([{ indicators: [] }]);
  });
});
