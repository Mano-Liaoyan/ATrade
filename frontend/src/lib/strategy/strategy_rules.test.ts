// The rules of the rule builder: the operands that the builder offers, the source of the rules that the "Rules" tab
// opens, and the code lines that a rule change changed (docs/architecture/strategy.md sections 9.8.2 and 9.8.5).
import { describe, expect, it } from 'vite-plus/test';
import {
  BLANK_RULES,
  createCondition,
  createOperand,
  findChangedLines,
  describeRulesWarning,
  findRulesVersionNumber,
  readOperandChoice,
  type RuleCondition,
} from './strategy_rules';

describe('createOperand', () => {
  it('gives a price operand for a price choice', () => {
    expect(createOperand('price:high')).toEqual({ type: 'price', price: 'high' });
  });

  it('gives an indicator with the catalog default parameters', () => {
    expect(createOperand('indicator:rsi')).toEqual({ type: 'indicator', indicator: 'rsi', parameters: { period: 14 } });
  });

  it('gives the first line of a multi-line indicator', () => {
    expect(createOperand('indicator:macd')).toEqual({
      type: 'indicator',
      indicator: 'macd',
      parameters: { fast_period: 12, slow_period: 26, signal_period: 9 },
      output: 'value',
    });
  });

  it('gives the number 0 for the number choice', () => {
    expect(createOperand('number')).toEqual({ type: 'number', value: 0 });
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
