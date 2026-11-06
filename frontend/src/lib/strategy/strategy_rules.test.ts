// The rules of the rule builder: the operands that the builder offers, the source of the rules that the "Rules" tab
// opens, and the code lines that a rule change changed (docs/architecture/strategy.md sections 9.8.2 and 9.8.5).
import { describe, expect, it } from 'vite-plus/test';
import {
  BLANK_RULES,
  createCondition,
  createOperand,
  findChangedLines,
  findIndicatorChoice,
  describeRulesWarning,
  findRulesVersionNumber,
  listOperandChoices,
  readCurrentOperand,
  readOperandChoice,
  type CatalogIndicator,
  type RuleCondition,
} from './strategy_rules';

function makeIndicator(key: string, change: Partial<CatalogIndicator> = {}): CatalogIndicator {
  return { key, name: key, short_name: key, chart_placement: 'own', parameters: [], outputs: ['value'], value_description: '', ...change };
}

function makePeriod(name: string, value: number): CatalogIndicator['parameters'][number] {
  return { name, value_type: 'int', default: value, minimum: 1, maximum: 1000, is_in_name: true };
}

const CATALOG = [
  makeIndicator('rsi', { parameters: [makePeriod('period', 14)] }),
  makeIndicator('macd', {
    name: 'MACD',
    parameters: [makePeriod('fast_period', 12), makePeriod('slow_period', 26), makePeriod('signal_period', 9)],
    outputs: ['value', 'signal', 'histogram'],
  }),
  makeIndicator('bollinger_bands', { outputs: ['upper', 'middle', 'lower'] }),
];

describe('createOperand', () => {
  it('gives a price operand for a price choice', () => {
    expect(createOperand('price:high', CATALOG)).toEqual({ type: 'price', price: 'high' });
  });

  it('gives an indicator with the catalog default parameters', () => {
    expect(createOperand('indicator:rsi', CATALOG)).toEqual({ type: 'indicator', indicator: 'rsi', parameters: { period: 14 } });
  });

  it('gives the first line of a multi-line indicator', () => {
    expect(createOperand('indicator:macd', CATALOG)).toEqual({
      type: 'indicator',
      indicator: 'macd',
      parameters: { fast_period: 12, slow_period: 26, signal_period: 9 },
      output: 'value',
    });
  });

  it('gives the number 0 for the number choice', () => {
    expect(createOperand('number', CATALOG)).toEqual({ type: 'number', value: 0 });
  });
});

describe('readOperandChoice', () => {
  it('names the choice of each operand kind', () => {
    expect(readOperandChoice({ type: 'price', price: 'close' })).toBe('price:close');
    expect(readOperandChoice({ type: 'indicator', indicator: 'sma', parameters: { period: 200 } })).toBe('indicator:sma');
    expect(readOperandChoice({ type: 'number', value: 30 })).toBe('number');
  });
});

describe('createCondition', () => {
  it('compares the close with a 50-bar SMA', () => {
    const condition: RuleCondition = createCondition();

    expect(condition).toEqual({
      type: 'condition',
      left: { type: 'price', price: 'close' },
      comparison: 'above',
      right: { type: 'indicator', indicator: 'sma', parameters: { period: 50 } },
    });
  });
});

describe('BLANK_RULES', () => {
  it('has no conditions, no exit items, and 10 fixed shares', () => {
    expect(BLANK_RULES).toEqual({
      format_version: 1,
      settings: { position_size: { type: 'fixed_shares', shares: 10 } },
      entry: { type: 'group', match: 'all_of', items: [] },
      exits: { exit_when_entry_is_false: false },
    });
  });
});

describe('findRulesVersionNumber', () => {
  const version = (versionNumber: number, source: 'user' | 'rule_builder') => ({ version_number: versionNumber, source });

  it('gives the open version when it has rules', () => {
    const versions = [version(1, 'rule_builder'), version(2, 'rule_builder'), version(3, 'user')];

    expect(findRulesVersionNumber(versions, 1)).toBe(1);
  });

  it('gives the latest version with rules when the open version has none', () => {
    const versions = [version(1, 'rule_builder'), version(2, 'rule_builder'), version(3, 'user')];

    expect(findRulesVersionNumber(versions, 3)).toBe(2);
  });

  it('gives null when no version has rules', () => {
    expect(findRulesVersionNumber([version(1, 'user')], 1)).toBeNull();
  });
});

describe('describeRulesWarning', () => {
  it('warns when the open version has no rules and is newer than the version of the rules', () => {
    expect(describeRulesWarning(2, 1)).toBe('Code of v2 changed. Rules are from v1.');
  });

  it('gives no warning when the rules are from the open version', () => {
    expect(describeRulesWarning(2, 2)).toBeNull();
  });

  it('gives no warning when the open version is older than the version of the rules', () => {
    expect(describeRulesWarning(1, 3)).toBeNull();
  });

  it('gives no warning when no version has rules', () => {
    expect(describeRulesWarning(2, 0)).toBeNull();
  });
});

describe('findChangedLines', () => {
  it('gives the numbers of the new lines that the old code does not have', () => {
    const before = 'a = 1\nb = 2\nc = 3\n';
    const after = 'a = 1\nb = 5\nc = 3\nd = 4\n';

    expect(findChangedLines(before, after)).toEqual([2, 4]);
  });

  it('marks a repeated line only as often as the old code lacks it', () => {
    expect(findChangedLines('x\n', 'x\nx\n')).toEqual([2]);
  });

  it('gives no lines when there is no old code', () => {
    expect(findChangedLines('', 'a = 1\n')).toEqual([]);
  });
});

describe('listOperandChoices', () => {
  it('offers only indicators for the rank of the universe mode', () => {
    const choices = listOperandChoices('rank', CATALOG).map((choice) => choice.value);

    expect(choices).toContain('indicator:rsi');
    expect(choices.every((choice) => choice.startsWith('indicator:'))).toBe(true);
  });

  const FORMULA = { name: 'Ratio', expression: 'close / sma(5)', chart_placement: 'own' };

  it('offers the indicators in the order of the catalog', () => {
    const choices = listOperandChoices('rank', [...CATALOG, makeIndicator('custom_1', { name: 'Ratio', formula: FORMULA })]);

    expect(choices.at(-1)).toEqual({ value: 'indicator:custom_1', label: 'Ratio' });
  });

  it('keeps a deleted custom indicator of the operand', () => {
    const choices = listOperandChoices('rank', [], { type: 'indicator', indicator: 'custom_1', parameters: {}, formula: FORMULA });

    expect(choices.at(-1)).toEqual({ value: 'indicator:custom_1', label: 'Ratio' });
  });

  it('a custom operand holds the formula', () => {
    expect(createOperand('indicator:custom_1', [makeIndicator('custom_1', { formula: FORMULA })])).toEqual({
      type: 'indicator',
      indicator: 'custom_1',
      parameters: {},
      formula: FORMULA,
    });
  });
});

describe('a new indicator of the catalog', () => {
  const NEW_INDICATOR = makeIndicator('new_one', {
    name: 'New one',
    parameters: [makePeriod('period', 7), { ...makePeriod('hidden', 3), is_in_name: false }],
    outputs: ['value', 'upper'],
  });

  it('is a choice of the rule builder without a change of the frontend', () => {
    expect(listOperandChoices('rank', [NEW_INDICATOR])).toEqual([{ value: 'indicator:new_one', label: 'New one' }]);
  });

  it('gets its parameters and its first line from the catalog', () => {
    expect(createOperand('indicator:new_one', [NEW_INDICATOR])).toEqual({
      type: 'indicator',
      indicator: 'new_one',
      parameters: { period: 7 },
      output: 'value',
    });
  });
});

describe('findIndicatorChoice', () => {
  it('keeps the MACD line labels and names other lines from their output', () => {
    expect(findIndicatorChoice('macd', CATALOG)?.lines).toEqual([
      ['value', 'MACD line'],
      ['signal', 'Signal line'],
      ['histogram', 'Histogram'],
    ]);
    expect(findIndicatorChoice('bollinger_bands', CATALOG)?.lines[0]).toEqual(['upper', 'Upper']);
  });

  it('gives no choice for a custom indicator', () => {
    const formula = { name: 'Ratio', expression: 'close / sma(5)', chart_placement: 'own' };

    expect(findIndicatorChoice('custom_1', [makeIndicator('custom_1', { formula })])).toBeUndefined();
  });
});

describe('readCurrentOperand', () => {
  const formula = { name: 'Ratio', expression: 'close / sma(5)', chart_placement: 'own' };
  const changed = makeIndicator('custom_1', { formula: { ...formula, expression: 'close / sma(9)' } });
  const operand = { type: 'indicator', indicator: 'custom_1', parameters: {}, formula } as const;

  it('copies the formula of the catalog into an operand with another formula', () => {
    expect(readCurrentOperand(operand, [changed])).toEqual({ ...operand, formula: changed.formula });
  });

  it('gives null when the operand has the formula of the catalog', () => {
    expect(readCurrentOperand(operand, [makeIndicator('custom_1', { formula })])).toBeNull();
  });

  it('gives null for a deleted indicator and for an operand without a formula', () => {
    expect(readCurrentOperand(operand, [])).toBeNull();
    expect(readCurrentOperand({ type: 'number', value: 1 }, [changed])).toBeNull();
    expect(readCurrentOperand({ type: 'indicator', indicator: 'custom_1', parameters: {} }, [changed])).toBeNull();
  });
});
