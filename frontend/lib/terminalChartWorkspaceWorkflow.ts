'use client';

import { useMemo } from 'react';

import {
  ChartPollingFallbackMs,
  formatMarketDataSourceLabel,
  useSymbolChartWorkflow,
  type SymbolChartWorkflow,
  type SymbolChartWorkflowOptions,
} from './symbolChartWorkflow';
import { getMarketDataIdentity, type NormalizedInstrumentIdentity } from './instrumentIdentity';
import {
  CHART_RANGE_DESCRIPTIONS,
  CHART_RANGE_LABELS,
  SUPPORTED_CHART_RANGES,
  type ChartRange,
  type MarketDataSymbolIdentity,
} from '../types/marketData';

export const TERMINAL_CHART_RANGE_HELP_COPY = 'Lookback from now: 1D = past day, 1m = past month, 6m = past six months.';
export const TERMINAL_CHART_HTTP_FALLBACK_COPY = 'SignalR applies market-data updates when /hubs/market-data is reachable; if streaming is unavailable the view falls back to HTTP polling without synthetic data.';
export const TERMINAL_CHART_NO_ORDER_COPY = 'Chart and analysis workspaces are read-only: no order-entry, simulated-submit, or broker-routing controls are available.';

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
      indicatorsSource: chart.indicators?.source,
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
  indicatorsSource,
  latestUpdateSource,
  streamState,
  identity,
  hasCandleData,
  hasIndicatorData,
}: {
  symbol: string;
  chartRange: ChartRange;
  candlesSource?: string | null;
  indicatorsSource?: string | null;
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
    candleSourceLabel: formatMarketDataSourceLabel(candlesSource),
    indicatorSourceLabel: formatMarketDataSourceLabel(indicatorsSource ?? candlesSource),
    latestUpdateSourceLabel: latestUpdateSource ? formatMarketDataSourceLabel(latestUpdateSource) : null,
    streamLabel: `SignalR ${streamState}`,
    streamTone: getTerminalChartStreamTone(streamState),
    fallbackCopy: TERMINAL_CHART_HTTP_FALLBACK_COPY,
    noOrderCopy: TERMINAL_CHART_NO_ORDER_COPY,
    identity,
    identitySummary: formatTerminalChartIdentitySummary(symbol, identity),
    identityRows: createTerminalChartIdentityRows(symbol, identity),
    hasCandleData,
    hasIndicatorData,
    isEmpty: !hasCandleData,
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
    return `${symbol} uses the default manual symbol identity until provider metadata is supplied by search, trending, watchlist, or market-data payloads.`;
  }

  const provider = identity.provider.toUpperCase();
  const providerId = identity.providerSymbolId ? ` · provider id ${identity.providerSymbolId}` : '';
  const exchange = identity.exchange ? ` · market ${identity.exchange}` : '';

  return `${identity.symbol} exact instrument identity: provider ${provider}${providerId}${exchange} · ${identity.currency} · ${identity.assetClass}.`;
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
      { label: 'Identity handoff', value: 'Awaiting exact provider-market metadata from search, trending, watchlist, or market-data payloads.' },
    ];
  }

  return [
    { label: 'Symbol', value: identity.symbol, code: true },
    { label: 'Provider', value: identity.provider.toUpperCase(), code: true },
    { label: 'Provider ID', value: identity.providerSymbolId ?? 'Unavailable', code: true },
    { label: 'IBKR conid', value: identity.ibkrConid === null ? 'Unavailable' : String(identity.ibkrConid), code: true },
    { label: 'Exchange', value: identity.exchange ?? 'Unavailable', code: true },
    { label: 'Currency', value: identity.currency, code: true },
    { label: 'Asset class', value: identity.assetClass, code: true },
  ];
}

export { ChartPollingFallbackMs };
