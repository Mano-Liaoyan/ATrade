// The last price of an instrument and its change from the previous close, from its daily bars and its live bar.
import { formatSignedNumber, formatSignedPercent, MISSING_VALUE } from '#lib/foundation/value_format';
import { SvelteMap } from 'svelte/reactivity';
import type { Bar } from './bars';
import { formatInstrument, type Instrument } from './instrument_search';

export interface DayQuote {
  last: number;
  change: number | null;
  changePercent: number | null;
}

const PERCENT = 100;
const BARS_BACK_TO_PREVIOUS_DAY = 2;
const DAY_SECONDS = 86_400;

/** 00:00 UTC of the day that contains the time (UNIX seconds). */
function readDayStart(time: number): number {
  return Math.floor(time / DAY_SECONDS) * DAY_SECONDS;
}

/**
 * The last price and its change from the previous close. A live bar (of any bar period) gives the last price. The
 * previous close is the close of the last daily bar before the day of the live bar: a daily bar starts at 00:00 UTC of
 * its trading date. Without a live bar, the last close is the last price. A live bar older than the last daily bar is
 * not used.
 */
export function readDayQuote(dailyBars: readonly Bar[], liveBar: Bar | null = null): DayQuote | null {
  const lastBar = dailyBars.at(-1);
  if (lastBar === undefined) {
    return null;
  }
  const liveDay = liveBar === null ? null : readDayStart(liveBar.time);
  const isNewDay = liveDay !== null && liveDay > lastBar.time;
  const previousBar = isNewDay ? lastBar : dailyBars.at(-BARS_BACK_TO_PREVIOUS_DAY);
  const last = liveBar !== null && liveDay !== null && liveDay >= lastBar.time ? liveBar.close : lastBar.close;
  if (previousBar === undefined) {
    return { last, change: null, changePercent: null };
  }
  const change = last - previousBar.close;
  return { last, change, changePercent: (change / previousBar.close) * PERCENT };
}

// The one latest quote of each instrument in the browser. Each view (the watchlist rows, the header of the instrument
// page, the order panel) reads it, so all show the same numbers, also after a page change.
const latestQuotes = new SvelteMap<string, DayQuote>();

/**
 * Writes the quote of the daily bars and a live bar. A quote with a live bar replaces the quote of the instrument. A
 * quote of the daily bars only is written when the instrument has no quote.
 */
export function writeLatestQuote(instrument: Instrument, dailyBars: readonly Bar[], liveBar: Bar | null): void {
  const key = formatInstrument(instrument);
  const quote = readDayQuote(dailyBars, liveBar);
  if (quote !== null && (liveBar !== null || !latestQuotes.has(key))) {
    latestQuotes.set(key, quote);
  }
}

export function readLatestQuote(instrument: Instrument): DayQuote | null {
  return latestQuotes.get(formatInstrument(instrument)) ?? null;
}

/** "+2.00 (+2.00 %)". */
export function formatDayChange(quote: DayQuote): string {
  if (quote.change === null || quote.changePercent === null) {
    return MISSING_VALUE;
  }
  return `${formatSignedNumber(quote.change)} (${formatSignedPercent(quote.changePercent)})`;
}
