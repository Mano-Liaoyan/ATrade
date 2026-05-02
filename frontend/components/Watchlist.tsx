'use client';

import Link from 'next/link';
import { createSymbolChartHref } from '../lib/instrumentIdentity';
import type { WatchlistPinState, WatchlistWorkflowSymbol } from '../lib/watchlistWorkflow';
import type { TrendingSymbol } from '../types/marketData';
import { MarketLogo } from './MarketLogo';

type WatchlistProps = {
  symbols: WatchlistWorkflowSymbol[];
  trendingSymbols: TrendingSymbol[];
  loading: boolean;
  error: string | null;
  source: 'backend' | 'cache';
  getPinState: (symbol: WatchlistWorkflowSymbol) => WatchlistPinState;
  onRetry: () => void;
  onRemove: (symbol: WatchlistWorkflowSymbol) => void;
};

export function Watchlist({
  symbols,
  trendingSymbols,
  loading,
  error,
  source,
  getPinState,
  onRetry,
  onRemove,
}: WatchlistProps) {
  const bySymbol = new Map(trendingSymbols.map((symbol) => [symbol.symbol, symbol]));
  const sourceLabel = source === 'backend' ? 'Postgres' : 'Cached snapshot';

  return (
    <section className="workspace-panel watchlist-panel" aria-labelledby="watchlist-title" data-testid="watchlist-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Backend workspace preference</p>
          <h2 id="watchlist-title">Personal watchlist</h2>
        </div>
        <span className="pill">{sourceLabel}</span>
      </div>

      {loading ? (
        <div className="loading-state" role="status">
          Loading saved pins from the backend workspace…
        </div>
      ) : null}

      {!loading && error ? (
        <div className="error-state" role="alert">
          <strong>Watchlist backend unavailable.</strong>
          <p>{error}</p>
          <button className="primary-button" type="button" onClick={onRetry}>
            Retry watchlist request
          </button>
        </div>
      ) : null}

      {!loading && symbols.length === 0 && !error ? (
        <div className="empty-state">
          <strong>No pinned symbols yet.</strong>
          <p>Use IBKR stock search or pin a provider-backed trending result to persist it to your backend workspace watchlist.</p>
        </div>
      ) : null}

      {!loading && symbols.length > 0 ? (
        <ul className="watchlist" aria-label={source === 'backend' ? 'Saved watchlist pins' : 'Cached watchlist pins'}>
          {symbols.map((watchlistSymbol) => {
            const details = bySymbol.get(watchlistSymbol.symbol);
            const name = watchlistSymbol.name ?? details?.name ?? 'Pinned symbol';
            const exchange = watchlistSymbol.exchange ?? details?.exchange;
            const provider = watchlistSymbol.provider === 'ibkr' ? 'IBKR' : watchlistSymbol.provider;
            const currency = watchlistSymbol.currency ? ` · ${watchlistSymbol.currency}` : '';
            const assetClass = watchlistSymbol.assetClass ? ` · ${watchlistSymbol.assetClass}` : '';
            const providerId = formatProviderId(watchlistSymbol.provider, watchlistSymbol.providerSymbolId);
            const pinState = getPinState(watchlistSymbol);
            const marketLabel = exchange ? `Market ${exchange}` : 'Market unknown';
            const chartHref = createSymbolChartHref(watchlistSymbol);

            return (
              <li key={pinState.pinKey} aria-label={`${watchlistSymbol.symbol} ${marketLabel} ${provider}`}>
                <div>
                  <Link className="symbol-link" href={chartHref}>
                    {watchlistSymbol.symbol}
                  </Link>
                  <div className="instrument-identity-row">
                    <MarketLogo exchange={exchange} provider={watchlistSymbol.provider} compact />
                    <p>{exchange ? `${name} · Market ${exchange} · Provider ${provider}${currency}${assetClass}${providerId}` : `${name} · Provider ${provider}${currency}${assetClass}${providerId}`}</p>
                  </div>
                </div>
                <button
                  className="text-button"
                  type="button"
                  disabled={pinState.disabled}
                  onClick={() => onRemove(watchlistSymbol)}
                >
                  {pinState.saving ? 'Removing…' : 'Remove'}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}

function formatProviderId(provider: string, providerSymbolId: string | null): string {
  if (!providerSymbolId) {
    return '';
  }

  return provider.toLowerCase() === 'ibkr' ? ` · IBKR conid ${providerSymbolId}` : ` · ${provider.toUpperCase()} ID ${providerSymbolId}`;
}
