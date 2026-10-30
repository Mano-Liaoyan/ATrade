// The rules of the rule builder (docs/architecture/strategy.md section 9.8.2). The backend checks them and makes the
// code from them. This module gives the choices of the "Rules" tab (section 9.8.5): the prices, the indicators of the
// catalog (backend/src/atrade/indicator/indicator_catalog.py) with their parameters and lines, and the comparisons.

import type { components } from '#lib/api';

type Schemas = components['schemas'];
export type StrategyRules = Schemas['StrategyRules'];
export type RuleGroup = Schemas['RuleGroup'];
export type InnerRuleGroup = Schemas['InnerRuleGroup'];
export type RuleCondition = Schemas['RuleCondition'];
export type LeftOperand = Schemas['LeftOperand'];
export type RightOperand = Schemas['RightOperand'];
export type IndicatorOperand = Schemas['IndicatorOperand'];
export type Comparison = Schemas['Comparison'];
export type PriceName = Schemas['PriceName'];
export type GroupMatch = Schemas['GroupMatch'];
export type PositionSize = Schemas['RuleSettings']['position_size'];
export type RuleExits = Schemas['RuleExits'];

export interface IndicatorParameterChoice {
  name: string;
  isInteger: boolean;
  default: number;
  minimum: number;
  maximum: number;
}

export interface IndicatorChoice {
  key: string;
  label: string;
  parameters: IndicatorParameterChoice[];
  /** The lines of a multi-line indicator as [output, label]. A single-line indicator has none. */
  lines: [string, string][];
}

const MAXIMUM_PERIOD = 1000;

function period(choice: { default: number; name?: string; minimum?: number }): IndicatorParameterChoice {
  return {
    name: choice.name ?? 'period',
    isInteger: true,
    default: choice.default,
    minimum: choice.minimum ?? 1,
    maximum: MAXIMUM_PERIOD,
  };
}

const THREE_LINES: [string, string][] = [
  ['upper', 'Upper'],
  ['middle', 'Middle'],
  ['lower', 'Lower'],
];

// The order and the defaults of the catalog. A parameter that the catalog leaves out of the name (bars_per_year of
// realized volatility) keeps its default: the builder does not show it.
export const INDICATOR_CHOICES: IndicatorChoice[] = [
  { key: 'sma', label: 'SMA', parameters: [period({ default: 50 })], lines: [] },
  { key: 'ema', label: 'EMA', parameters: [period({ default: 20 })], lines: [] },
  {
    key: 'momentum_12_1',
    label: '12-1 momentum',
    parameters: [
      period({ name: 'look_back', default: 252 }),
      { name: 'skip', isInteger: true, default: 21, minimum: 0, maximum: MAXIMUM_PERIOD - 1 },
    ],
    lines: [],
  },
  { key: 'distance_to_52_week_high', label: 'Distance to 52-week high', parameters: [period({ default: 252 })], lines: [] },
  { key: 'realized_volatility', label: 'Realized volatility', parameters: [period({ default: 60, minimum: 2 })], lines: [] },
  { key: 'atr', label: 'ATR', parameters: [period({ default: 14 })], lines: [] },
  { key: 'average_trading_value', label: 'Average trading value', parameters: [period({ default: 20 })], lines: [] },
  { key: 'rsi', label: 'RSI', parameters: [period({ default: 14 })], lines: [] },
  {
    key: 'macd',
    label: 'MACD',
    parameters: [
      period({ name: 'fast_period', default: 12 }),
      period({ name: 'slow_period', default: 26, minimum: 2 }),
      period({ name: 'signal_period', default: 9 }),
    ],
    lines: [
      ['value', 'MACD line'],
      ['signal', 'Signal line'],
      ['histogram', 'Histogram'],
    ],
  },
  {
    key: 'bollinger_bands',
    label: 'Bollinger Bands',
    parameters: [period({ default: 20 }), { name: 'k', isInteger: false, default: 2, minimum: 0.1, maximum: 10 }],
    lines: THREE_LINES,
  },
  { key: 'donchian_channel', label: 'Donchian channel', parameters: [period({ default: 20 })], lines: THREE_LINES },
];

export const PRICE_CHOICES: [PriceName, string][] = [
  ['close', 'Close'],
  ['open', 'Open'],
  ['high', 'High'],
  ['low', 'Low'],
];

export const COMPARISON_CHOICES: { value: Comparison; label: string }[] = [
  { value: 'above', label: 'is above' },
  { value: 'below', label: 'is below' },
  { value: 'at_or_above', label: 'is at or above' },
  { value: 'at_or_below', label: 'is at or below' },
  { value: 'crosses_above', label: 'crosses above' },
  { value: 'crosses_below', label: 'crosses below' },
];

/** The value of the operand select: `price:<name>`, `indicator:<key>`, or `number` (right side only). */
export type OperandChoice = `price:${PriceName}` | `indicator:${string}` | 'number';

export function listOperandChoices(side: 'left' | 'right'): { value: OperandChoice; label: string }[] {
  const prices = PRICE_CHOICES.map(([name, label]) => ({ value: `price:${name}` as const, label }));
  const indicators = INDICATOR_CHOICES.map((choice) => ({ value: `indicator:${choice.key}` as const, label: choice.label }));
  const numbers = side === 'right' ? [{ value: 'number' as const, label: 'Number' }] : [];
  return [...prices, ...indicators, ...numbers];
}

export function findIndicatorChoice(key: string): IndicatorChoice | undefined {
  return INDICATOR_CHOICES.find((choice) => choice.key === key);
}

export function readOperandChoice(operand: RightOperand): OperandChoice {
  if (operand.type === 'price') {
    return `price:${operand.price}`;
  }
  if (operand.type === 'indicator') {
    return `indicator:${operand.indicator}`;
  }
  return 'number';
}

export function createOperand(choice: OperandChoice): RightOperand {
  if (choice === 'number') {
    return { type: 'number', value: 0 };
  }
  const [kind, name] = choice.split(':') as ['price' | 'indicator', string];
  if (kind === 'price') {
    return { type: 'price', price: name as PriceName };
  }
  const indicator = findIndicatorChoice(name);
  const parameters = Object.fromEntries((indicator?.parameters ?? []).map((parameter) => [parameter.name, parameter.default]));
  const operand: IndicatorOperand = { type: 'indicator', indicator: name, parameters };
  const firstLine = indicator?.lines[0];
  return firstLine === undefined ? operand : { ...operand, output: firstLine[0] };
}

export function createCondition(): RuleCondition {
  return {
    type: 'condition',
    left: { type: 'price', price: 'close' },
    comparison: 'above',
    right: createOperand('indicator:sma'),
  };
}

export function createGroup(): InnerRuleGroup {
  return { type: 'group', match: 'all_of', items: [] };
}

// Decided (#173): a strategy without a version with rules opens these rules in the "Rules" tab.
export const BLANK_RULES: StrategyRules = {
  format_version: 1,
  settings: { position_size: { type: 'fixed_shares', shares: 10 } },
  entry: { type: 'group', match: 'all_of', items: [] },
  exits: { exit_when_entry_is_false: false },
};

/** The version whose rules the "Rules" tab opens: the open version when it has rules, or else the latest version with
 rules (vM, section 9.8.4). Null when no version has rules. */
export function findRulesVersionNumber(
  versions: readonly { version_number: number; source: string }[],
  openVersionNumber: number,
): number | null {
  const ruleVersions = versions.filter((version) => version.source === 'rule_builder');
  if (ruleVersions.some((version) => version.version_number === openVersionNumber)) {
    return openVersionNumber;
  }
  return ruleVersions.at(-1)?.version_number ?? null;
}

/** The line numbers (1 is the first line) of the new code that the old code does not have. Each old line matches one
 new line. Without old code, no line changed. */
export function findChangedLines(oldCode: string, newCode: string): number[] {
  if (oldCode === '') {
    return [];
  }
  const oldLineCounts = new Map<string, number>();
  for (const line of oldCode.split('\n')) {
    oldLineCounts.set(line, (oldLineCounts.get(line) ?? 0) + 1);
  }
  const changedLines: number[] = [];
  newCode.split('\n').forEach((line, index) => {
    const count = oldLineCounts.get(line) ?? 0;
    if (count > 0) {
      oldLineCounts.set(line, count - 1);
    } else {
      changedLines.push(index + 1);
    }
  });
  return changedLines;
}
