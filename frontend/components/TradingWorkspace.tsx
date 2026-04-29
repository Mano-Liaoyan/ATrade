'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from '../lib/marketDataClient';
import { readWatchlist, toggleWatchlistSymbol } from '../lib/watchlistStorage';
import type { TrendingSymbol } from '../types/marketData';
import { TrendingList } from './TrendingList';
import { Watchlist } from './Watchlist';

export function TradingWorkspace() {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTrendingSymbols = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getTrendingSymbols();
      setTrendingSymbols(response.symbols);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'The market-data backend is unavailable.');
      setTrendingSymbols([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setWatchlistSymbols(readWatchlist());
    void loadTrendingSymbols();
  }, [loadTrendingSymbols]);

  const sortedTrendingSymbols = useMemo(
    () => [...trendingSymbols].sort((left, right) => right.score - left.score),
    [trendingSymbols],
  );

  const handleTogglePin = useCallback((symbol: string) => {
    setWatchlistSymbols((currentSymbols) => toggleWatchlistSymbol(currentSymbols, symbol));
  }, []);

  return (
    <section className="workspace-stack" data-testid="trading-workspace">
      <div className="workspace-status-row" aria-live="polite">
        <span className="status-dot" aria-hidden="true" />
        <span>Paper-only workspace consuming mocked backend market data and safe IBKR status surfaces.</span>
      </div>

      {loading ? (
        <div className="workspace-panel loading-state" role="status">
          Loading backend-driven trending stocks and ETFs…
        </div>
      ) : null}

      {!loading && error ? (
        <div className="workspace-panel error-state" role="alert">
          <strong>Market data backend unavailable.</strong>
          <p>{error}</p>
          <button className="primary-button" type="button" onClick={() => void loadTrendingSymbols()}>
            Retry backend request
          </button>
        </div>
      ) : null}

      {!loading && !error && sortedTrendingSymbols.length === 0 ? (
        <div className="workspace-panel empty-state">
          <strong>No trending symbols returned.</strong>
          <p>The backend responded, but no stocks or ETFs were available for the workspace.</p>
        </div>
      ) : null}

      {!loading && !error && sortedTrendingSymbols.length > 0 ? (
        <div className="workspace-layout">
          <TrendingList symbols={sortedTrendingSymbols} pinnedSymbols={watchlistSymbols} onTogglePin={handleTogglePin} />
          <Watchlist symbols={watchlistSymbols} trendingSymbols={sortedTrendingSymbols} onRemove={handleTogglePin} />
        </div>
      ) : null}
    </section>
  );
}
