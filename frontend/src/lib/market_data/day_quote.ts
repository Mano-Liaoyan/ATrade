// The last price of an instrument and its change from the previous close, from its daily bars and its live bar.
import { formatSignedNumber, formatSignedPercent, MISSING_VALUE } from '#lib/foundation/value_format';
import type { Bar } from './bars';

export interface DayQuote {
  last: number;
  change: number | null;
  changePercent: number | null;
}

const PERCENT = 100;
const BARS_BACK_TO_PREVIOUS_DAY = 2;

/** The last close is the last price. A live bar of a new day compares with the last bar; else with the bar before. */
export function readDayQuote(dailyBars: readonly Bar[], liveBar: Bar | null = null): DayQuote | null {
  const lastBar = dailyBars.at(-1);
  if (lastBar === undefined) {
    return null;
  }
  const isNewDay = liveBar !== null && liveBar.time > lastBar.time;
  const previousBar = isNewDay ? lastBar : dailyBars.at(-BARS_BACK_TO_PREVIOUS_DAY);
  const last = liveBar?.close ?? lastBar.close;
  if (previousBar === undefined) {
    return { last, change: null, changePercent: null };
  }
  const change = last - previousBar.close;
  return { last, change, changePercent: (change / previousBar.close) * PERCENT };
}

/** "+2.00 (+2.00 %)". */
export function formatDayChange(quote: DayQuote): string {
  if (quote.change === null || quote.changePercent === null) {
    return MISSING_VALUE;
  }
  return `${formatSignedNumber(quote.change)} (${formatSignedPercent(quote.changePercent)})`;
}
