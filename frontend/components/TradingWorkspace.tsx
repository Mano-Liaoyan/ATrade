'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from '../lib/marketDataClient';
import { useWatchlistWorkflow } from '../lib/watchlistWorkflow';
import type { TrendingSymbol } from '../types/marketData';
import { SymbolSearch } from './SymbolSearch';
import { TrendingList } from './TrendingList';
import { Watchlist } from './Watchlist';

export function TradingWorkspace() {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [marketDataLoading, setMarketDataLoading] = useState(true);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [marketDataSource, setMarketDataSource] = useState<string | null>(null);
  const watchlist = useWatchlistWorkflow();

  const loadTrendingSymbols = useCallback(async () => {
    setMarketDataLoading(true);
    setMarketDataError(null);

    try {
      const response = await getTrendingSymbols();
      setTrendingSymbols(response.symbols);
      setMarketDataSource(response.source);
    } catch (caughtError) {
      setMarketDataError(caughtError instanceof Error ? caughtError.message : 'IBKR market data is unavailable.');
      setMarketDataSource(null);
      setTrendingSymbols([]);
    } finally {
      setMarketDataLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTrendingSymbols();
  }, [loadTrendingSymbols]);

  const sortedTrendingSymbols = useMemo(
    () => [...trendingSymbols].sort((left, right) => right.score - left.score),
    [trendingSymbols],
  );

  return (
    <section className="workspace-stack" data-testid="trading-workspace">
      <div className="workspace-status-row" aria-live="polite">
        <span className="status-dot" aria-hidden="true" />
        <span>Paper-only workspace consuming IBKR/iBeam market data and Postgres-backed workspace watchlists.</span>
      </div>

      <SymbolSearch
        getPinState={watchlist.getSearchResultPinState}
        onTogglePin={(result) => void watchlist.toggleSearchPin(result)}
      />

      {marketDataLoading ? (
        <div className="workspace-panel loading-state" role="status">
          Loading IBKR/iBeam trending stocks and ETFs…
        </div>
      ) : null}

      {!marketDataLoading ? (
        <div className="workspace-layout">
          {marketDataError ? (
            <div className="workspace-panel error-state" role="alert">
              <strong>IBKR market data unavailable.</strong>
              <p>{marketDataError}</p>
              <button className="primary-button" type="button" onClick={() => void loadTrendingSymbols()}>
                Retry IBKR market data
              </button>
            </div>
          ) : null}

          {!marketDataError && sortedTrendingSymbols.length === 0 ? (
            <div className="workspace-panel empty-state">
              <strong>No trending symbols returned.</strong>
              <p>The IBKR/iBeam provider responded, but no stocks or ETFs were available for the workspace.</p>
            </div>
          ) : null}

          {!marketDataError && sortedTrendingSymbols.length > 0 ? (
            <TrendingList
              symbols={sortedTrendingSymbols}
              getPinState={watchlist.getTrendingPinState}
              source={marketDataSource}
              onTogglePin={(symbol) => void watchlist.toggleTrendingPin(symbol)}
            />
          ) : null}

          <Watchlist
            symbols={watchlist.symbols}
            trendingSymbols={sortedTrendingSymbols}
            loading={watchlist.loading}
            error={watchlist.error}
            source={watchlist.source}
            getPinState={watchlist.getWatchlistSymbolPinState}
            onRetry={watchlist.retry}
            onRemove={(symbol) => void watchlist.removePin(symbol)}
          />
        </div>
      ) : null}
    </section>
  );
}
