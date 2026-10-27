// Labels and values that the backtest pages show.
import type { StatusKind } from '#lib/foundation/carbon';
import type { BacktestStatus } from './backtest_api';

const STATUS_LABELS: Record<BacktestStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  finished: 'Finished',
  failed: 'Failed',
  timed_out: 'Timed out',
};
// The status indicator kind of each status. The indicator also shows an icon and the status word, so the color is
// never the only sign.
const STATUS_KINDS: Record<BacktestStatus, StatusKind> = {
  queued: 'neutral',
  running: 'in-progress',
  finished: 'success',
  failed: 'error',
  timed_out: 'warning',
};
const FINAL_STATUSES: readonly BacktestStatus[] = ['finished', 'failed', 'timed_out'];
const PERCENT_DECIMAL_PLACES = 2;
const SECONDS_PER_MINUTE = 60;
const WHOLE_NUMBER_PATTERN = /^\d+$/;
const AMOUNT_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function describeBacktestStatus(status: BacktestStatus): string {
  return STATUS_LABELS[status];
}

export function findBacktestStatusKind(status: BacktestStatus): StatusKind {
  return STATUS_KINDS[status];
}

export function isFinalStatus(status: BacktestStatus): boolean {
  return FINAL_STATUSES.includes(status);
}

// The date input gives YYYY-MM-DD. Backtest ranges start and end at 00:00 UTC, like daily bars.
export function convertDateToUtcStart(date: string): string {
  return `${date}T00:00:00Z`;
}

export function formatPercent(percent: string): string {
  const percentNumber = Number(percent);
  const sign = percentNumber > 0 ? '+' : '';
  return `${sign}${percentNumber.toFixed(PERCENT_DECIMAL_PLACES)} %`;
}

export function formatUsd(amount: string): string {
  return AMOUNT_FORMAT.format(Number(amount));
}

// The backend stores the timeout in seconds. The UI shows and takes it in minutes.
export function formatTimeoutMinutes(timeoutSeconds: number): string {
  return String(timeoutSeconds / SECONDS_PER_MINUTE);
}

// Returns null when the text is not a whole number of minutes above 0.
export function convertTimeoutMinutesToSeconds(minutesText: string): number | null {
  const trimmedText = minutesText.trim();
  if (!WHOLE_NUMBER_PATTERN.test(trimmedText)) {
    return null;
  }
  const minutes = Number(trimmedText);
  if (minutes === 0) {
    return null;
  }
  return minutes * SECONDS_PER_MINUTE;
}
