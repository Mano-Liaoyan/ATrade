// The bars and the indicator values of a backtest or forward test chart (docs/architecture/indicator.md section
// 23.9.8). The bars route and the series route refuse a range of more than MAX_BARS_PER_REQUEST bar lengths, so a long
// run range is read in consecutive windows, one after the other, and the answers are joined.
import type { RequestResult } from '#lib/foundation/http_request';
import { readBars, type Bar, type BarPeriod, type BarsRange, type BarsResult } from './bars';
import { readIndicatorSeries, type IndicatorSeriesRequest, type IndicatorSeriesResult } from './indicator_series';
import type { Instrument } from './instrument_search';
import { BAR_PERIOD_SECONDS } from './trade_marks';

/** The same limit as `MAX_BARS_PER_REQUEST` in backend `market_data/bar_models.py`. */
export const MAX_BARS_PER_REQUEST = 20_000;

const MILLISECONDS_PER_SECOND = 1000;

/** A time range in UNIX seconds; the end is not included. */
export interface TimeWindow {
  start: number;
  end: number;
}

/** Consecutive windows from `start` to `end` (UNIX seconds), each at most MAX_BARS_PER_REQUEST bar lengths. */
export function splitTimeRange(start: number, end: number, barPeriod: BarPeriod): TimeWindow[] {
  const windowLength = MAX_BARS_PER_REQUEST * BAR_PERIOD_SECONDS[barPeriod];
  const windows: TimeWindow[] = [];
  for (let windowStart = start; windowStart < end; windowStart += windowLength) {
    windows.push({ start: windowStart, end: Math.min(windowStart + windowLength, end) });
  }
  return windows.length === 0 ? [{ start, end }] : windows;
}

function toIsoTime(unixSeconds: number): string {
  return new Date(unixSeconds * MILLISECONDS_PER_SECOND).toISOString();
}

/** The bars route ranges of the run range: the first keeps `startUtc`, the last keeps `endUtc` (or no end). */
function splitBarsRange(barPeriod: BarPeriod, range: BarsRange, nowMilliseconds: number): BarsRange[] {
  const start = Date.parse(range.startUtc) / MILLISECONDS_PER_SECOND;
  const end = Date.parse(range.endUtc ?? new Date(nowMilliseconds).toISOString()) / MILLISECONDS_PER_SECOND;
  const windows = splitTimeRange(start, end, barPeriod);
  return windows.map((window, index) => {
    const endUtc = index === windows.length - 1 ? range.endUtc : toIsoTime(window.end);
    return {
      startUtc: index === 0 ? range.startUtc : toIsoTime(window.start),
      ...(endUtc === undefined ? {} : { endUtc }),
      ...(range.sourceOrder === undefined ? {} : { sourceOrder: range.sourceOrder }),
    };
  });
}

/** Reads the bars of the run range. Without `endUtc`, the range ends now, and the last window sends no end. */
export async function readRunBars(
  fetchFunction: typeof fetch,
  instrument: Instrument,
  barPeriod: BarPeriod,
  range: BarsRange,
  nowMilliseconds = Date.now(),
): Promise<BarsResult> {
  const bars: Bar[] = [];
  for (const windowRange of splitBarsRange(barPeriod, range, nowMilliseconds)) {
    const result = await readBars(fetchFunction, instrument, barPeriod, windowRange);
    if (result.kind === 'failed') {
      return result;
    }
    // The route widens each window to whole bars, so a bar at a window border can come 2 times.
    const lastTime = bars.at(-1)?.time ?? Number.NEGATIVE_INFINITY;
    bars.push(...result.bars.filter((bar) => bar.time > lastTime));
  }
  return { kind: 'loaded', bars };
}

/** Reads the indicator values from the first to the last bar in windows and joins the times and the outputs. */
export async function readRunIndicatorSeries(
  fetchFunction: typeof fetch,
  request: IndicatorSeriesRequest,
): Promise<RequestResult<IndicatorSeriesResult>> {
  // `readIndicatorSeries` ends 1 second after the start of its last bar.
  const windows = splitTimeRange(request.firstBarTime, request.lastBarTime + 1, request.barPeriod);
  let joined: IndicatorSeriesResult | null = null;
  for (const window of windows) {
    const result = await readIndicatorSeries(fetchFunction, { ...request, firstBarTime: window.start, lastBarTime: window.end - 1 });
    if (result.kind === 'failed') {
      return result;
    }
    joined = joined === null ? result.value : joinSeries(joined, result.value);
  }
  return { kind: 'ok', value: joined ?? { times: [], series: [] } };
}

function joinSeries(before: IndicatorSeriesResult, after: IndicatorSeriesResult): IndicatorSeriesResult {
  const lastTime = before.times.at(-1) ?? Number.NEGATIVE_INFINITY;
  const firstNew = after.times.findIndex((time) => time > lastTime);
  const from = firstNew === -1 ? after.times.length : firstNew;
  return {
    times: [...before.times, ...after.times.slice(from)],
    series: before.series.map((series, index) => {
      const afterOutputs = after.series[index]?.outputs ?? {};
      return {
        ...series,
        outputs: Object.fromEntries(
          Object.entries(series.outputs).map(([output, values]) => [output, [...values, ...(afterOutputs[output] ?? []).slice(from)]]),
        ),
      };
    }),
  };
}
