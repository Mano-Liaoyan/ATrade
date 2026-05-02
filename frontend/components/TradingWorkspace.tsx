'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from '../lib/marketDataClient';
import {
  createProvisionalInstrumentKey,
  getSearchResultIdentity,
  getTrendingSymbolIdentity,
  type InstrumentIdentityInput,
} from '../lib/instrumentIdentity';
import {
  getWatchlist,
  getWatchlistPinKey,
  pinWatchlistSymbol,
  unpinWatchlistInstrument,
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
import type { MarketDataSymbolSearchResult, TrendingSymbol } from '../types/marketData';
import { SymbolSearch } from './SymbolSearch';
import { TrendingList } from './TrendingList';
import { Watchlist } from './Watchlist';

type WatchlistSource = 'backend' | 'cache';

export function TradingWorkspace() {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [watchlistSymbols, setWatchlistSymbols] = useState<WatchlistSymbol[]>([]);
  const [marketDataLoading, setMarketDataLoading] = useState(true);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [marketDataSource, setMarketDataSource] = useState<string | null>(null);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistSource, setWatchlistSource] = useState<WatchlistSource>('backend');
  const [savingPinKey, setSavingPinKey] = useState<string | null>(null);

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
      setMarketDataSource(response.source);
    } catch (caughtError) {
      setMarketDataError(caughtError instanceof Error ? caughtError.message : 'IBKR market data is unavailable.');
      setMarketDataSource(null);
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

  const pinnedInstrumentKeys = useMemo(() => watchlistSymbols.map(getWatchlistPinKey), [watchlistSymbols]);
  const pinnedInstrumentKeySet = useMemo(() => new Set(pinnedInstrumentKeys), [pinnedInstrumentKeys]);

  const handleTogglePin = useCallback(
    async (symbol: TrendingSymbol) => {
      if (watchlistLoading || watchlistError || savingPinKey) {
        return;
      }

      const input = createWatchlistInput(symbol);
      const pinKey = createProvisionalInstrumentKey(input);
      setSavingPinKey(pinKey);

      try {
        const response = pinnedInstrumentKeySet.has(pinKey)
          ? await unpinWatchlistInstrument(pinKey)
          : await pinWatchlistSymbol(input);
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistError(caughtError, false));
      } finally {
        setSavingPinKey(null);
      }
    },
    [applyWatchlistResponse, pinnedInstrumentKeySet, savingPinKey, watchlistError, watchlistLoading],
  );

  const handleToggleSearchPin = useCallback(
    async (result: MarketDataSymbolSearchResult) => {
      if (watchlistLoading || watchlistError || savingPinKey) {
        return;
      }

      const input = createSearchResultWatchlistInput(result);
      const pinKey = createProvisionalInstrumentKey(input);
      setSavingPinKey(pinKey);

      try {
        const response = pinnedInstrumentKeySet.has(pinKey)
          ? await unpinWatchlistInstrument(pinKey)
          : await pinWatchlistSymbol(input);
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistError(caughtError, false));
      } finally {
        setSavingPinKey(null);
      }
    },
    [applyWatchlistResponse, pinnedInstrumentKeySet, savingPinKey, watchlistError, watchlistLoading],
  );

  const handleRemovePin = useCallback(
    async (symbol: WatchlistSymbol) => {
      if (watchlistLoading || watchlistError || savingPinKey) {
        return;
      }

      const pinKey = getWatchlistPinKey(symbol);
      setSavingPinKey(pinKey);

      try {
        const response = pinKey
          ? await unpinWatchlistInstrument(pinKey)
          : await unpinWatchlistSymbol(symbol.symbol);
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistError(caughtError, false));
      } finally {
        setSavingPinKey(null);
      }
    },
    [applyWatchlistResponse, savingPinKey, watchlistError, watchlistLoading],
  );

  const watchlistActionsDisabled = watchlistLoading || Boolean(watchlistError) || savingPinKey !== null;

  return (
    <section className="workspace-stack" data-testid="trading-workspace">
      <div className="workspace-status-row" aria-live="polite">
        <span className="status-dot" aria-hidden="true" />
        <span>Paper-only workspace consuming IBKR/iBeam market data and Postgres-backed workspace watchlists.</span>
      </div>

      <SymbolSearch
        pinnedInstrumentKeys={pinnedInstrumentKeys}
        actionsDisabled={watchlistActionsDisabled}
        savingPinKey={savingPinKey}
        onTogglePin={handleToggleSearchPin}
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
              pinnedInstrumentKeys={pinnedInstrumentKeys}
              source={marketDataSource}
              onTogglePin={handleTogglePin}
              actionsDisabled={watchlistActionsDisabled}
              savingPinKey={savingPinKey}
            />
          ) : null}

          <Watchlist
            symbols={watchlistSymbols}
            trendingSymbols={sortedTrendingSymbols}
            loading={watchlistLoading}
            error={watchlistError}
            source={watchlistSource}
            actionsDisabled={watchlistActionsDisabled}
            savingPinKey={savingPinKey}
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
    const backendInstrumentKeys = new Set(response.symbols.map(getWatchlistPinKey));
    for (const cachedSymbol of cachedSymbols) {
      const manualInput = createManualWatchlistInput(cachedSymbol);
      const manualPinKey = createProvisionalInstrumentKey(manualInput);
      if (!backendInstrumentKeys.has(manualPinKey)) {
        nextResponse = await pinWatchlistSymbol(manualInput);
        backendInstrumentKeys.add(manualPinKey);
      }
    }
  }

  markWatchlistMigrationCompleted();
  return nextResponse;
}

function createWatchlistInput(symbol: TrendingSymbol): WatchlistSymbolInput {
  return {
    ...getTrendingSymbolIdentity(symbol),
    name: symbol.name,
  };
}

function createSearchResultWatchlistInput(result: MarketDataSymbolSearchResult): WatchlistSymbolInput {
  return {
    ...getSearchResultIdentity(result),
    name: result.name,
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
  const identity: InstrumentIdentityInput = {
    symbol,
    provider: 'cache',
    currency: 'USD',
    assetClass: 'STK',
  };
  const instrumentKey = createProvisionalInstrumentKey(identity);

  return {
    symbol,
    instrumentKey,
    pinKey: instrumentKey,
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
  return cachedSymbolsVisible ? `${message} Cached legacy pins are shown read-only until the backend returns.` : message;
}
