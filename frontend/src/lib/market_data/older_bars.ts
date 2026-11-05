// Older bars of the instrument page chart (docs/architecture/market_data.md section 8.4). The first read of the bars
// route has the default range of the bar period. When the user scrolls or drags the chart to the left near the first
// bar, the page reads the next older range with an explicit start and end and puts its bars before the chart bars.
// An empty answer means no more history.
import { readBars, type Bar, type BarPeriod, type BarsRange, type BarsResult } from './bars';
import type { Instrument } from './instrument_search';

const SECONDS_PER_DAY = 86_400;
const MILLISECONDS_PER_SECOND = 1000;

/**
 * The length in days of each older range. The same as the default range of the bars route, but 7 days for 1 minute
 * bars: a range of 3 days can have no trading day (a weekend and a holiday), and an empty answer ends the history.
 * Each range has at most MAX_BARS_PER_REQUEST bar lengths.
 */
export const OLDER_BARS_RANGE_DAYS: Record<BarPeriod, number> = {
  '1-MINUTE': 7,
  '5-MINUTE': 10,
  '15-MINUTE': 30,
  '30-MINUTE': 60,
  '1-HOUR': 90,
  '1-DAY': 1096,
};

/** The chart asks for older bars when fewer than this count of bars are left of the visible range. */
export const OLDER_BARS_MARGIN = 10;

function toIsoTime(unixSeconds: number): string {
  return new Date(unixSeconds * MILLISECONDS_PER_SECOND).toISOString();
}

/** The range before the first bar (its start in UNIX seconds). The end is not included. */
export function findOlderBarsRange(firstBarTime: number, barPeriod: BarPeriod): BarsRange {
  return {
    startUtc: toIsoTime(firstBarTime - OLDER_BARS_RANGE_DAYS[barPeriod] * SECONDS_PER_DAY),
    endUtc: toIsoTime(firstBarTime),
  };
}

/** Reads the bars before the first bar. The route widens a range to whole bars, so the first bar is dropped again. */
export async function readOlderBars(
  fetchFunction: typeof fetch,
  instrument: Instrument,
  barPeriod: BarPeriod,
  firstBarTime: number,
): Promise<BarsResult> {
  const result = await readBars(fetchFunction, instrument, barPeriod, findOlderBarsRange(firstBarTime, barPeriod));
  return result.kind === 'loaded' ? { kind: 'loaded', bars: result.bars.filter((bar) => bar.time < firstBarTime) } : result;
}

/** The older bars before the bars, each bar time 1 time. */
export function prependOlderBars(olderBars: readonly Bar[], bars: readonly Bar[]): Bar[] {
  const firstTime = bars.at(0)?.time ?? Number.POSITIVE_INFINITY;
  return [...olderBars.filter((bar) => bar.time < firstTime), ...bars];
}

/** The count of bars that `next` has before the bars of `previous`, or null when `next` is not `previous` with older bars. */
export function countPrependedBars(previous: readonly Bar[], next: readonly Bar[]): number | null {
  const count = next.length - previous.length;
  const firstPrevious = previous.at(0);
  if (firstPrevious === undefined || count <= 0) {
    return null;
  }
  return next[count]?.time === firstPrevious.time && next.at(-1)?.time === previous.at(-1)?.time ? count : null;
}

/** A move of the visible range to the left (`from` is a logical bar index) that comes near the first bar. */
export function isMoveToFirstBar(previousFrom: number | null, from: number): boolean {
  return previousFrom !== null && from < previousFrom && from < OLDER_BARS_MARGIN;
}
