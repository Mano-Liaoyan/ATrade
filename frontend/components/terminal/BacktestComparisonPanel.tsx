'use client';

import {
  type TerminalBacktestComparisonCurve,
  type TerminalBacktestComparisonRunSummary,
  type TerminalBacktestWorkflow,
} from '@/lib/terminalBacktestWorkflow';
import { Button } from '../ui/button';
import { TerminalStatusBadge } from './TerminalStatusBadge';

const CHART_WIDTH = 720;
const CHART_HEIGHT = 260;
const CHART_PADDING = {
  top: 18,
  right: 24,
  bottom: 32,
  left: 48,
};

type BacktestComparisonPanelProps = {
  workflow: TerminalBacktestWorkflow;
};

type ChartScale = {
  minTime: number;
  maxTime: number;
  minReturn: number;
  maxReturn: number;
};

export function BacktestComparisonPanel({ workflow }: BacktestComparisonPanelProps) {
  const comparison = workflow.comparison;
  const selectedSummaries = comparison.selectedSummaries;
  const selectedCount = selectedSummaries.length;
  const missingBenchmarkCount = selectedSummaries.filter((summary) => !summary.benchmarkCurve).length;

  return (
    <div className="terminal-backtest-comparison" data-testid="backtest-comparison-panel">
      <div className="terminal-backtest-comparison__header">
        <div>
          <span>Saved-run comparison</span>
          <strong>{selectedCount} selected · {comparison.eligibleRuns.length} eligible completed runs</strong>
          <small>{workflow.comparisonCopy}</small>
        </div>
        <div className="terminal-backtest-comparison__actions">
          <TerminalStatusBadge tone={comparison.hasMinimumSelection ? 'success' : 'warning'} data-testid="backtest-comparison-selection-status">
            {comparison.hasMinimumSelection ? 'Comparison ready' : 'Select 2 completed runs'}
          </TerminalStatusBadge>
          <Button data-testid="backtest-comparison-clear-button" disabled={selectedCount === 0} onClick={workflow.clearComparisonSelection} size="sm" type="button" variant="ghost">
            Clear comparison
          </Button>
        </div>
      </div>

      {comparison.eligibleRuns.length === 0 ? (
        <div className="terminal-backtest-comparison__empty" data-testid="backtest-comparison-no-eligible-runs" role="status">
          <strong>No comparable saved runs yet.</strong>
          <span>Queued, running, failed, and cancelled runs remain visible in history, but comparison requires completed /api/backtests result envelopes with persisted strategy equity curve points.</span>
        </div>
      ) : null}

      {!comparison.hasMinimumSelection ? (
        <div className="terminal-backtest-comparison__empty" data-testid="backtest-comparison-empty-state" role="status">
          <strong>Choose completed history rows to compare.</strong>
          <span>{comparison.emptyState || 'Select completed saved runs from history to compare their persisted metrics and curves.'}</span>
        </div>
      ) : null}

      {selectedCount > 0 ? (
        <div className="terminal-backtest-comparison__cards" data-testid="backtest-comparison-selected-cards" aria-label="Selected backtest runs">
          {selectedSummaries.map((summary) => (
            <article className="terminal-backtest-comparison__card" key={summary.runId}>
              <div>
                <span>{summary.symbol}</span>
                <strong>{summary.strategyLabel}</strong>
                <small>{summary.chartRangeLabel} · {summary.capitalSourceLabel} · {summary.statusLabel}</small>
              </div>
              <div>
                <span>Return</span>
                <strong>{formatPercent(summary.totalReturnPercent)}</strong>
                <small>Benchmark {formatPercent(summary.benchmarkReturnPercent)}</small>
              </div>
              <Button data-testid="backtest-comparison-remove-run" onClick={() => workflow.removeComparisonRunSelection(summary.runId)} size="sm" type="button" variant="ghost">
                Remove
              </Button>
            </article>
          ))}
        </div>
      ) : null}

      {comparison.hasMinimumSelection ? (
        <>
          <ComparisonMetricsTable summaries={selectedSummaries} />
          <ComparisonEquityOverlay curves={comparison.curves} summaries={selectedSummaries} />
          {missingBenchmarkCount > 0 ? (
            <div className="terminal-backtest-comparison__empty" data-testid="backtest-comparison-benchmark-empty" role="status">
              <strong>Benchmark curve unavailable for {missingBenchmarkCount} selected run{missingBenchmarkCount === 1 ? '' : 's'}.</strong>
              <span>Only persisted buy-and-hold benchmark curves from completed result envelopes are drawn; no synthetic benchmark is generated in the browser.</span>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function ComparisonMetricsTable({ summaries }: { summaries: TerminalBacktestComparisonRunSummary[] }) {
  return (
    <div className="terminal-backtest-comparison__table-wrap" data-testid="backtest-comparison-metrics">
      <table className="terminal-backtest-comparison__table">
        <caption>Selected completed backtest run metrics from persisted ATrade.Api result payloads.</caption>
        <thead>
          <tr>
            <th scope="col">Strategy</th>
            <th scope="col">Symbol</th>
            <th scope="col">Range</th>
            <th scope="col">Capital source</th>
            <th scope="col">Return</th>
            <th scope="col">Max drawdown</th>
            <th scope="col">Win rate</th>
            <th scope="col">Trades</th>
            <th scope="col">Final equity</th>
            <th scope="col">Benchmark return</th>
            <th scope="col">Status/source</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((summary) => (
            <tr key={summary.runId}>
              <th scope="row">{summary.strategyLabel}</th>
              <td>{summary.symbol}</td>
              <td>{summary.chartRangeLabel}</td>
              <td>{summary.capitalSourceLabel}</td>
              <td>{formatPercent(summary.totalReturnPercent)}</td>
              <td>{formatPercent(summary.maxDrawdownPercent)}</td>
              <td>{formatPercent(summary.winRatePercent, 1)}</td>
              <td>{formatInteger(summary.tradeCount)}</td>
              <td>{formatCurrency(summary.finalEquity, summary.run.capital.currency)}</td>
              <td>{formatPercent(summary.benchmarkReturnPercent)}</td>
              <td>
                <span>{summary.statusLabel}</span>
                <small>{summary.sourceLabel}</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ComparisonEquityOverlay({ curves, summaries }: { curves: TerminalBacktestComparisonCurve[]; summaries: TerminalBacktestComparisonRunSummary[] }) {
  const scale = getChartScale(curves);
  const yLabels = getYAxisLabels(scale);
  const hasCurves = curves.some((curve) => curve.points.length > 0);

  if (!hasCurves) {
    return (
      <div className="terminal-backtest-comparison__empty" data-testid="backtest-comparison-equity-empty" role="status">
        <strong>No persisted equity curve points to draw.</strong>
        <span>The overlay renders only strategy equity and buy-and-hold benchmark points saved in completed /api/backtests result payloads.</span>
      </div>
    );
  }

  return (
    <div className="terminal-backtest-comparison__overlay" data-testid="backtest-equity-overlay">
      <div className="terminal-backtest-comparison__overlay-header">
        <div>
          <span>Equity overlay</span>
          <strong>Strategy equity vs buy-and-hold benchmark</strong>
          <small>Curves are normalized to return percent from each persisted curve baseline so runs with different capital sizes can be compared honestly.</small>
        </div>
      </div>

      <svg
        aria-label={`Strategy equity and buy-and-hold benchmark overlay for ${summaries.length} completed saved backtest runs.`}
        className="terminal-backtest-comparison__svg"
        data-testid="backtest-comparison-equity-svg"
        role="img"
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      >
        <rect className="terminal-backtest-comparison__plot" x={CHART_PADDING.left} y={CHART_PADDING.top} width={plotWidth()} height={plotHeight()} />
        {yLabels.map((label) => {
          const y = yFor(label, scale);
          return (
            <g key={label}>
              <line className="terminal-backtest-comparison__grid-line" x1={CHART_PADDING.left} x2={CHART_WIDTH - CHART_PADDING.right} y1={y} y2={y} />
              <text className="terminal-backtest-comparison__axis-label" x={CHART_PADDING.left - 8} y={y + 4} textAnchor="end">{formatPercent(label)}</text>
            </g>
          );
        })}
        <line className="terminal-backtest-comparison__zero-line" x1={CHART_PADDING.left} x2={CHART_WIDTH - CHART_PADDING.right} y1={yFor(0, scale)} y2={yFor(0, scale)} />
        {curves.map((curve) => (
          <path
            className="terminal-backtest-comparison__curve"
            d={buildPath(curve, scale)}
            fill="none"
            key={curve.id}
            stroke={curve.color}
            strokeDasharray={curve.kind === 'benchmark' ? '7 5' : undefined}
          >
            <title>{curve.label}: {formatPercent(curve.totalReturnPercent)} final return</title>
          </path>
        ))}
      </svg>

      <ul className="terminal-backtest-comparison__legend" data-testid="backtest-comparison-legend" aria-label="Equity overlay legend">
        {curves.map((curve) => (
          <li key={curve.id}>
            <span className="terminal-backtest-comparison__legend-swatch" style={{ backgroundColor: curve.color }} aria-hidden="true" />
            <strong>{curve.kind === 'strategy' ? 'Strategy equity' : 'Buy-and-hold benchmark'}</strong>
            <span>{curve.label} · {formatPercent(curve.totalReturnPercent)} · {curve.points.length} persisted points</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function getChartScale(curves: TerminalBacktestComparisonCurve[]): ChartScale {
  const points = curves.flatMap((curve) => curve.points);
  const minTime = Math.min(...points.map((point) => point.timestamp));
  const maxTime = Math.max(...points.map((point) => point.timestamp));
  const minReturn = Math.min(0, ...points.map((point) => point.normalizedReturnPercent));
  const maxReturn = Math.max(0, ...points.map((point) => point.normalizedReturnPercent));
  const timePadding = minTime === maxTime ? 1 : 0;
  const returnPadding = minReturn === maxReturn ? 1 : Math.max(0.5, (maxReturn - minReturn) * 0.08);

  return {
    minTime: minTime - timePadding,
    maxTime: maxTime + timePadding,
    minReturn: minReturn - returnPadding,
    maxReturn: maxReturn + returnPadding,
  };
}

function getYAxisLabels(scale: ChartScale): number[] {
  const labels = [scale.maxReturn, 0, scale.minReturn].map((value) => Number(value.toFixed(2)));
  return Array.from(new Set(labels));
}

function buildPath(curve: TerminalBacktestComparisonCurve, scale: ChartScale): string {
  return curve.points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(point.timestamp, scale).toFixed(2)} ${yFor(point.normalizedReturnPercent, scale).toFixed(2)}`)
    .join(' ');
}

function xFor(timestamp: number, scale: ChartScale): number {
  const ratio = (timestamp - scale.minTime) / (scale.maxTime - scale.minTime || 1);
  return CHART_PADDING.left + (ratio * plotWidth());
}

function yFor(value: number, scale: ChartScale): number {
  const ratio = (value - scale.minReturn) / (scale.maxReturn - scale.minReturn || 1);
  return CHART_HEIGHT - CHART_PADDING.bottom - (ratio * plotHeight());
}

function plotWidth(): number {
  return CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
}

function plotHeight(): number {
  return CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
}

function formatCurrency(value: number | null, currency = 'USD'): string {
  if (value === null || !Number.isFinite(value)) {
    return 'n/a';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number | null, digits = 2): string {
  return value === null || !Number.isFinite(value) ? 'n/a' : `${value.toFixed(digits)}%`;
}

function formatInteger(value: number | null): string {
  return value === null || !Number.isFinite(value) ? 'n/a' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}
