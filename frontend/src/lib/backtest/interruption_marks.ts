// The bar ends that the equity chart marks grey: a forward test has no record of these bars
// (docs/architecture/forward_test.md section 12.10). The chart can mark only times that a curve has.
import type { EquityPoint } from './backtest_api';

export interface TimeInterval {
  start_utc: string;
  end_utc: string;
}

function isInInterval(timeMilliseconds: number, interval: TimeInterval): boolean {
  return timeMilliseconds > Date.parse(interval.start_utc) && timeMilliseconds <= Date.parse(interval.end_utc);
}

/** The bar ends of the curves after an interruption start, up to and with its end. Sorted, each one time. */
export function findInterruptedTimes(
  curves: readonly (readonly Pick<EquityPoint, 'time_utc'>[])[],
  interruptions: readonly TimeInterval[],
): string[] {
  const timesByMilliseconds = new Map<number, string>();
  for (const point of curves.flat()) {
    const timeMilliseconds = Date.parse(point.time_utc);
    if (interruptions.some((interval) => isInInterval(timeMilliseconds, interval))) {
      timesByMilliseconds.set(timeMilliseconds, point.time_utc);
    }
  }
  const sortedMilliseconds = [...timesByMilliseconds.keys()].sort((first, second) => first - second);
  return sortedMilliseconds.map((timeMilliseconds) => timesByMilliseconds.get(timeMilliseconds) ?? '');
}
