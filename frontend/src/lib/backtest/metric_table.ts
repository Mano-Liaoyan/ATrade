// The rows of the Metrics table of a backtest (docs/architecture/backtest.md sections 10.9.2, 10.9.3, and 10.9.6):
// the metrics of section 10.9.2, each with its name, its definition for the name tooltip, and one value for each set
// of metrics (a column of the table). The API gives a metric without a meaning as null and its reason in
// `missing_reasons`: the value is "–" and its tooltip gives the reason.
import { formatSignedNumber, formatSignedPercent, MISSING_VALUE } from '#lib/foundation/value_format';
import type { BacktestMetrics } from './backtest_api';
import { formatRatio, formatUnsignedPercent } from './backtest_format';

/** One cell of a value column. `reason` is set only for a "–" value with a reason of the API. */
export interface MetricTableValue {
  text: string;
  reason?: string;
}

export interface MetricTableRow {
  name: string;
  /** The definition and "Risk-free rate: 0": the tooltip of the name. */
  definition: string;
  values: MetricTableValue[];
}

type MetricField = Exclude<keyof BacktestMetrics, 'missing_reasons' | 'trade_count'>;

interface MetricSpec {
  name: string;
  definition: string;
  /** The field that is null when the metric has no value. Its reason names the "–" value. */
  field: MetricField;
  format: (metrics: BacktestMetrics) => string;
}

const RISK_FREE_RATE = 'Risk-free rate: 0';

function readNumber(value: string | null): number | null {
  return value === null ? null : Number(value);
}

function formatAverageWin(metrics: BacktestMetrics): string {
  const percent = formatSignedPercent(readNumber(metrics.average_win_percent));
  return `${formatSignedNumber(readNumber(metrics.average_win_usd))} (${percent})`;
}

function formatTurnover(metrics: BacktestMetrics): string {
  return `${formatRatio(metrics.turnover_per_year)}× per year`;
}

const METRIC_SPECS: readonly MetricSpec[] = [
  {
    name: 'CAGR',
    definition: '(Final equity / paper capital)^(1 / years) − 1. Years: calendar days of the range / 365.25',
    field: 'cagr_percent',
    format: (metrics) => formatSignedPercent(readNumber(metrics.cagr_percent)),
  },
  {
    name: 'Annual volatility',
    definition: 'Sample standard deviation of the daily returns × √252',
    field: 'annual_volatility_percent',
    format: (metrics) => formatUnsignedPercent(metrics.annual_volatility_percent),
  },
  {
    name: 'Sharpe ratio',
    definition: 'Mean of the daily returns / standard deviation of the daily returns × √252',
    field: 'sharpe_ratio',
    format: (metrics) => formatRatio(metrics.sharpe_ratio),
  },
  {
    name: 'Sortino ratio',
    definition: 'Mean of the daily returns / downside deviation of all daily returns × √252',
    field: 'sortino_ratio',
    format: (metrics) => formatRatio(metrics.sortino_ratio),
  },
  {
    name: 'Calmar ratio',
    definition: 'CAGR / max drawdown',
    field: 'calmar_ratio',
    format: (metrics) => formatRatio(metrics.calmar_ratio),
  },
  {
    name: 'Profit factor',
    definition: 'Sum of the profits of the round trips with a profit / sum of the losses of the round trips with a loss',
    field: 'profit_factor',
    format: (metrics) => formatRatio(metrics.profit_factor),
  },
  {
    name: 'Win rate',
    definition: 'Round trips with a profit after commissions / all round trips',
    field: 'win_rate_percent',
    format: (metrics) => formatUnsignedPercent(metrics.win_rate_percent),
  },
  {
    name: 'Average win (USD)',
    definition: 'Mean profit of the round trips with a profit, also as a percent of the entry amount',
    field: 'average_win_usd',
    format: formatAverageWin,
  },
  {
    name: 'Average loss (USD)',
    definition: 'Mean profit of the round trips with a loss',
    field: 'average_loss_usd',
    format: (metrics) => formatSignedNumber(readNumber(metrics.average_loss_usd)),
  },
  {
    name: 'Exposure',
    definition: 'Bars with a position / all bars of the range',
    field: 'exposure_percent',
    format: (metrics) => formatUnsignedPercent(metrics.exposure_percent),
  },
  {
    name: 'Turnover',
    definition: 'Amount of all fills / mean equity / years',
    field: 'turnover_per_year',
    format: formatTurnover,
  },
];

function readValue(spec: MetricSpec, metrics: BacktestMetrics): MetricTableValue {
  if (metrics[spec.field] !== null) {
    return { text: spec.format(metrics) };
  }
  const reason = metrics.missing_reasons[spec.field];
  return reason === undefined ? { text: MISSING_VALUE } : { text: MISSING_VALUE, reason };
}

/** The rows of the Metrics table, with one value for each set of metrics in `metricSets`. */
export function readMetricRows(metricSets: readonly BacktestMetrics[]): MetricTableRow[] {
  return METRIC_SPECS.map((spec) => ({
    name: spec.name,
    definition: `${spec.definition}. ${RISK_FREE_RATE}`,
    values: metricSets.map((metrics) => readValue(spec, metrics)),
  }));
}
