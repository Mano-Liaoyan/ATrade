// The rules of the rule builder (docs/architecture/strategy.md section 9.8.2). The backend checks them and makes the
// code from them. This module gives the choices of the "Rules" tab (section 9.8.5): the prices, the indicators of the
// catalog response with their parameters and lines, and the comparisons.

import type { components } from '#lib/api';

type Schemas = components['schemas'];
export type StrategyRules = Schemas['StrategyRules'];
export type RuleGroup = Schemas['RuleGroup'];
export type InnerRuleGroup = Schemas['InnerRuleGroup'];
export type RuleCondition = Schemas['RuleCondition'];
export type LeftOperand = Schemas['LeftOperand'];
export type RightOperand = Schemas['RightOperand'];
export type IndicatorOperand = Schemas['IndicatorOperand'];
/** One indicator of the catalog response, built-in or custom. */
export type CatalogIndicator = Schemas['IndicatorResponse'];
export type Comparison = Schemas['Comparison'];
export type PriceName = Schemas['PriceName'];
export type GroupMatch = Schemas['GroupMatch'];
export type PositionSize = Schemas['RuleSettings']['position_size'];
export type RuleExits = Schemas['RuleExits'];
export type UniverseSettings = Schemas['UniverseSettings'];
export type RankDirection = Schemas['RankDirection'];
export type RebalancePeriod = Schemas['RebalancePeriod'];

// The universe mode settings (docs/architecture/strategy.md section 9.8.6), with the words of the prototype (#138).
export const REBALANCE_CHOICES: { value: RebalancePeriod; label: string }[] = [
  { value: 'weekly', label: 'Each week' },
  { value: 'monthly', label: 'Each month' },
  { value: 'quarterly', label: 'Each quarter' },
];
export const RANK_DIRECTION_CHOICES: { value: RankDirection; label: string }[] = [
  { value: 'high_to_low', label: 'Highest first' },
  { value: 'low_to_high', label: 'Lowest first' },
];

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

const LINE_LABELS: Record<string, string> = { value: 'MACD line', signal: 'Signal line', histogram: 'Histogram' };

function readLineLabel(output: string): string {
  return LINE_LABELS[output] ?? output.charAt(0).toUpperCase() + output.slice(1);
}

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

// The rank of the universe mode takes an indicator only.
// A deleted custom indicator stays in the list of its operand: the operand holds the expression (indicator.md section 23.10).
function listDeletedIndicator(catalog: readonly CatalogIndicator[], operand: RightOperand | undefined): { key: string; name: string }[] {
  if (operand?.type !== 'indicator' || catalog.some((choice) => choice.key === operand.indicator)) {
    return [];
  }
  return operand.formula ? [{ key: operand.indicator, name: operand.formula.name }] : [];
}

export function listOperandChoices(
  side: 'left' | 'right' | 'rank',
  catalog: readonly CatalogIndicator[],
  operand?: RightOperand,
): { value: OperandChoice; label: string }[] {
  const prices = side === 'rank' ? [] : PRICE_CHOICES.map(([name, label]) => ({ value: `price:${name}` as const, label }));
  const indicators = [...catalog, ...listDeletedIndicator(catalog, operand)].map((choice) => ({
    value: `indicator:${choice.key}` as const,
    label: choice.name,
  }));
  const numbers = side === 'right' ? [{ value: 'number' as const, label: 'Number' }] : [];
  return [...prices, ...indicators, ...numbers];
}

/** The parameters and lines of a built-in indicator. A custom indicator has none. A parameter that the catalog leaves
 * out of the name (bars_per_year of realized volatility) keeps its default: the builder does not show it. */
export function findIndicatorChoice(key: string, catalog: readonly CatalogIndicator[]): IndicatorChoice | undefined {
  const indicator = catalog.find((choice) => choice.key === key);
  if (indicator === undefined || indicator.formula) {
    return undefined;
  }
  return {
    key,
    label: indicator.name,
    parameters: indicator.parameters
      .filter((parameter) => parameter.is_in_name)
      .map((parameter) => ({
        name: parameter.name,
        isInteger: parameter.value_type === 'int',
        default: parameter.default,
        minimum: parameter.minimum,
        maximum: parameter.maximum,
      })),
    lines: indicator.outputs.length > 1 ? indicator.outputs.map((output) => [output, readLineLabel(output)]) : [],
  };
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

export function createOperand(choice: OperandChoice, catalog: readonly CatalogIndicator[]): RightOperand {
  if (choice === 'number') {
    return { type: 'number', value: 0 };
  }
  const [kind, name] = choice.split(':') as ['price' | 'indicator', string];
  if (kind === 'price') {
    return { type: 'price', price: name as PriceName };
  }
  const formula = catalog.find((item) => item.key === name)?.formula;
  if (formula) {
    return { type: 'indicator', indicator: name, parameters: {}, formula };
  }
  const indicator = findIndicatorChoice(name, catalog);
  const parameters = Object.fromEntries((indicator?.parameters ?? []).map((parameter) => [parameter.name, parameter.default]));
  const operand: IndicatorOperand = { type: 'indicator', indicator: name, parameters };
  const firstLine = indicator?.lines[0];
  return firstLine === undefined ? operand : { ...operand, output: firstLine[0] };
}

/**
 * The operand with the formula of the catalog. Null when the operand already has it or the indicator is deleted. The
 * Select cannot do this: a click on the selected item changes nothing.
 */
export function readCurrentOperand(operand: RightOperand, catalog: readonly CatalogIndicator[]): IndicatorOperand | null {
  const formula = operand.type === 'indicator' ? operand.formula : null;
  const current = operand.type === 'indicator' ? catalog.find((item) => item.key === operand.indicator)?.formula : null;
  if (operand.type !== 'indicator' || !formula || !current) {
    return null;
  }
  const isSame =
    formula.name === current.name && formula.expression === current.expression && formula.chart_placement === current.chart_placement;
  return isSame ? null : { ...operand, formula: current };
}

export function createCondition(): RuleCondition {
  return {
    type: 'condition',
    left: { type: 'price', price: 'close' },
    comparison: 'above',
    right: { type: 'indicator', indicator: 'sma', parameters: { period: 50 } },
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

/** The warning of the "Rules" tab (docs/architecture/strategy.md section 9.8.4): the open version vN has no rules and
 is newer than the latest version with rules vM. `rulesVersionNumber` is 0 when no version has rules. */
export function describeRulesWarning(openVersionNumber: number, rulesVersionNumber: number): string | null {
  if (rulesVersionNumber === 0 || openVersionNumber <= rulesVersionNumber) {
    return null;
  }
  return `Code of v${String(openVersionNumber)} changed. Rules are from v${String(rulesVersionNumber)}.`;
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
