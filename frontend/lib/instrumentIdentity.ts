import type { MarketDataSymbolIdentity, MarketDataSymbolSearchResult, TrendingSymbol } from '../types/marketData';

export const DEFAULT_PROVIDER = 'manual';
export const DEFAULT_IBKR_PROVIDER = 'ibkr';
export const DEFAULT_CURRENCY = 'USD';
export const DEFAULT_ASSET_CLASS = 'STK';

export type InstrumentIdentityInput = {
  symbol: string;
  provider?: string | null;
  providerSymbolId?: string | null;
  ibkrConid?: number | null;
  exchange?: string | null;
  currency?: string | null;
  assetClass?: string | null;
};

export type NormalizedInstrumentIdentity = {
  symbol: string;
  provider: string;
  providerSymbolId: string | null;
  ibkrConid: number | null;
  exchange: string | null;
  currency: string;
  assetClass: string;
};

export function normalizeInstrumentIdentity(identity: InstrumentIdentityInput): NormalizedInstrumentIdentity {
  const ibkrConid = normalizeNullableNumber(identity.ibkrConid);
  const provider = normalizeProvider(identity.provider, ibkrConid);
  const providerSymbolId = normalizeOptional(identity.providerSymbolId) ?? (ibkrConid === null ? null : String(ibkrConid));

  return {
    symbol: identity.symbol.trim().toUpperCase(),
    provider,
    providerSymbolId,
    ibkrConid,
    exchange: normalizeOptional(identity.exchange)?.toUpperCase() ?? null,
    currency: normalizeOptional(identity.currency)?.toUpperCase() ?? DEFAULT_CURRENCY,
    assetClass: normalizeInstrumentAssetClass(identity.assetClass),
  };
}

export function createProvisionalInstrumentKey(identity: InstrumentIdentityInput): string {
  const normalized = normalizeInstrumentIdentity(identity);

  return [
    `provider=${encodeSegment(normalized.provider)}`,
    `providerSymbolId=${encodeSegment(normalized.providerSymbolId)}`,
    `ibkrConid=${encodeSegment(normalized.ibkrConid === null ? null : String(normalized.ibkrConid))}`,
    `symbol=${encodeSegment(normalized.symbol)}`,
    `exchange=${encodeSegment(normalized.exchange)}`,
    `currency=${encodeSegment(normalized.currency)}`,
    `assetClass=${encodeSegment(normalized.assetClass)}`,
  ].join('|');
}

export function normalizeInstrumentAssetClass(assetClass: string | null | undefined): string {
  const normalized = normalizeOptional(assetClass)?.toUpperCase();
  if (!normalized) {
    return DEFAULT_ASSET_CLASS;
  }

  return normalized === 'STOCK' || normalized === 'STOCKS' ? DEFAULT_ASSET_CLASS : normalized;
}

export function parseIbkrConid(provider: string | null | undefined, providerSymbolId: string | null | undefined): number | null {
  if (normalizeOptional(provider)?.toLowerCase() !== DEFAULT_IBKR_PROVIDER || !providerSymbolId || !/^\d+$/.test(providerSymbolId)) {
    return null;
  }

  return Number(providerSymbolId);
}

export function getSearchResultIdentity(result: MarketDataSymbolSearchResult): NormalizedInstrumentIdentity {
  const provider = result.provider || result.identity.provider;
  const providerSymbolId = result.providerSymbolId ?? result.identity.providerSymbolId;

  return normalizeInstrumentIdentity({
    symbol: result.symbol || result.identity.symbol,
    provider,
    providerSymbolId,
    ibkrConid: parseIbkrConid(provider, providerSymbolId),
    exchange: result.exchange || result.identity.exchange,
    currency: result.currency || result.identity.currency,
    assetClass: result.assetClass || result.identity.assetClass,
  });
}

export function getTrendingSymbolIdentity(symbol: TrendingSymbol): NormalizedInstrumentIdentity {
  const identity = symbol.identity;
  const provider = identity?.provider ?? DEFAULT_IBKR_PROVIDER;
  const providerSymbolId = identity?.providerSymbolId ?? null;

  return normalizeInstrumentIdentity({
    symbol: identity?.symbol ?? symbol.symbol,
    provider,
    providerSymbolId,
    ibkrConid: parseIbkrConid(provider, providerSymbolId),
    exchange: identity?.exchange ?? symbol.exchange,
    currency: identity?.currency ?? DEFAULT_CURRENCY,
    assetClass: identity?.assetClass ?? symbol.assetClass,
  });
}

export function getMarketDataIdentity(identity: MarketDataSymbolIdentity | null | undefined, fallbackSymbol: string): NormalizedInstrumentIdentity | null {
  if (!identity) {
    return null;
  }

  return normalizeInstrumentIdentity({
    symbol: identity.symbol || fallbackSymbol,
    provider: identity.provider,
    providerSymbolId: identity.providerSymbolId,
    ibkrConid: parseIbkrConid(identity.provider, identity.providerSymbolId),
    exchange: identity.exchange,
    currency: identity.currency,
    assetClass: identity.assetClass,
  });
}

export function createSymbolChartHref(identity: InstrumentIdentityInput): string {
  const normalized = normalizeInstrumentIdentity(identity);
  const params = toExactIdentitySearchParams(normalized);
  const query = params.toString();
  return `/symbols/${encodeURIComponent(normalized.symbol)}${query ? `?${query}` : ''}`;
}

export function appendIdentityQueryParams(params: URLSearchParams, identity: InstrumentIdentityInput | null | undefined): URLSearchParams {
  if (!identity) {
    return params;
  }

  for (const [key, value] of toExactIdentitySearchParams(normalizeInstrumentIdentity(identity))) {
    params.set(key, value);
  }

  return params;
}

function toExactIdentitySearchParams(identity: NormalizedInstrumentIdentity): URLSearchParams {
  const params = new URLSearchParams();

  if (identity.provider && identity.provider !== DEFAULT_PROVIDER) {
    params.set('provider', identity.provider);
  }

  if (identity.providerSymbolId) {
    params.set('providerSymbolId', identity.providerSymbolId);
  }

  if (identity.exchange) {
    params.set('exchange', identity.exchange);
  }

  if (identity.currency) {
    params.set('currency', identity.currency);
  }

  if (identity.assetClass) {
    params.set('assetClass', identity.assetClass);
  }

  return params;
}

function normalizeProvider(provider: string | null | undefined, ibkrConid: number | null): string {
  const normalized = normalizeOptional(provider)?.toLowerCase();
  if (normalized) {
    return normalized;
  }

  return ibkrConid === null ? DEFAULT_PROVIDER : DEFAULT_IBKR_PROVIDER;
}

function normalizeOptional(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function normalizeNullableNumber(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function encodeSegment(value: string | number | null | undefined): string {
  return encodeURIComponent(value === null || value === undefined ? '' : String(value).trim());
}
