import type { NormalizedInstrumentIdentity } from './instrumentIdentity';
import type { MarketDataSourceStatus } from '../types/marketData';

export type TerminalChartHoverDetailRow = {
  label: string;
  value: string;
};

export type TerminalChartHoverDetails = {
  compactIdentityLabel: string;
  compactSourceLabel: string;
  compactStateLabel: string | null;
  rows: TerminalChartHoverDetailRow[];
  title: string;
  hoverDetailRows: TerminalChartHoverDetailRow[];
  hoverDetailsTitle: string;
};

export type TerminalChartHoverDetailsInput = {
  candleSource?: string | null;
  candleSourceLabel: string;
  candleSourceStatus?: MarketDataSourceStatus | null;
  fallbackCopy: string;
  identity: NormalizedInstrumentIdentity | null;
  indicatorSource?: string | null;
  indicatorSourceLabel: string;
  latestUpdateSource?: string | null;
  latestUpdateSourceLabel?: string | null;
  noOrderCopy: string;
  rangeDescription: string;
  rangeLabel: string;
  streamLabel: string;
  streamState: string;
  symbol: string;
};

const TimescaleCachePrefix = 'timescale-cache:';
const UnsafeDetailPattern = /https?:\/\/|\b(token|cookie|password|secret|account|gateway|command|docker|runtime)\b|\/v\d+\/api|iserver\//i;

export function createTerminalChartHoverDetails({
  candleSource,
  candleSourceLabel,
  candleSourceStatus,
  fallbackCopy,
  identity,
  indicatorSource,
  indicatorSourceLabel,
  latestUpdateSource,
  latestUpdateSourceLabel,
  noOrderCopy,
  rangeDescription,
  rangeLabel,
  streamLabel,
  streamState,
  symbol,
}: TerminalChartHoverDetailsInput): TerminalChartHoverDetails {
  const compactIdentityLabel = formatCompactIdentityLabel(symbol, identity);
  const compactSourceLabel = sanitizeDetailValue(candleSourceLabel);
  const compactStateLabel = formatCompactStateLabel(candleSourceStatus, streamState);
  const rows = compactRows([
    { label: 'Exact Instrument Identity', value: compactIdentityLabel },
    { label: 'Provider', value: identity ? identity.provider.toUpperCase() : 'Manual / unavailable' },
    { label: 'Provider symbol id', value: formatProviderSymbolId(identity) },
    { label: 'Symbol', value: identity?.symbol ?? symbol.toUpperCase() },
    { label: 'Exchange', value: identity?.exchange ?? 'Unavailable' },
    { label: 'Currency', value: identity?.currency ?? 'Unavailable' },
    { label: 'Asset class', value: identity?.assetClass ?? 'Unavailable' },
    { label: 'Candle source', value: compactSourceLabel },
    { label: 'Original provider source', value: formatOriginalProviderSource(candleSourceStatus?.source ?? candleSource) },
    { label: 'Indicator source', value: indicatorSourceLabel },
    latestUpdateSource || latestUpdateSourceLabel ? { label: 'Latest update source', value: latestUpdateSourceLabel ?? latestUpdateSource ?? 'Unavailable' } : null,
    { label: 'Cache freshness', value: candleSourceStatus?.freshness ?? 'live/current provider' },
    candleSourceStatus?.generatedAtUtc ? { label: 'Cache generated', value: formatUtc(candleSourceStatus.generatedAtUtc) } : null,
    candleSourceStatus?.refreshAttemptedAtUtc ? { label: 'Cache refresh attempted', value: formatUtc(candleSourceStatus.refreshAttemptedAtUtc) } : null,
    candleSourceStatus?.refreshError ? { label: 'Cache refresh result', value: 'Provider refresh did not replace the displayed cache.' } : null,
    { label: 'Lookback range', value: `${rangeLabel} — ${rangeDescription}` },
    { label: 'Stream state', value: streamLabel },
    { label: 'Fallback state', value: fallbackCopy },
    { label: 'Read-only state', value: noOrderCopy },
  ]);

  const title = rows.map((row) => `${row.label}: ${row.value}`).join('\n');

  return {
    compactIdentityLabel,
    compactSourceLabel,
    compactStateLabel,
    rows,
    title,
    hoverDetailRows: rows,
    hoverDetailsTitle: title,
  };
}

function formatCompactIdentityLabel(symbol: string, identity: NormalizedInstrumentIdentity | null): string {
  if (!identity) {
    return `${symbol.toUpperCase()} · manual identity`;
  }

  const providerId = identity.providerSymbolId ? `:${identity.providerSymbolId}` : '';
  const exchange = identity.exchange ? ` · ${identity.exchange}` : '';
  return `${identity.symbol} · ${identity.provider.toUpperCase()}${providerId}${exchange} · ${identity.currency} · ${identity.assetClass}`;
}

function formatProviderSymbolId(identity: NormalizedInstrumentIdentity | null): string {
  if (!identity?.providerSymbolId) {
    return 'Unavailable';
  }

  if (identity.provider === 'ibkr' && identity.ibkrConid !== null && String(identity.ibkrConid) === identity.providerSymbolId) {
    return `${identity.providerSymbolId} (IBKR conid alias)`;
  }

  return identity.providerSymbolId;
}

function formatOriginalProviderSource(source: string | null | undefined): string {
  const safeSource = sanitizeDetailValue(source ?? 'Unavailable');
  if (safeSource.startsWith(TimescaleCachePrefix)) {
    return sanitizeDetailValue(safeSource.slice(TimescaleCachePrefix.length));
  }

  return safeSource;
}

function formatCompactStateLabel(sourceStatus: MarketDataSourceStatus | null | undefined, streamState: string): string | null {
  const states: string[] = [];
  if (sourceStatus?.freshness === 'stale') {
    states.push('Cache stale');
  }

  if (streamState === 'unavailable' || streamState === 'closed') {
    states.push(`stream ${streamState}`);
  }

  return states.length > 0 ? states.join(' · ') : null;
}

function compactRows(rows: Array<TerminalChartHoverDetailRow | null>): TerminalChartHoverDetailRow[] {
  return rows
    .filter((row): row is TerminalChartHoverDetailRow => row !== null)
    .map((row) => ({
      label: sanitizeDetailValue(row.label),
      value: sanitizeDetailValue(row.value),
    }));
}

function sanitizeDetailValue(value: string): string {
  return UnsafeDetailPattern.test(value) ? 'Redacted provider detail' : value;
}

function formatUtc(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? sanitizeDetailValue(value) : parsed.toISOString();
}
