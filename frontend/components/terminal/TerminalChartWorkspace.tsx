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
    <section className={cn('terminal-chart-workspace workspace-stack', className)} data-testid="terminal-chart-workspace">
      <TerminalInstrumentHeader chart={chart} />

      <section className="workspace-panel terminal-data-panel chart-view terminal-chart-workspace__market-grid" data-testid="chart-workspace">
        <div className="terminal-chart-workspace__chart-region">
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
          {!chart.loading && !chart.error && chart.candles ? <CandlestickChart candles={chart.candles} indicators={chart.indicators} /> : null}
          {!chart.loading && !chart.error && !chart.candles ? (
            <div className="empty-state" role="status">
              <strong>No candle data returned.</strong>
              <p>The provider returned an empty response for this lookback range; no synthetic chart data is shown.</p>
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
    <div className="chart-footer-note">
      <p>
        HTTP candles/indicators are refreshed for the selected lookback range from now. {chart.view.fallbackCopy}
      </p>
      {chart.candles ? <p>Current candle source: {chart.view.candleSourceLabel}.</p> : null}
      {chart.streamState === 'unavailable' ? (
        <p>Streaming snapshots are unavailable; polling continues against the IBKR/iBeam HTTP provider.</p>
      ) : null}
      {chart.latestUpdate ? (
        <p>
          Last market-data stream update: {chart.latestUpdate.symbol} {chart.latestUpdate.timeframe} range close {chart.latestUpdate.close.toFixed(2)} from {chart.view.latestUpdateSourceLabel ?? chart.view.candleSourceLabel}.
        </p>
      ) : null}
      <p>{chart.view.identitySummary}</p>
      <p>{chart.view.noOrderCopy}</p>
    </div>
  );
}
