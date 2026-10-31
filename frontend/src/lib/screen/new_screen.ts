// The screen of the "New screen" button of the "Screens" side column (docs/architecture/screen.md section 24.13): a US
// screen of the quarter universe with no filters and no indicator conditions. The definition requires an order
// (section 24.4.1), so the new screen has the order Avg trading value (20), high first.
import type { ScreenDefinition } from './condition_bar';
import type { ScreenMarket } from './screen_draft';

const NEW_SCREEN_NAME = 'New screen';

/** "New screen", or "New screen N" with the first N from 2 that is not in use. */
export function nameNewScreen(names: readonly string[]): string {
  const usedNames = new Set(names);
  let candidate = NEW_SCREEN_NAME;
  for (let number = 2; usedNames.has(candidate); number += 1) {
    candidate = `${NEW_SCREEN_NAME} ${String(number)}`;
  }
  return candidate;
}

/** The body of `POST /api/screens` for a new screen. `names` are the names of the screens that exist. */
export function newScreen(names: readonly string[]): {
  name: string;
  market: ScreenMarket;
  definition: ScreenDefinition;
} {
  return {
    name: nameNewScreen(names),
    market: 'US',
    definition: {
      start: 'quarter_universe',
      filters: [],
      indicator_conditions: [],
      order: {
        indicator: { indicator: 'average_trading_value', parameters: { period: 20 }, output: 'value' },
        direction: 'descending',
      },
    },
  };
}
