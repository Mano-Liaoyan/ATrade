// Pure functions of a stored indicator reference (docs/architecture/indicator.md sections 23.6 and 23.10). The bar
// charts, the screen conditions, and the rule builder use them: a reference to a custom indicator holds its `formula`
// with its parameters, so the reference works after a change or a delete of the custom indicator.
import type { components } from '#lib/api';

/** One indicator of the catalog (`GET /api/market-data/indicators`, `GET /api/screen-indicators`). */
export type ChartIndicatorDefinition = components['schemas']['IndicatorResponse'];
export type IndicatorFormula = components['schemas']['IndicatorFormulaBody'];
export type ChartIndicatorParameter = ChartIndicatorDefinition['parameters'][number];

/** The parameters of a formula in the form of the catalog. */
export function listFormulaParameters(formula: IndicatorFormula): ChartIndicatorParameter[] {
  return (formula.parameters ?? []).map((parameter) => ({
    name: parameter.name,
    value_type: parameter.value_type === 'int' ? 'int' : 'float',
    default: parameter.default,
    minimum: parameter.minimum,
    maximum: parameter.maximum,
    is_in_name: true,
    label: parameter.label,
    description: parameter.description,
  }));
}

/** True when the 2 formulas give the same indicator with the same parameters. */
export function isSameFormula(first: IndicatorFormula, second: IndicatorFormula): boolean {
  return (
    first.name === second.name &&
    first.expression === second.expression &&
    first.chart_placement === second.chart_placement &&
    JSON.stringify(listFormulaParameters(first)) === JSON.stringify(listFormulaParameters(second))
  );
}

/**
 * The definition of a reference: the definition of its `formula` when it has one, else the catalog item. A deleted
 * custom indicator is not in the catalog, and a changed one has another expression there.
 */
export function findChartDefinition(
  catalog: readonly ChartIndicatorDefinition[],
  reference: { indicator: string; formula?: IndicatorFormula | null },
): ChartIndicatorDefinition | undefined {
  const { indicator, formula } = reference;
  const catalogItem = catalog.find((item) => item.key === indicator);
  if (formula === undefined || formula === null) {
    return catalogItem;
  }
  return {
    key: indicator,
    name: formula.name,
    short_name: formula.name,
    chart_placement: formula.chart_placement === 'price' ? 'price' : 'own',
    parameters: listFormulaParameters(formula),
    outputs: ['value'],
    value_description: catalogItem?.value_description ?? '',
    formula,
  };
}

/** The parameters of the indicator with the catalog defaults for the missing ones, in the catalog order. */
export function withDefaults(definition: ChartIndicatorDefinition, parameters: Record<string, number>): Record<string, number> {
  return Object.fromEntries(definition.parameters.map((parameter) => [parameter.name, parameters[parameter.name] ?? parameter.default]));
}
