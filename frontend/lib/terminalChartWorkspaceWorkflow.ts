'use client';

import { useMemo } from 'react';

import {
  ChartPollingFallbackMs,
  formatMarketDataSourceLabel,
  formatStaleMarketDataSourceWarning,
  useSymbolChartWorkflow,
  type SymbolChartWorkflow,
  type SymbolChartWorkflowOptions,
} from './symbolChartWorkflow';
import { getMarketDataIdentity, type NormalizedInstrumentIdentity } from './instrumentIdentity';
import { createTerminalChartHoverDetails, type TerminalChartHoverDetailRow } from './terminalChartHoverDetails';
import {
  CHART_RANGE_DESCRIPTIONS,
  CHART_RANGE_LABELS,
  SUPPORTED_CHART_RANGES,
  type ChartRange,
  type MarketDataSourceStatus,
  type MarketDataSymbolIdentity,
} from '../types/marketData';

export const TERMINAL_CHART_RANGE_HELP_COPY = 'Lookback: 1D, 1m, 6m.';
export const TERMINAL_CHART_HTTP_FALLBACK_COPY = 'SignalR unavailable: HTTP fallback active.';
export const TERMINAL_CHART_NO_ORDER_COPY = 'Read-only chart and analysis. No order controls.';

export type TerminalChartStreamTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type TerminalChartIdentityRow = {
  label: string;
  value: string;
  code?: boolean;
};

export type TerminalChartWorkspaceViewModel = {
  symbol: string;
  chartRange: ChartRange;
  chartRangeLabel: string;
  chartRangeDescription: string;
  supportedRanges: readonly ChartRange[];
  rangeHelpCopy: string;
  candleSourceLabel: string;
  indicatorSourceLabel: string;
  latestUpdateSourceLabel: string | null;
  staleCandleSourceWarning: string | null;
  hoverDetailRows: TerminalChartHoverDetailRow[];
  hoverDetailsTitle: string;
  compactIdentityLabel: string;
  compactSourceLabel: string;
  compactStateLabel: string | null;
  streamLabel: string;
  streamTone: TerminalChartStreamTone;
  fallbackCopy: string;
  noOrderCopy: string;
  identity: NormalizedInstrumentIdentity | null;
  identitySummary: string;
  identityRows: TerminalChartIdentityRow[];
  hasCandleData: boolean;
  hasIndicatorData: boolean;
  isEmpty: boolean;
};

export type TerminalChartWorkspaceWorkflow = SymbolChartWorkflow & {
  view: TerminalChartWorkspaceViewModel;
};

export function useTerminalChartWorkspaceWorkflow(options: SymbolChartWorkflowOptions): TerminalChartWorkspaceWorkflow {
  const chart = useSymbolChartWorkflow(options);
  const responseIdentity = useMemo(
    () => getFirstMarketDataIdentity(
      chart.normalizedSymbol,
      chart.candles?.identity,
      chart.indicators?.identity,
      chart.latestUpdate?.identity,
    ),
    [chart.candles?.identity, chart.indicators?.identity, chart.latestUpdate?.identity, chart.normalizedSymbol],
  );
  const displayIdentity = chart.chartIdentity ?? responseIdentity;
  const view = useMemo(
    () => createTerminalChartWorkspaceViewModel({
      symbol: chart.normalizedSymbol,
      chartRange: chart.chartRange,
      candlesSource: chart.candles?.source,
      candlesSourceStatus: chart.candles?.sourceStatus,
      indicatorsSource: chart.indicators?.source,
      indicatorsSourceStatus: chart.indicators?.sourceStatus,
      latestUpdateSource: chart.latestUpdate?.source,
      streamState: chart.streamState,
      identity: displayIdentity,
      hasCandleData: Boolean(chart.candles && chart.candles.candles.length > 0),
      hasIndicatorData: Boolean(chart.indicators && (
        chart.indicators.movingAverages.length > 0
        || chart.indicators.rsi.length > 0
        || chart.indicators.macd.length > 0
      )),
    }),
    [
      chart.candles,
      chart.chartRange,
      chart.indicators,
      chart.latestUpdate?.source,
      chart.normalizedSymbol,
      chart.streamState,
      displayIdentity,
    ],
  );

  return {
    ...chart,
    view,
  };
}

export function createTerminalChartWorkspaceViewModel({
  symbol,
  chartRange,
  candlesSource,
  candlesSourceStatus,
  indicatorsSource,
  indicatorsSourceStatus,
  latestUpdateSource,
  streamState,
  identity,
  hasCandleData,
  hasIndicatorData,
}: {
  symbol: string;
  chartRange: ChartRange;
  candlesSource?: string | null;
  candlesSourceStatus?: MarketDataSourceStatus | null;
  indicatorsSource?: string | null;
  indicatorsSourceStatus?: MarketDataSourceStatus | null;
  latestUpdateSource?: string | null;
  streamState: SymbolChartWorkflow['streamState'];
  identity: NormalizedInstrumentIdentity | null;
  hasCandleData: boolean;
  hasIndicatorData: boolean;
}): TerminalChartWorkspaceViewModel {
  return {
    symbol,
    chartRange,
    chartRangeLabel: CHART_RANGE_LABELS[chartRange],
    chartRangeDescription: CHART_RANGE_DESCRIPTIONS[chartRange],
    supportedRanges: SUPPORTED_CHART_RANGES,
    rangeHelpCopy: TERMINAL_CHART_RANGE_HELP_COPY,
    candleSourceLabel: formatMarketDataSourceLabel(candlesSource, candlesSourceStatus),
    indicatorSourceLabel: formatMarketDataSourceLabel(indicatorsSource ?? candlesSource, indicatorsSourceStatus ?? candlesSourceStatus),
    latestUpdateSourceLabel: latestUpdateSource ? formatMarketDataSourceLabel(latestUpdateSource) : null,
    staleCandleSourceWarning: formatStaleMarketDataSourceWarning(candlesSourceStatus),
    streamLabel: `Stream ${streamState}`,
    streamTone: getTerminalChartStreamTone(streamState),
    fallbackCopy: TERMINAL_CHART_HTTP_FALLBACK_COPY,
    noOrderCopy: TERMINAL_CHART_NO_ORDER_COPY,
    identity,
    identitySummary: formatTerminalChartIdentitySummary(symbol, identity),
    identityRows: createTerminalChartIdentityRows(symbol, identity),
    hasCandleData,
    hasIndicatorData,
    isEmpty: !hasCandleData,
    ...createTerminalChartHoverDetails({
      candleSource: candlesSource,
      candleSourceLabel: formatMarketDataSourceLabel(candlesSource, candlesSourceStatus),
      candleSourceStatus: candlesSourceStatus ?? null,
      fallbackCopy: TERMINAL_CHART_HTTP_FALLBACK_COPY,
      identity,
      indicatorSource: indicatorsSource ?? candlesSource,
      indicatorSourceLabel: formatMarketDataSourceLabel(indicatorsSource ?? candlesSource, indicatorsSourceStatus ?? candlesSourceStatus),
      latestUpdateSource,
      latestUpdateSourceLabel: latestUpdateSource ? formatMarketDataSourceLabel(latestUpdateSource) : null,
      noOrderCopy: TERMINAL_CHART_NO_ORDER_COPY,
      rangeDescription: CHART_RANGE_DESCRIPTIONS[chartRange],
      rangeLabel: CHART_RANGE_LABELS[chartRange],
      streamLabel: `Stream ${streamState}`,
      streamState,
      symbol,
    }),
  };
}

export function getTerminalChartStreamTone(streamState: SymbolChartWorkflow['streamState']): TerminalChartStreamTone {
  switch (streamState) {
    case 'connected':
      return 'success';
    case 'connecting':
    case 'reconnecting':
      return 'info';
    case 'closed':
    case 'unavailable':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function formatTerminalChartIdentitySummary(symbol: string, identity: NormalizedInstrumentIdentity | null): string {
  if (!identity) {
    return `${symbol} identity pending.`;
  }

  const provider = identity.provider.toUpperCase();
  const providerId = identity.providerSymbolId ? ` · provider id ${identity.providerSymbolId}` : '';
  const exchange = identity.exchange ? ` · market ${identity.exchange}` : '';

  return `${identity.symbol} Exact Instrument Identity: ${provider}${providerId}${exchange} · ${identity.currency} · ${identity.assetClass}.`;
}

function getFirstMarketDataIdentity(
  fallbackSymbol: string,
  ...identities: Array<MarketDataSymbolIdentity | null | undefined>
): NormalizedInstrumentIdentity | null {
  for (const identity of identities) {
    const normalized = getMarketDataIdentity(identity, fallbackSymbol);
    if (normalized) {
      return normalized;
    }
  }

  return null;
}

function createTerminalChartIdentityRows(symbol: string, identity: NormalizedInstrumentIdentity | null): TerminalChartIdentityRow[] {
  if (!identity) {
    return [
      { label: 'Symbol', value: symbol, code: true },
      { label: 'Provider', value: 'Manual / unavailable' },
      { label: 'Identity handoff', value: 'Provider-market metadata pending.' },
    ];
  }

  return [
    { label: 'Symbol', value: identity.symbol, code: true },
    { label: 'Provider', value: identity.provider.toUpperCase(), code: true },
    { label: 'Provider symbol id', value: formatProviderSymbolIdRowValue(identity), code: true },
    { label: 'Exchange', value: identity.exchange ?? 'Unavailable', code: true },
    { label: 'Currency', value: identity.currency, code: true },
    { label: 'Asset class', value: identity.assetClass, code: true },
  ];
}

function formatProviderSymbolIdRowValue(identity: NormalizedInstrumentIdentity): string {
  if (!identity.providerSymbolId) {
    return 'Unavailable';
  }

  if (identity.provider === 'ibkr' && identity.ibkrConid !== null && String(identity.ibkrConid) === identity.providerSymbolId) {
    return `${identity.providerSymbolId} (IBKR conid alias)`;
  }

  return identity.providerSymbolId;
}

export { ChartPollingFallbackMs };
