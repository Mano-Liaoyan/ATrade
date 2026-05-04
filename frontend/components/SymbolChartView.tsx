'use client';

import type { InstrumentIdentityInput } from '../lib/instrumentIdentity';
import { formatMarketDataSourceLabel, useSymbolChartWorkflow } from '../lib/symbolChartWorkflow';
import { CHART_RANGE_LABELS } from '../types/marketData';
import { AnalysisPanel } from './AnalysisPanel';
import { BrokerPaperStatus } from './BrokerPaperStatus';
import { CandlestickChart } from './CandlestickChart';
import { IndicatorPanel } from './IndicatorPanel';
import { SymbolSearch } from './SymbolSearch';
import { TerminalWorkspaceShell } from './TerminalWorkspaceShell';
import { TimeframeSelector } from './TimeframeSelector';

type SymbolChartViewProps = {
  symbol: string;
  identity?: InstrumentIdentityInput | null;
};

export function SymbolChartView({ symbol, identity }: SymbolChartViewProps) {
  const chart = useSymbolChartWorkflow({ symbol, identity });
  const workspaceId = `chart-workspace-${chart.normalizedSymbol.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  const sourceLabel = formatMarketDataSourceLabel(chart.candles?.source);
  const streamTone = chart.streamState === 'connected' ? 'positive' : chart.streamState === 'connecting' ? 'default' : 'warning';

  return (
    <TerminalWorkspaceShell
      workspaceId={workspaceId}
      eyebrow="Lookback candlestick chart"
      title={`${chart.normalizedSymbol} chart workspace`}
      subtitle="Terminal-style chart, provider status, and analysis console"
      description="Chart range controls use lookback windows from now while provider/source metadata, SignalR state, and HTTP fallback notes stay visible."
      navigationLabel={`${chart.normalizedSymbol} chart workspace navigation`}
      navigationItems={[
        {
          id: 'chart-candles',
          label: 'Chart',
          href: '#chart-candles',
          description: 'Candlesticks, indicators, and source notes',
          badge: chart.normalizedSymbol,
        },
        {
          id: 'chart-range',
          label: 'Range',
          href: '#chart-range',
          description: 'Lookback selector from now',
          badge: CHART_RANGE_LABELS[chart.chartRange],
        },
        {
          id: 'chart-analysis',
          label: 'Analysis',
          href: '#chart-analysis',
          description: 'Provider-neutral signal runner',
          badge: 'no orders',
        },
        {
          id: 'chart-provider',
          label: 'Provider',
          href: '#chart-provider',
          description: 'Paper broker status and identity context',
          badge: 'safe',
        },
        {
          id: 'chart-search',
          label: 'Search',
          href: '#chart-search',
          description: 'Jump to another IBKR stock',
          badge: 'IBKR',
        },
      ]}
      commandItems={[
        { label: 'Back to workspace', href: '/' },
        { label: 'Search another', href: '#chart-search' },
        { label: 'Run analysis', href: '#chart-analysis' },
      ]}
      statusItems={[
        { label: 'Symbol', value: chart.normalizedSymbol, tone: 'positive' },
        { label: 'Range', value: CHART_RANGE_LABELS[chart.chartRange] },
        { label: 'SignalR', value: chart.streamState, tone: streamTone },
        { label: 'Source', value: sourceLabel },
      ]}
      commandControls={
        <div id="chart-range" className="chart-command-range" aria-label="Chart range lookback controls">
          <span className="indicator-label">Chart range lookback controls</span>
          <TimeframeSelector value={chart.chartRange} onChange={chart.setChartRange} />
        </div>
      }
      context={{
        eyebrow: 'Chart context',
        title: `${chart.normalizedSymbol} provider map`,
        description: formatChartIdentity(chart),
        metrics: [
          { label: 'Candle source', value: sourceLabel },
          { label: 'Stream state', value: chart.streamState, tone: streamTone },
          { label: 'Range', value: CHART_RANGE_LABELS[chart.chartRange] },
        ],
        cards: [
          {
            label: 'Lookback semantics',
            title: `${CHART_RANGE_LABELS[chart.chartRange]} from now`,
            description: 'Range buttons request normalized lookback windows, not fixed chart intervals.',
          },
          {
            label: 'Fallback path',
            title: 'SignalR to HTTP polling',
            description: 'If streaming snapshots are closed or unavailable, the workflow continues refreshing the same provider-backed HTTP candles.',
            tone: chart.streamState === 'connected' ? 'positive' : 'warning',
          },
        ],
        children: (
          <div id="chart-provider" className="terminal-context-panel__section">
            <BrokerPaperStatus />
          </div>
        ),
      }}
    >
      <section id="chart-search" className="terminal-panel-anchor" aria-label="Search another IBKR stock">
        <SymbolSearch
          title="Search another IBKR stock"
          description="Jump from this symbol page to any IBKR/iBeam stock result without relying on a local symbol catalog."
          compact
        />
      </section>

      <section id="chart-candles" className="workspace-panel terminal-data-panel chart-view" data-testid="chart-workspace">
        <div className="panel-heading chart-heading terminal-panel-heading">
          <div>
            <p className="eyebrow">Lookback candlestick chart</p>
            <h2>{chart.normalizedSymbol} candles and indicators</h2>
            <p>Current source: {sourceLabel}. Chart controls request the selected lookback range from now.</p>
          </div>
          <div className="chart-actions">
            <span className={chart.streamState === 'connected' ? 'stream-pill stream-pill--connected' : 'stream-pill'} data-testid="stream-state">
              SignalR {chart.streamState}
            </span>
            <span className="pill">{CHART_RANGE_LABELS[chart.chartRange]} lookback</span>
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

        <IndicatorPanel indicators={chart.indicators} />

        <div className="chart-footer-note">
          <p>
            HTTP candles/indicators are refreshed for the selected lookback range from now. SignalR applies IBKR snapshot updates when `/hubs/market-data` is reachable;
            if streaming is unavailable this view falls back to HTTP polling without synthetic fallback data.
          </p>
          {chart.candles ? <p>Current candle source: {sourceLabel}.</p> : null}
          {chart.streamState === 'unavailable' ? (
            <p>Streaming snapshots are unavailable; polling continues against the IBKR/iBeam HTTP provider.</p>
          ) : null}
          {chart.latestUpdate ? (
            <p>
              Last market-data stream update: {chart.latestUpdate.symbol} {chart.latestUpdate.timeframe} range close {chart.latestUpdate.close.toFixed(2)} from {formatMarketDataSourceLabel(chart.latestUpdate.source)}.
            </p>
          ) : null}
        </div>
      </section>

      <section id="chart-analysis" className="terminal-panel-anchor" aria-label="Provider-neutral analysis entry point">
        <AnalysisPanel symbol={chart.normalizedSymbol} chartRange={chart.chartRange} candleSource={chart.candles?.source} />
      </section>
    </TerminalWorkspaceShell>
  );
}

function formatChartIdentity(chart: ReturnType<typeof useSymbolChartWorkflow>): string {
  if (!chart.chartIdentity) {
    return `${chart.normalizedSymbol} uses the default manual symbol identity until provider metadata is supplied by search, trending, or cache payloads.`;
  }

  const provider = chart.chartIdentity.provider.toUpperCase();
  const providerId = chart.chartIdentity.providerSymbolId ? ` · provider id ${chart.chartIdentity.providerSymbolId}` : '';
  const exchange = chart.chartIdentity.exchange ? ` · market ${chart.chartIdentity.exchange}` : '';

  return `${chart.chartIdentity.symbol} exact instrument identity: provider ${provider}${providerId}${exchange} · ${chart.chartIdentity.currency} · ${chart.chartIdentity.assetClass}.`;
}
