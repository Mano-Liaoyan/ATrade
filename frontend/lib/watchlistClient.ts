import { buildApiUrl } from './apiBaseUrl';
import {
  createProvisionalInstrumentKey,
  normalizeInstrumentAssetClass,
  type InstrumentIdentityInput,
} from './instrumentIdentity';

export type WatchlistSymbol = {
  symbol: string;
  instrumentKey: string;
  pinKey: string;
  provider: string;
  providerSymbolId: string | null;
  ibkrConid: number | null;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  assetClass: string | null;
  sortOrder: number;
  createdAtUtc: string;
  updatedAtUtc: string;
};

export type WatchlistInstrumentIdentity = InstrumentIdentityInput;

export type WatchlistSymbolInput = WatchlistInstrumentIdentity & {
  name?: string | null;
};

export type WatchlistResponse = {
  userId: string;
  workspaceId: string;
  symbols: WatchlistSymbol[];
};

export class WatchlistApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = 'WatchlistApiClientError';
  }
}

export async function getWatchlist(): Promise<WatchlistResponse> {
  return fetchWatchlist('/api/workspace/watchlist');
}

export async function replaceWatchlist(symbols: WatchlistSymbolInput[]): Promise<WatchlistResponse> {
  return fetchWatchlist('/api/workspace/watchlist', {
    method: 'PUT',
    body: JSON.stringify({ symbols }),
  });
}

export async function pinWatchlistSymbol(symbol: WatchlistSymbolInput): Promise<WatchlistResponse> {
  return fetchWatchlist('/api/workspace/watchlist', {
    method: 'POST',
    body: JSON.stringify(symbol),
  });
}

export async function unpinWatchlistInstrument(instrumentKey: string): Promise<WatchlistResponse> {
  const encodedInstrumentKey = encodeURIComponent(instrumentKey.trim());
  return fetchWatchlist(`/api/workspace/watchlist/pins/${encodedInstrumentKey}`, { method: 'DELETE' });
}

export async function unpinWatchlistSymbol(symbol: string): Promise<WatchlistResponse> {
  const encodedSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  return fetchWatchlist(`/api/workspace/watchlist/${encodedSymbol}`, { method: 'DELETE' });
}

export function getWatchlistPinKey(symbol: WatchlistSymbol): string {
  return symbol.pinKey || symbol.instrumentKey || createWatchlistInstrumentKey(symbol);
}

export const createWatchlistInstrumentKey = createProvisionalInstrumentKey;

export const normalizeWatchlistAssetClass = normalizeInstrumentAssetClass;

async function fetchWatchlist(path: string, init: RequestInit = {}): Promise<WatchlistResponse> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
      ...(init.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    const parsedError = parseErrorBody(body);
    throw new WatchlistApiClientError(
      parsedError?.error ?? `ATrade watchlist request failed with HTTP ${response.status}.`,
      response.status,
      body,
      parsedError?.code,
    );
  }

  return response.json() as Promise<WatchlistResponse>;
}

function parseErrorBody(body: string): { code?: string; error?: string } | null {
  try {
    const parsed: unknown = JSON.parse(body);
    if (typeof parsed !== 'object' || parsed === null) {
      return null;
    }

    const candidate = parsed as { code?: unknown; error?: unknown };
    return {
      code: typeof candidate.code === 'string' ? candidate.code : undefined,
      error: typeof candidate.error === 'string' ? candidate.error : undefined,
    };
  } catch {
    return null;
  }
}
