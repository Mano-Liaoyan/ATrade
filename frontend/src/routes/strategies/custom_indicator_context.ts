// The custom indicators of the rule builder (docs/architecture/indicator.md section 23.10). RulesTab reads them once. Each
// RuleOperand, at any depth of the rule groups, gets them from this context.
import { getContext, setContext } from 'svelte';
import type { CustomIndicatorChoice } from '#lib/strategy';

type CustomIndicatorReader = () => CustomIndicatorChoice[];

const CONTEXT_KEY = Symbol('custom indicators');

export function provideCustomIndicators(reader: CustomIndicatorReader): void {
  setContext(CONTEXT_KEY, reader);
}

export function readCustomIndicators(): CustomIndicatorReader {
  return getContext<CustomIndicatorReader | undefined>(CONTEXT_KEY) ?? (() => []);
}
