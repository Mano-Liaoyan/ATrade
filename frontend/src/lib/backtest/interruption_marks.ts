// The bar ends that the equity chart marks grey: a forward test has no record of these bars
// (docs/architecture/forward_test.md section 12.10). The chart marks a time on its time scale: the bar ends of the
// curves in an interruption, or, when no curve has a bar end in it (one forward test curve), the interruption end.
import type { EquityPoint } from './backtest_api';

export interface TimeInterval {
  start_utc: string;
  end_utc: string;
}

function isInInterval(timeMilliseconds: number, interval: TimeInterval): boolean {
  return timeMilliseconds > Date.parse(interval.start_utc) && timeMilliseconds <= Date.parse(interval.end_utc);
}

/**
 * The bar ends of the curves after an interruption start, up to and with its end. An interruption without a bar end of
 * a curve gives its end time, so the chart shows a grey column there too. Sorted, each one time.
 */
export function findInterruptedTimes(
  curves: readonly (readonly Pick<EquityPoint, 'time_utc'>[])[],
  interruptions: readonly TimeInterval[],
): string[] {
  const timesByMilliseconds = new Map<number, string>();
  const points = curves.flat();
  for (const interval of interruptions) {
    const intervalPoints = points.filter((point) => isInInterval(Date.parse(point.time_utc), interval));
    for (const point of intervalPoints) {
      timesByMilliseconds.set(Date.parse(point.time_utc), point.time_utc);
    }
    if (intervalPoints.length === 0 && points.length > 0) {
      timesByMilliseconds.set(Date.parse(interval.end_utc), interval.end_utc);
    }
  }
  const sortedMilliseconds = [...timesByMilliseconds.keys()].sort((first, second) => first - second);
  return sortedMilliseconds.map((timeMilliseconds) => timesByMilliseconds.get(timeMilliseconds) ?? '');
}
