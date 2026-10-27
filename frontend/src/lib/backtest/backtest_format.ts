// Labels and values that the backtest pages show.
import type { BacktestStatus } from './backtest_api';

const STATUS_LABELS: Record<BacktestStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  finished: 'Finished',
  failed: 'Failed',
  timed_out: 'Timed out',
};
const FINAL_STATUSES: readonly BacktestStatus[] = ['finished', 'failed', 'timed_out'];
const PERCENT_DECIMAL_PLACES = 2;
const AMOUNT_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function describeBacktestStatus(status: BacktestStatus): string {
  return STATUS_LABELS[status];
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
