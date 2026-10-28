// PROTOTYPE (#99), throwaway: the last price and the change of an instrument, from its 1-DAY bars.
import type { Bar } from '#lib/market_data';

export interface DayQuote {
  last: number;
  change: number | null;
  changePercent: number | null;
}

export type ChangeDirection = 'up' | 'down' | 'flat';

const PERCENT = 100;
const PRICE_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const CHANGE_FORMAT = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
const MISSING_VALUE = '–';
const BARS_BACK_TO_PREVIOUS = 2;

// The last close is the last price. The change is from the close of the bar before it.
export function readDayQuote(bars: readonly Bar[], liveBar: Bar | null = null): DayQuote | null {
  const lastBar = bars.at(-1);
  if (lastBar === undefined) {
    return null;
  }
  const isNewBar = liveBar !== null && liveBar.time > lastBar.time;
  const previousBar = isNewBar ? lastBar : bars.at(-BARS_BACK_TO_PREVIOUS);
  const last = liveBar?.close ?? lastBar.close;
  if (previousBar === undefined) {
    return { last, change: null, changePercent: null };
  }
  const change = last - previousBar.close;
  return { last, change, changePercent: (change / previousBar.close) * PERCENT };
}

export function findChangeDirection(change: number | null): ChangeDirection {
  if (change === null || change === 0) {
    return 'flat';
  }
  return change > 0 ? 'up' : 'down';
}

export function formatPrice(price: number | null): string {
  return price === null ? MISSING_VALUE : PRICE_FORMAT.format(price);
}

export function formatChange(quote: DayQuote): string {
  if (quote.change === null || quote.changePercent === null) {
    return MISSING_VALUE;
  }
  return `${CHANGE_FORMAT.format(quote.change)} (${CHANGE_FORMAT.format(quote.changePercent)}%)`;
}

// Decimal text from the backend, with its sign. "–" when there is no value.
export function formatSignedAmount(amount: string | null): string {
  if (amount === null) {
    return MISSING_VALUE;
  }
  return CHANGE_FORMAT.format(Number(amount));
}

export function findAmountDirection(amount: string | null): ChangeDirection {
  return findChangeDirection(amount === null ? null : Number(amount));
}
