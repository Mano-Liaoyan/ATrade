'use client';

import type { TerminalChartWorkspaceWorkflow } from '@/lib/terminalChartWorkspaceWorkflow';
import { CHART_RANGE_DESCRIPTIONS, CHART_RANGE_LABELS, type ChartRange } from '@/types/marketData';
import { TerminalMetadataGrid } from './TerminalMetadataGrid';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type TerminalInstrumentHeaderProps = {
  chart: TerminalChartWorkspaceWorkflow;
};

export function TerminalInstrumentHeader({ chart }: TerminalInstrumentHeaderProps) {
  return (
    <TerminalPanel
      className="terminal-instrument-header"
      data-testid="terminal-instrument-header"
      density="compact"
      eyebrow="Instrument"
      title={`${chart.normalizedSymbol} · ${chart.view.chartRangeLabel} lookback`}
      description="Exact identity, source, stream, fallback, and range."
      actions={(
        <div className="terminal-instrument-header__actions">
          <TerminalStatusBadge tone={chart.view.streamTone}>{chart.view.streamLabel}</TerminalStatusBadge>
          <TerminalStatusBadge tone={chart.view.identity ? 'success' : 'warning'}>
            {chart.view.identity ? 'Exact identity' : 'Manual symbol'}
          </TerminalStatusBadge>
        </div>
      )}
    >
      <div className="terminal-instrument-header__grid">
        <div className="terminal-instrument-header__summary">
          <span className="terminal-instrument-header__symbol">{chart.normalizedSymbol}</span>
          <span
            aria-label={`Chart identity details. ${chart.view.hoverDetailsTitle}`}
            className="terminal-instrument-header__hover-chip"
            data-testid="chart-identity-hover-details"
            tabIndex={0}
            title={chart.view.hoverDetailsTitle}
          >
            {chart.view.compactIdentityLabel}
          </span>
          <span
            aria-label={`Chart source details. ${chart.view.hoverDetailsTitle}`}
            className="terminal-instrument-header__hover-chip"
            data-testid="chart-source-hover-details"
            tabIndex={0}
            title={chart.view.hoverDetailsTitle}
          >
            {chart.view.compactSourceLabel}
          </span>
          {chart.view.compactStateLabel ? <span className="terminal-instrument-header__state-label">{chart.view.compactStateLabel}</span> : null}
          <span>{chart.view.chartRangeDescription}</span>
        </div>

        <TerminalMetadataGrid
          ariaLabel="Chart Exact Instrument Identity metadata"
          className="terminal-instrument-header__identity"
          columns={3}
          items={chart.view.identityRows.map((row) => ({
            code: row.code,
            label: row.label,
            value: row.value,
          }))}
          testId="terminal-chart-identity"
        />
      </div>

      <div id="terminal-chart-range" className="terminal-chart-range-controls" aria-label="Chart range lookback controls" data-testid="chart-range-controls">
        <span className="terminal-chart-range-controls__help" data-testid="chart-range-help">
          {chart.view.rangeHelpCopy}
        </span>
        <div className="terminal-chart-range-controls__buttons" role="group" aria-label="Supported lookback ranges from now">
          {chart.view.supportedRanges.map((chartRange) => (
            <RangeButton
              active={chartRange === chart.chartRange}
              chartRange={chartRange}
              key={chartRange}
              onChange={chart.setChartRange}
            />
          ))}
        </div>
      </div>
    </TerminalPanel>
  );
}

function RangeButton({
  active,
  chartRange,
  onChange,
}: {
  active: boolean;
  chartRange: ChartRange;
  onChange: (chartRange: ChartRange) => void;
}) {
  return (
    <button
      aria-label={CHART_RANGE_DESCRIPTIONS[chartRange]}
      aria-pressed={active}
      className={active ? 'terminal-chart-range-button terminal-chart-range-button--active' : 'terminal-chart-range-button'}
      data-chart-range={chartRange}
      title={CHART_RANGE_DESCRIPTIONS[chartRange]}
      type="button"
      onClick={() => onChange(chartRange)}
    >
      {CHART_RANGE_LABELS[chartRange]}
    </button>
  );
}
