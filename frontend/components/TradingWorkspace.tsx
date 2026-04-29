'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from '../lib/marketDataClient';
import {
  getWatchlist,
  pinWatchlistSymbol,
  unpinWatchlistSymbol,
  type WatchlistResponse,
  type WatchlistSymbol,
  type WatchlistSymbolInput,
} from '../lib/watchlistClient';
import {
  hasCompletedWatchlistMigration,
  markWatchlistMigrationCompleted,
  readCachedWatchlist,
  writeCachedWatchlist,
} from '../lib/watchlistStorage';
import type { TrendingSymbol } from '../types/marketData';
import { TrendingList } from './TrendingList';
import { Watchlist } from './Watchlist';

type WatchlistSource = 'backend' | 'cache';

export function TradingWorkspace() {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [watchlistSymbols, setWatchlistSymbols] = useState<WatchlistSymbol[]>([]);
  const [marketDataLoading, setMarketDataLoading] = useState(true);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistSource, setWatchlistSource] = useState<WatchlistSource>('backend');
  const [savingSymbol, setSavingSymbol] = useState<string | null>(null);

  const applyWatchlistResponse = useCallback((response: WatchlistResponse) => {
    setWatchlistSymbols(response.symbols);
    setWatchlistSource('backend');
    writeCachedWatchlist(response.symbols.map((symbol) => symbol.symbol));
  }, []);

  const loadTrendingSymbols = useCallback(async () => {
    setMarketDataLoading(true);
    setMarketDataError(null);

    try {
      const response = await getTrendingSymbols();
      setTrendingSymbols(response.symbols);
    } catch (caughtError) {
      setMarketDataError(caughtError instanceof Error ? caughtError.message : 'The market-data backend is unavailable.');
      setTrendingSymbols([]);
    } finally {
      setMarketDataLoading(false);
    }
  }, []);

  const loadWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    setWatchlistError(null);

    try {
      const response = await getWatchlist();
      const migratedResponse = await migrateCachedWatchlistAfterBackendLoad(response);
      applyWatchlistResponse(migratedResponse);
    } catch (caughtError) {
      const cachedSymbols = readCachedWatchlist();
      setWatchlistSymbols(cachedSymbols.map(createCachedWatchlistSymbol));
      setWatchlistSource('cache');
      setWatchlistError(formatWatchlistError(caughtError, cachedSymbols.length > 0));
    } finally {
      setWatchlistLoading(false);
    }
  }, [applyWatchlistResponse]);

  useEffect(() => {
    void loadTrendingSymbols();
    void loadWatchlist();
  }, [loadTrendingSymbols, loadWatchlist]);

  const sortedTrendingSymbols = useMemo(
    () => [...trendingSymbols].sort((left, right) => right.score - left.score),
    [trendingSymbols],
  );

  const pinnedSymbolNames = useMemo(() => watchlistSymbols.map((symbol) => symbol.symbol.toUpperCase()), [watchlistSymbols]);

  const handleTogglePin = useCallback(
    async (symbol: TrendingSymbol) => {
      if (watchlistLoading || watchlistError || savingSymbol) {
        return;
      }

      const normalizedSymbol = symbol.symbol.toUpperCase();
      setSavingSymbol(normalizedSymbol);

      try {
        const response = pinnedSymbolNames.includes(normalizedSymbol)
          ? await unpinWatchlistSymbol(normalizedSymbol)
          : await pinWatchlistSymbol(createWatchlistInput(symbol));
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistError(caughtError, false));
      } finally {
        setSavingSymbol(null);
      }
    },
    [applyWatchlistResponse, pinnedSymbolNames, savingSymbol, watchlistError, watchlistLoading],
  );

  const handleRemovePin = useCallback(
    async (symbol: string) => {
      if (watchlistLoading || watchlistError || savingSymbol) {
        return;
      }

      const normalizedSymbol = symbol.trim().toUpperCase();
      setSavingSymbol(normalizedSymbol);

      try {
        const response = await unpinWatchlistSymbol(normalizedSymbol);
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistError(caughtError, false));
      } finally {
        setSavingSymbol(null);
      }
    },
    [applyWatchlistResponse, savingSymbol, watchlistError, watchlistLoading],
  );

  const watchlistActionsDisabled = watchlistLoading || Boolean(watchlistError) || savingSymbol !== null;

  return (
    <section className="workspace-stack" data-testid="trading-workspace">
      <div className="workspace-status-row" aria-live="polite">
        <span className="status-dot" aria-hidden="true" />
        <span>Paper-only workspace consuming backend market data and Postgres-backed workspace watchlists.</span>
      </div>

      {marketDataLoading ? (
        <div className="workspace-panel loading-state" role="status">
          Loading backend-driven trending stocks and ETFs…
        </div>
      ) : null}

      {!marketDataLoading ? (
        <div className="workspace-layout">
          {marketDataError ? (
            <div className="workspace-panel error-state" role="alert">
              <strong>Market data backend unavailable.</strong>
              <p>{marketDataError}</p>
              <button className="primary-button" type="button" onClick={() => void loadTrendingSymbols()}>
                Retry backend request
              </button>
            </div>
          ) : null}

          {!marketDataError && sortedTrendingSymbols.length === 0 ? (
            <div className="workspace-panel empty-state">
              <strong>No trending symbols returned.</strong>
              <p>The backend responded, but no stocks or ETFs were available for the workspace.</p>
            </div>
          ) : null}

          {!marketDataError && sortedTrendingSymbols.length > 0 ? (
            <TrendingList
              symbols={sortedTrendingSymbols}
              pinnedSymbols={pinnedSymbolNames}
              onTogglePin={handleTogglePin}
              actionsDisabled={watchlistActionsDisabled}
              savingSymbol={savingSymbol}
            />
          ) : null}

          <Watchlist
            symbols={watchlistSymbols}
            trendingSymbols={sortedTrendingSymbols}
            loading={watchlistLoading}
            error={watchlistError}
            source={watchlistSource}
            actionsDisabled={watchlistActionsDisabled}
            savingSymbol={savingSymbol}
            onRetry={() => void loadWatchlist()}
            onRemove={handleRemovePin}
          />
        </div>
      ) : null}
    </section>
  );
}

async function migrateCachedWatchlistAfterBackendLoad(response: WatchlistResponse): Promise<WatchlistResponse> {
  if (hasCompletedWatchlistMigration()) {
    return response;
  }

  const cachedSymbols = readCachedWatchlist();
  let nextResponse = response;

  if (cachedSymbols.length > 0) {
    const backendSymbols = new Set(response.symbols.map((symbol) => symbol.symbol.toUpperCase()));
    for (const cachedSymbol of cachedSymbols) {
      if (!backendSymbols.has(cachedSymbol)) {
        nextResponse = await pinWatchlistSymbol(createManualWatchlistInput(cachedSymbol));
        backendSymbols.add(cachedSymbol);
      }
    }
  }

  markWatchlistMigrationCompleted();
  return nextResponse;
}

function createWatchlistInput(symbol: TrendingSymbol): WatchlistSymbolInput {
  return {
    symbol: symbol.symbol,
    provider: 'manual',
    name: symbol.name,
    exchange: symbol.exchange,
    currency: 'USD',
    assetClass: symbol.assetClass === 'Stock' ? 'STK' : symbol.assetClass,
  };
}

function createManualWatchlistInput(symbol: string): WatchlistSymbolInput {
  return {
    symbol,
    provider: 'manual',
    currency: 'USD',
    assetClass: 'STK',
  };
}

function createCachedWatchlistSymbol(symbol: string, sortOrder: number): WatchlistSymbol {
  return {
    symbol,
    provider: 'cache',
    providerSymbolId: null,
    ibkrConid: null,
    name: null,
    exchange: null,
    currency: 'USD',
    assetClass: 'STK',
    sortOrder,
    createdAtUtc: '',
    updatedAtUtc: '',
  };
}

function formatWatchlistError(caughtError: unknown, cachedSymbolsVisible: boolean): string {
  const message = caughtError instanceof Error ? caughtError.message : 'The watchlist backend is unavailable.';
  return cachedSymbolsVisible ? `${message} Cached pins are shown read-only until the backend returns.` : message;
}
