// Labels and values that the backtest pages show.
import type { StatusKind } from '#lib/foundation/carbon';
import { formatSignedPercent, MISSING_VALUE } from '#lib/foundation/value_format';
import type { BacktestStatus } from './backtest_api';

const STATUS_LABELS: Record<BacktestStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  finished: 'Finished',
  failed: 'Failed',
  timed_out: 'Timed out',
  cancelled: 'Cancelled',
};
// The status indicator kind of each status. The indicator also shows an icon and the status word, so the color is
// never the only sign.
const STATUS_KINDS: Record<BacktestStatus, StatusKind> = {
  queued: 'neutral',
  running: 'in-progress',
  finished: 'success',
  failed: 'error',
  timed_out: 'warning',
  cancelled: 'neutral',
};
const FINAL_STATUSES: readonly BacktestStatus[] = ['finished', 'failed', 'timed_out', 'cancelled'];
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

/** "1.6" gives "+1.60 %", "-1.02" gives "-1.02 %": formatSignedPercent (foundation/value_format). */
export function formatPercent(percent: string): string {
  return formatSignedPercent(Number(percent));
}

/**
 * The one sign rule of the max drawdown on all pages (spec #99): the API gives a positive percent ("37.71"), the pages
 * show a loss as a negative percent ("-37.71 %"). `change` is the signed number for ChangeText or MetricTile; 0 stays 0.
 */
export function formatMaxDrawdown(maxDrawdownPercent: string): { text: string; change: number } {
  const drawdown = Number(maxDrawdownPercent);
  const change = drawdown === 0 ? 0 : -drawdown;
  return { text: formatPercent(String(change)), change };
}

export function formatUsd(amount: string): string {
  return AMOUNT_FORMAT.format(Number(amount));
}

/** A ratio of the API with 2 decimal places ("1.23"), or "–" for null. */
export function formatRatio(ratio: string | null): string {
  return ratio === null ? MISSING_VALUE : AMOUNT_FORMAT.format(Number(ratio));
}

/** A share of the API without a sign ("66.67 %"), or "–" for null. */
export function formatUnsignedPercent(percent: string | null): string {
  return percent === null ? MISSING_VALUE : `${AMOUNT_FORMAT.format(Number(percent))} %`;
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
