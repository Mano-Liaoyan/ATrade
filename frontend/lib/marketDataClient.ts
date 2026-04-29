import { buildApiUrl } from './apiBaseUrl';
import type { CandleSeriesResponse, IndicatorResponse, Timeframe, TrendingSymbolsResponse } from '../types/marketData';

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: string,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

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
    throw new ApiClientError(`ATrade API request failed with HTTP ${response.status}.`, response.status, body);
  }

  return response.json() as Promise<T>;
}
