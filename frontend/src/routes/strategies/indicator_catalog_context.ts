// The indicator catalog of the rule builder (docs/architecture/indicator.md section 23.10). RulesTab reads it once. Each
// RuleOperand, at any depth of the rule groups, gets it from this context.
import { getContext, setContext } from 'svelte';
import type { CatalogIndicator } from '#lib/strategy';

type IndicatorCatalogReader = () => CatalogIndicator[];

const CONTEXT_KEY = Symbol('indicator catalog');

export function provideIndicatorCatalog(reader: IndicatorCatalogReader): void {
  setContext(CONTEXT_KEY, reader);
}

export function readIndicatorCatalog(): IndicatorCatalogReader {
  return getContext<IndicatorCatalogReader | undefined>(CONTEXT_KEY) ?? (() => []);
}
