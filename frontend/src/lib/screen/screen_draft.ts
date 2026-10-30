// The changed, unsaved screen of the screen page (docs/architecture/screen.md section 24.13). The page runs the draft
// at once after each change; the saved screen changes only on "Save screen" or "Save as new screen".
import type { ScreenDefinition } from './condition_bar';

export type ScreenMarket = 'US' | 'HK';
export type RemovableGroup = 'Filters' | 'Indicator conditions';

export interface ScreenDraft {
  market: string;
  definition: ScreenDefinition;
}

// The start instruments that a market switch selects (section 24.2).
const MARKET_START: Record<ScreenMarket, string> = { US: 'quarter_universe', HK: 'hk_instrument_list' };

function items(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function removeCondition(definition: ScreenDefinition, group: RemovableGroup, index: number): ScreenDefinition {
  const key = group === 'Filters' ? 'filters' : 'indicator_conditions';
  return { ...definition, [key]: items(definition[key]).filter((_, itemIndex) => itemIndex !== index) };
}

/** The exchanges of one market do not apply to the other market, so the switch removes the exchange filters. */
export function switchMarket(definition: ScreenDefinition, market: ScreenMarket): ScreenDefinition {
  return {
    ...definition,
    start: MARKET_START[market],
    filters: items(definition.filters).filter(
      (filter) => (filter as Record<string, unknown> | null)?.['field'] !== 'exchange',
    ),
  };
}

export function isDraftChanged(saved: ScreenDraft, draft: ScreenDraft): boolean {
  return saved.market !== draft.market || JSON.stringify(saved.definition) !== JSON.stringify(draft.definition);
}
