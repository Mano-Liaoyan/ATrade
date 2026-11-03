// Pure functions of the indicator settings popover (docs/architecture/indicator.md section 23.9.5): the draft of
// the fields, its check (the catalog ranges and the parameter order rules of section 23.6), "Reset to defaults", and
// the apply step.
import { isHistogramLine } from './chart_indicator_styles';
import type { ChartIndicator, ChartIndicatorDefinition, ChartIndicatorLine, ChartPane } from './chart_indicators';

/** The fields of the settings. The parameters are the texts of the number fields, so a wrong text stays. */
export interface IndicatorSettingsDraft {
  parameters: Record<string, string>;
  lines: ChartIndicatorLine[];
}

/** The invalid text of each parameter field that has a problem. */
export type SettingsProblems = Record<string, string>;

// Section 23.6: the first parameter must be less than the second. The catalog route does not give these rules.
const PARAMETER_ORDERS: Record<string, readonly (readonly [string, string])[]> = {
  macd: [['fast_period', 'slow_period']],
  momentum_12_1: [['skip', 'look_back']],
};

const RESET_LINE_STYLE = 'solid';
const RESET_LINE_WIDTH = 2;

export function createSettingsDraft(indicator: ChartIndicator): IndicatorSettingsDraft {
  return {
    parameters: Object.fromEntries(Object.entries(indicator.parameters).map(([name, value]) => [name, String(value)])),
    lines: indicator.lines.map((line) => ({ ...line })),
  };
}

function readNumber(text: string | undefined): number | null {
  if (text === undefined || text.trim() === '') {
    return null;
  }
  const number = Number(text);
  return Number.isFinite(number) ? number : null;
}

function checkParameter(parameter: ChartIndicatorDefinition['parameters'][number], number: number | null): string | null {
  if (number === null) {
    return 'Enter a number.';
  }
  if (parameter.value_type === 'int' && !Number.isInteger(number)) {
    return 'Enter a whole number.';
  }
  if (number < parameter.minimum || number > parameter.maximum) {
    return `Enter a value from ${String(parameter.minimum)} to ${String(parameter.maximum)}.`;
  }
  return null;
}

/** The problems of the parameter fields. An empty object means that "Apply" can apply the draft. */
export function checkSettingsDraft(definition: ChartIndicatorDefinition, draft: IndicatorSettingsDraft): SettingsProblems {
  const problems: SettingsProblems = {};
  const numbers: Record<string, number> = {};
  for (const parameter of definition.parameters) {
    const number = readNumber(draft.parameters[parameter.name]);
    const problem = checkParameter(parameter, number);
    if (problem !== null) {
      problems[parameter.name] = problem;
    } else if (number !== null) {
      numbers[parameter.name] = number;
    }
  }
  for (const [smaller, larger] of PARAMETER_ORDERS[definition.key] ?? []) {
    const smallerValue = numbers[smaller];
    const largerValue = numbers[larger];
    if (smallerValue !== undefined && largerValue !== undefined && smallerValue >= largerValue) {
      problems[smaller] = `${formatParameterLabel(smaller)} must be less than ${formatParameterLabel(larger).toLowerCase()} (${String(largerValue)}).`;
    }
  }
  return problems;
}

export function hasSettingsProblems(problems: SettingsProblems): boolean {
  return Object.keys(problems).length > 0;
}

/** "Reset to defaults": the catalog defaults of the parameters, solid lines of width 2. The colors do not change. */
export function resetSettingsDraft(definition: ChartIndicatorDefinition, draft: IndicatorSettingsDraft): IndicatorSettingsDraft {
  return {
    parameters: Object.fromEntries(definition.parameters.map((parameter) => [parameter.name, String(parameter.default)])),
    lines: draft.lines.map((line) => ({ ...line, style: RESET_LINE_STYLE, width: RESET_LINE_WIDTH })),
  };
}

/** The indicator with the values of a draft without problems. It stays hidden or shown. */
export function applySettingsDraft(
  indicator: ChartIndicator,
  definition: ChartIndicatorDefinition,
  draft: IndicatorSettingsDraft,
): ChartIndicator {
  return {
    ...indicator,
    parameters: Object.fromEntries(
      definition.parameters.map((parameter) => [parameter.name, readNumber(draft.parameters[parameter.name]) ?? parameter.default]),
    ),
    lines: draft.lines.map((line) => ({ ...line })),
  };
}

/** Puts `indicator` in place of indicator `indicatorIndex` of pane `paneIndex`. Returns new panes. */
export function replaceChartIndicator(
  panes: readonly ChartPane[],
  paneIndex: number,
  indicatorIndex: number,
  indicator: ChartIndicator,
): ChartPane[] {
  return panes.map((pane, index) =>
    index === paneIndex
      ? { indicators: pane.indicators.map((item, itemIndex) => (itemIndex === indicatorIndex ? indicator : item)) }
      : pane,
  );
}

/** "bars_per_year" is "Bars per year", as the parameter labels of the screen editor. */
export function formatParameterLabel(name: string): string {
  const words = name.replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const LINE_LABELS: Record<string, Record<string, string>> = {
  macd: { value: 'MACD line', signal: 'Signal line' },
};

/** The heading of the line group of `output`: "Line" or "Histogram" for one line, else the output label. */
export function formatLineLabel(definition: ChartIndicatorDefinition, output: string): string {
  if (definition.outputs.length === 1) {
    return isHistogramLine(definition.key, output) ? 'Histogram' : 'Line';
  }
  return LINE_LABELS[definition.key]?.[output] ?? formatParameterLabel(output);
}
