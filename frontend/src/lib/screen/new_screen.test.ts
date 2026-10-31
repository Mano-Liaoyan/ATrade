import { describe, expect, it } from 'vite-plus/test';
import { nameNewScreen, newScreen } from './new_screen';

describe('newScreen', () => {
  it('is a US screen of the quarter universe with no conditions, ordered by Avg trading value (20), high first', () => {
    expect(newScreen([])).toEqual({
      name: 'New screen',
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
    });
  });
});

describe('nameNewScreen', () => {
  it('is "New screen" when no screen has that name', () => {
    expect(nameNewScreen(['Momentum', 'New screen copy'])).toBe('New screen');
  });

  it('adds the first number that is not in use', () => {
    expect(nameNewScreen(['New screen'])).toBe('New screen 2');
    expect(nameNewScreen(['New screen', 'New screen 2', 'New screen 4'])).toBe('New screen 3');
  });
});
