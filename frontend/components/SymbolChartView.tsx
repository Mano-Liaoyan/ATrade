'use client';

import type { InstrumentIdentityInput } from '../lib/instrumentIdentity';
import { formatMarketDataSourceLabel, useSymbolChartWorkflow } from '../lib/symbolChartWorkflow';
import { AnalysisPanel } from './AnalysisPanel';
import { BrokerPaperStatus } from './BrokerPaperStatus';
import { CandlestickChart } from './CandlestickChart';
import { IndicatorPanel } from './IndicatorPanel';
import { SymbolSearch } from './SymbolSearch';
import { TimeframeSelector } from './TimeframeSelector';

type SymbolChartViewProps = {
  symbol: string;
  identity?: InstrumentIdentityInput | null;
};

export function SymbolChartView({ symbol, identity }: SymbolChartViewProps) {
  const chart = useSymbolChartWorkflow({ symbol, identity });

  return (
    <div className="symbol-chart-layout">
      <section className="workspace-panel chart-view" data-testid="chart-workspace">
        <div className="panel-heading chart-heading">
          <div>
            <p className="eyebrow">Interactive candlestick chart</p>
            <h1>{chart.normalizedSymbol} chart workspace</h1>
          </div>
          <div className="chart-actions">
            <span className={chart.streamState === 'connected' ? 'stream-pill stream-pill--connected' : 'stream-pill'} data-testid="stream-state">
              SignalR {chart.streamState}
            </span>
            <TimeframeSelector value={chart.timeframe} onChange={chart.setTimeframe} />
          </div>
        </div>

        <SymbolSearch
          title="Search another IBKR stock"
          description="Jump from this symbol page to any IBKR/iBeam stock result without relying on a local symbol catalog."
          compact
          limit={6}
        />

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

        <IndicatorPanel indicators={chart.indicators} />

        <AnalysisPanel symbol={chart.normalizedSymbol} timeframe={chart.timeframe} candleSource={chart.candles?.source} />

        <div className="chart-footer-note">
          <p>
            HTTP candles/indicators are refreshed from IBKR/iBeam on demand. SignalR applies IBKR snapshot updates when `/hubs/market-data` is reachable;
            if streaming is unavailable this view falls back to HTTP polling without synthetic fallback data.
          </p>
          {chart.candles ? (
            <p>Current candle source: {formatMarketDataSourceLabel(chart.candles.source)}.</p>
          ) : null}
          {chart.streamState === 'unavailable' ? (
            <p>Streaming snapshots are unavailable; polling continues against the IBKR/iBeam HTTP provider.</p>
          ) : null}
          {chart.latestUpdate ? (
            <p>
              Last market-data stream update: {chart.latestUpdate.symbol} {chart.latestUpdate.timeframe} close {chart.latestUpdate.close.toFixed(2)} from {formatMarketDataSourceLabel(chart.latestUpdate.source)}.
            </p>
          ) : null}
        </div>
      </section>

      <BrokerPaperStatus />
    </div>
  );
}
