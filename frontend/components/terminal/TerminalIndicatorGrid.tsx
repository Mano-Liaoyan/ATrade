'use client';

import type { TerminalChartWorkspaceWorkflow } from '@/lib/terminalChartWorkspaceWorkflow';

export type TerminalIndicatorGridProps = {
  chart: TerminalChartWorkspaceWorkflow;
};

export function TerminalIndicatorGrid({ chart }: TerminalIndicatorGridProps) {
  const latestMovingAverage = chart.indicators?.movingAverages.at(-1);
  const latestRsi = chart.indicators?.rsi.at(-1);
  const latestMacd = chart.indicators?.macd.at(-1);

  return (
    <aside className="terminal-indicator-grid" aria-label="Chart indicator summary" data-testid="terminal-indicator-grid">
      <div className="terminal-indicator-grid__header">
        <div>
          <p className="eyebrow">Indicators</p>
          <h3>Signal overlays</h3>
        </div>
        <span>{chart.view.indicatorSourceLabel}</span>
      </div>

      {chart.loading ? <p className="terminal-indicator-grid__state" role="status">Loading indicator calculations…</p> : null}
      {!chart.loading && chart.error ? <p className="terminal-indicator-grid__state" role="status">Indicators unavailable until chart data loads.</p> : null}
      {!chart.loading && !chart.error && !chart.view.hasIndicatorData ? <p className="terminal-indicator-grid__state" role="status">No indicator points returned for this lookback yet.</p> : null}

      <div className="terminal-indicator-grid__tiles">
        <IndicatorTile label="SMA 20" value={formatNumber(latestMovingAverage?.sma20)} detail="Short moving average" />
        <IndicatorTile label="SMA 50" value={formatNumber(latestMovingAverage?.sma50)} detail="Long moving average" />
        <IndicatorTile label="RSI" value={formatNumber(latestRsi?.value)} detail="Relative strength index" />
        <IndicatorTile
          label="MACD"
          value={formatNumber(latestMacd?.macd)}
          detail={`Signal ${formatNumber(latestMacd?.signal)} · Hist ${formatNumber(latestMacd?.histogram)}`}
        />
      </div>
    </aside>
  );
}

function IndicatorTile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="terminal-indicator-grid__tile">
      <span className="indicator-label">{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function formatNumber(value: number | undefined): string {
  return typeof value === 'number' ? value.toFixed(2) : '—';
}
