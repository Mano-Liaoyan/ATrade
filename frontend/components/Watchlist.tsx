'use client';

import Link from 'next/link';
import type { WatchlistSymbol } from '../lib/watchlistClient';
import type { TrendingSymbol } from '../types/marketData';

type WatchlistProps = {
  symbols: WatchlistSymbol[];
  trendingSymbols: TrendingSymbol[];
  loading: boolean;
  error: string | null;
  source: 'backend' | 'cache';
  actionsDisabled: boolean;
  savingSymbol?: string | null;
  onRetry: () => void;
  onRemove: (symbol: string) => void;
};

export function Watchlist({
  symbols,
  trendingSymbols,
  loading,
  error,
  source,
  actionsDisabled,
  savingSymbol = null,
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
          <p>Pin a trending stock or ETF to persist it to your backend workspace watchlist.</p>
        </div>
      ) : null}

      {!loading && symbols.length > 0 ? (
        <ul className="watchlist" aria-label={source === 'backend' ? 'Saved watchlist pins' : 'Cached watchlist pins'}>
          {symbols.map((watchlistSymbol) => {
            const details = bySymbol.get(watchlistSymbol.symbol);
            const name = watchlistSymbol.name ?? details?.name ?? 'Pinned symbol';
            const exchange = watchlistSymbol.exchange ?? details?.exchange;
            const isSaving = savingSymbol === watchlistSymbol.symbol.toUpperCase();

            return (
              <li key={watchlistSymbol.symbol}>
                <div>
                  <Link className="symbol-link" href={`/symbols/${encodeURIComponent(watchlistSymbol.symbol)}`}>
                    {watchlistSymbol.symbol}
                  </Link>
                  <p>{exchange ? `${name} · ${exchange}` : name}</p>
                </div>
                <button
                  className="text-button"
                  type="button"
                  disabled={actionsDisabled || isSaving}
                  onClick={() => onRemove(watchlistSymbol.symbol)}
                >
                  {isSaving ? 'Removing…' : 'Remove'}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
