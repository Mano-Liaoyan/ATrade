'use client';

import { CandlestickChart } from '@/components/CandlestickChart';
import type { InstrumentIdentityInput } from '@/lib/instrumentIdentity';
import type { TerminalChartWorkspaceWorkflow } from '@/lib/terminalChartWorkspaceWorkflow';
import { cn } from '@/lib/utils';
import { TerminalAnalysisWorkspace } from './TerminalAnalysisWorkspace';
import { TerminalIndicatorGrid } from './TerminalIndicatorGrid';
import { TerminalInstrumentHeader } from './TerminalInstrumentHeader';

export type TerminalChartWorkspaceProps = {
  chart: TerminalChartWorkspaceWorkflow;
  className?: string;
  identity?: InstrumentIdentityInput | null;
  includeAnalysis?: boolean;
};

export function TerminalChartWorkspace({
  chart,
  className,
  identity = null,
  includeAnalysis = true,
}: TerminalChartWorkspaceProps) {
  return (
    <section className={cn('terminal-chart-workspace terminal-module-scroll-surface workspace-stack', className)} data-scroll-owner="chart-module" data-testid="terminal-chart-workspace">
      <TerminalInstrumentHeader chart={chart} />

      <section className="workspace-panel terminal-data-panel chart-view terminal-chart-workspace__market-grid" data-testid="chart-workspace">
        <div className="terminal-chart-workspace__chart-region terminal-scroll-owned" data-scroll-owner="chart-workspace-region">
          <div className="panel-heading chart-heading terminal-panel-heading">
            <div>
              <p className="eyebrow">Lookback candlestick chart</p>
              <h2>{chart.normalizedSymbol} candles</h2>
              <p>Current source: {chart.view.candleSourceLabel}. Chart controls request the selected lookback range from now.</p>
            </div>
            <div className="chart-actions">
              <span className={chart.streamState === 'connected' ? 'stream-pill stream-pill--connected' : 'stream-pill'} data-testid="stream-state">
                {chart.view.streamLabel}
              </span>
              <span className="pill">{chart.view.chartRangeLabel} lookback</span>
            </div>
          </div>

          {chart.loading ? <div className="loading-state" role="status">Loading OHLC candlestick chart data…</div> : null}
          {!chart.loading && chart.error ? (
            <div className="error-state" role="alert">
              <strong>IBKR chart data unavailable.</strong>
              <p>{chart.error}</p>
              <button className="primary-button" type="button" onClick={() => void chart.refreshChartData(true)}>
                Retry chart data
              </button>
            </div>
          ) : null}
          {!chart.loading && !chart.error && chart.view.staleCandleSourceWarning ? (
            <div className="warning-state" role="status" data-testid="stale-chart-source-warning">
              <strong>Stale Timescale cache shown.</strong>
              <p>{chart.view.staleCandleSourceWarning}</p>
            </div>
          ) : null}
          {!chart.loading && !chart.error && chart.candles && chart.view.hasCandleData ? <CandlestickChart candles={chart.candles} indicators={chart.indicators} /> : null}
          {!chart.loading && !chart.error && (!chart.candles || !chart.view.hasCandleData) ? (
            <div className="empty-state" role="status">
              <strong>No candle data returned.</strong>
              <p>The provider returned no candle rows for this lookback range; no synthetic chart data is shown.</p>
            </div>
          ) : null}
          <ChartFooter chart={chart} />
        </div>

        <TerminalIndicatorGrid chart={chart} />
      </section>

      {includeAnalysis ? (
        <section id="terminal-analysis" tabIndex={-1} aria-label="Provider-neutral analysis entry point">
          <TerminalAnalysisWorkspace symbol={chart.normalizedSymbol} chartRange={chart.chartRange} candleSource={chart.candles?.source} identity={chart.view.identity ?? identity} />
        </section>
      ) : null}
    </section>
  );
}

function ChartFooter({ chart }: { chart: TerminalChartWorkspaceWorkflow }) {
  return (
    <div className="chart-footer-note chart-footer-note--compact">
      <p>
        Read-only chart: selected lookback refreshes through API data only; no synthetic bars or order-entry controls are shown.
      </p>
      {chart.latestUpdate ? (
        <p>
          Latest stream close {chart.latestUpdate.close.toFixed(2)} · hover the stock ID/source chips for identity, source, range, cache, and fallback details.
        </p>
      ) : null}
    </div>
  );
}
