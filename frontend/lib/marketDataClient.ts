import { buildApiUrl } from './apiBaseUrl';
import type { CandleSeriesResponse, IndicatorResponse, Timeframe, TrendingSymbolsResponse } from '../types/marketData';

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

type ApiErrorPayload = {
  code?: string;
  message?: string;
  error?: string;
};

export async function getTrendingSymbols(): Promise<TrendingSymbolsResponse> {
  return fetchJson<TrendingSymbolsResponse>('/api/market-data/trending');
}

export async function getCandles(symbol: string, timeframe: Timeframe): Promise<CandleSeriesResponse> {
  const encodedSymbol = encodeURIComponent(symbol.toUpperCase());
  const encodedTimeframe = encodeURIComponent(timeframe);
  return fetchJson<CandleSeriesResponse>(`/api/market-data/${encodedSymbol}/candles?timeframe=${encodedTimeframe}`);
}

export async function getIndicators(symbol: string, timeframe: Timeframe): Promise<IndicatorResponse> {
  const encodedSymbol = encodeURIComponent(symbol.toUpperCase());
  const encodedTimeframe = encodeURIComponent(timeframe);
  return fetchJson<IndicatorResponse>(`/api/market-data/${encodedSymbol}/indicators?timeframe=${encodedTimeframe}`);
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const body = await response.text();
    const parsedError = parseApiErrorBody(body);
    throw new ApiClientError(formatMarketDataError(response.status, parsedError), response.status, body, parsedError?.code);
  }

  return response.json() as Promise<T>;
}

function parseApiErrorBody(body: string): ApiErrorPayload | null {
  try {
    const parsed = JSON.parse(body) as ApiErrorPayload;
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function formatMarketDataError(status: number, error: ApiErrorPayload | null): string {
  const detail = error?.message ?? error?.error;
  if (error?.code === 'provider-not-configured') {
    return detail ? `IBKR market data is not configured. ${detail}` : 'IBKR market data is not configured.';
  }

  if (error?.code === 'provider-unavailable') {
    return detail
      ? `IBKR market data is unavailable or authentication is required. ${detail}`
      : 'IBKR market data is unavailable or authentication is required.';
  }

  if (detail) {
    return detail;
  }

  return `ATrade API request failed with HTTP ${status}.`;
}
