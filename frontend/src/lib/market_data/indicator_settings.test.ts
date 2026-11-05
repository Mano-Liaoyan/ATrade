import { describe, expect, it } from 'vite-plus/test';
import type { ChartIndicator, ChartIndicatorDefinition, ChartPane } from './chart_indicators';
import {
  applySettingsDraft,
  checkSettingsDraft,
  createSettingsDraft,
  describeApplyBlock,
  formatLineLabel,
  formatParameterLabel,
  hasSettingsProblems,
  replaceChartIndicator,
  resetSettingsDraft,
} from './indicator_settings';

function period(defaultValue: number): ChartIndicatorDefinition['parameters'][number] {
  return { name: 'period', value_type: 'int', default: defaultValue, minimum: 1, maximum: 1000, is_in_name: true };
}

const SMA: ChartIndicatorDefinition = {
  key: 'sma',
  name: 'Simple moving average',
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
  value_description: '',
};
const MOMENTUM: ChartIndicatorDefinition = {
  key: 'momentum_12_1',
  name: '12-1 momentum',
  short_name: 'MOM',
  chart_placement: 'own',
  parameters: [
    { ...period(252), name: 'look_back' },
    { ...period(21), name: 'skip', minimum: 0, maximum: 999 },
  ],
  outputs: ['value'],
  value_description: '',
};

const smaIndicator: ChartIndicator = {
  indicator: 'sma',
  parameters: { period: 50 },
  hidden: false,
  lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }],
};

describe('describeApplyBlock', () => {
  it('names the first field with a problem, in the order of the fields', () => {
    expect(describeApplyBlock(MACD, { slow_period: 'Enter a number.', fast_period: 'Enter a number.' })).toBe('Fix Fast period to apply.');
  });

  it('is null without a problem', () => {
    expect(describeApplyBlock(SMA, {})).toBeNull();
  });
});

describe('createSettingsDraft', () => {
  it('holds the parameters as text and a copy of the lines', () => {
    const draft = createSettingsDraft(smaIndicator);
    expect(draft).toEqual({ parameters: { period: '50' }, lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }] });
    expect(draft.lines[0]).not.toBe(smaIndicator.lines[0]);
  });
});

describe('checkSettingsDraft', () => {
  it('gives no problems for values in their ranges', () => {
    const problems = checkSettingsDraft(BOLLINGER_BANDS, { parameters: { period: '20', k: '2.5' }, lines: [] });
    expect(problems).toEqual({});
    expect(hasSettingsProblems(problems)).toBe(false);
  });

  it('names a value out of its range, an empty value, and a fraction for a whole number parameter', () => {
    expect(checkSettingsDraft(SMA, { parameters: { period: '0' }, lines: [] })).toEqual({ period: 'Enter a value from 1 to 1000.' });
    expect(checkSettingsDraft(SMA, { parameters: { period: '1001' }, lines: [] })).toEqual({ period: 'Enter a value from 1 to 1000.' });
    expect(checkSettingsDraft(SMA, { parameters: { period: '' }, lines: [] })).toEqual({ period: 'Enter a number.' });
    expect(checkSettingsDraft(SMA, { parameters: { period: '20.5' }, lines: [] })).toEqual({ period: 'Enter a whole number.' });
    expect(checkSettingsDraft(BOLLINGER_BANDS, { parameters: { period: '20', k: '0.05' }, lines: [] })).toEqual({
      k: 'Enter a value from 0.1 to 10.',
    });
    expect(hasSettingsProblems({ period: 'Enter a number.' })).toBe(true);
  });

  it('needs the MACD fast period less than the slow period', () => {
    const draft = { parameters: { fast_period: '26', slow_period: '26', signal_period: '9' }, lines: [] };
    expect(checkSettingsDraft(MACD, draft)).toEqual({ fast_period: 'Fast period must be less than slow period (26).' });
    expect(checkSettingsDraft(MACD, { ...draft, parameters: { ...draft.parameters, fast_period: '25' } })).toEqual({});
  });

  it('needs the 12-1 momentum skip less than the look back', () => {
    const draft = { parameters: { look_back: '20', skip: '21' }, lines: [] };
    expect(checkSettingsDraft(MOMENTUM, draft)).toEqual({ skip: 'Skip must be less than look back (20).' });
    expect(checkSettingsDraft(MOMENTUM, { parameters: { look_back: '252', skip: '21' }, lines: [] })).toEqual({});
  });

  it('checks the order only when both values are correct numbers', () => {
    const draft = { parameters: { fast_period: '', slow_period: '26', signal_period: '9' }, lines: [] };
    expect(checkSettingsDraft(MACD, draft)).toEqual({ fast_period: 'Enter a number.' });
  });
});

describe('resetSettingsDraft', () => {
  it('gives the catalog defaults, solid lines of width 2, and keeps the colors', () => {
    const draft = {
      parameters: { period: '5', k: '' },
      lines: [
        { output: 'upper', color: 4, style: 'dotted' as const, width: 1 },
        { output: 'middle', color: 5, style: 'dashed' as const, width: 4 },
        { output: 'lower', color: 6, style: 'solid' as const, width: 3 },
      ],
    };
    expect(resetSettingsDraft(BOLLINGER_BANDS, draft)).toEqual({
      parameters: { period: '20', k: '2' },
      lines: [
        { output: 'upper', color: 4, style: 'solid', width: 2 },
        { output: 'middle', color: 5, style: 'solid', width: 2 },
        { output: 'lower', color: 6, style: 'solid', width: 2 },
      ],
    });
  });
});

describe('applySettingsDraft', () => {
  it('gives the indicator the numbers and the lines of the draft and keeps hidden', () => {
    const draft = { parameters: { period: '20' }, lines: [{ output: 'value', color: 3, style: 'dashed' as const, width: 3 }] };
    expect(applySettingsDraft({ ...smaIndicator, hidden: true }, SMA, draft)).toEqual({
      indicator: 'sma',
      parameters: { period: 20 },
      hidden: true,
      lines: [{ output: 'value', color: 3, style: 'dashed', width: 3 }],
    });
  });
});

describe('replaceChartIndicator', () => {
  it('replaces one indicator and keeps the others', () => {
    const rsi: ChartIndicator = { ...smaIndicator, indicator: 'rsi' };
    const panes: ChartPane[] = [{ indicators: [smaIndicator, smaIndicator] }, { indicators: [rsi] }];
    const changed = { ...smaIndicator, hidden: true };
    expect(replaceChartIndicator(panes, 0, 1, changed)).toEqual([{ indicators: [smaIndicator, changed] }, { indicators: [rsi] }]);
    expect(panes[0]?.indicators[1]).toBe(smaIndicator);
  });
});

describe('labels', () => {
  it('formats a parameter name as the screen editor does', () => {
    expect(formatParameterLabel('bars_per_year')).toBe('Bars per year');
    expect(formatParameterLabel('k')).toBe('K');
  });

  it('names the line groups: "Line" for one line, the output label for more, and "MACD line" for the MACD value', () => {
    expect(formatLineLabel(SMA, 'value')).toBe('Line');
    expect(formatLineLabel(BOLLINGER_BANDS, 'upper')).toBe('Upper');
    expect(formatLineLabel(MACD, 'value')).toBe('MACD line');
    expect(formatLineLabel(MACD, 'signal')).toBe('Signal line');
    expect(formatLineLabel(MACD, 'histogram')).toBe('Histogram');
  });
});
