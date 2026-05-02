'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createProvisionalInstrumentKey,
  getSearchResultIdentity,
  getTrendingSymbolIdentity,
  type InstrumentIdentityInput,
} from './instrumentIdentity';
import {
  getWatchlist,
  getWatchlistPinKey,
  pinWatchlistSymbol,
  unpinWatchlistInstrument,
  unpinWatchlistSymbol,
  type WatchlistResponse,
  type WatchlistSymbol,
  type WatchlistSymbolInput,
} from './watchlistClient';
import {
  hasCompletedWatchlistMigration,
  markWatchlistMigrationCompleted,
  readCachedWatchlist,
  writeCachedWatchlist,
} from './watchlistStorage';
import type { MarketDataSymbolSearchResult, TrendingSymbol } from '../types/marketData';

export type WatchlistWorkflowSource = 'backend' | 'cache';

export type WatchlistWorkflowSymbol = WatchlistSymbol;

export type WatchlistPinState = {
  pinKey: string;
  pinned: boolean;
  saving: boolean;
  disabled: boolean;
};

export type WatchlistWorkflowState = {
  symbols: WatchlistWorkflowSymbol[];
  source: WatchlistWorkflowSource;
  loading: boolean;
  error: string | null;
  savingPinKey: string | null;
  pinnedInstrumentKeys: string[];
  actionsDisabled: boolean;
};

export type WatchlistWorkflowCommands = {
  retry: () => void;
  getTrendingPinState: (symbol: TrendingSymbol) => WatchlistPinState;
  getSearchResultPinState: (result: MarketDataSymbolSearchResult) => WatchlistPinState;
  getWatchlistSymbolPinState: (symbol: WatchlistWorkflowSymbol) => WatchlistPinState;
  toggleTrendingPin: (symbol: TrendingSymbol) => Promise<void>;
  toggleSearchPin: (result: MarketDataSymbolSearchResult) => Promise<void>;
  removePin: (symbol: WatchlistWorkflowSymbol) => Promise<void>;
};

export type WatchlistWorkflow = WatchlistWorkflowState & WatchlistWorkflowCommands;

export function useWatchlistWorkflow(): WatchlistWorkflow {
  const [watchlistSymbols, setWatchlistSymbols] = useState<WatchlistSymbol[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistSource, setWatchlistSource] = useState<WatchlistWorkflowSource>('backend');
  const [savingPinKey, setSavingPinKey] = useState<string | null>(null);

  const applyWatchlistResponse = useCallback((response: WatchlistResponse) => {
    setWatchlistSymbols(response.symbols);
    setWatchlistSource('backend');
    writeCachedWatchlist(response.symbols.map((symbol) => symbol.symbol));
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
      setWatchlistError(formatWatchlistWorkflowError(caughtError, cachedSymbols.length > 0));
    } finally {
      setWatchlistLoading(false);
    }
  }, [applyWatchlistResponse]);

  useEffect(() => {
    void loadWatchlist();
  }, [loadWatchlist]);

  const pinnedInstrumentKeys = useMemo(() => watchlistSymbols.map(getWatchlistPinKey), [watchlistSymbols]);
  // Backend persisted pinKey/instrumentKey values are authoritative. Provisional
  // identity keys are only lookup aliases for optimistic UI matching before the
  // backend returns the canonical watchlist response.
  const pinKeyByOptimisticKey = useMemo(() => {
    const keyLookup = new Map<string, string>();

    for (const symbol of watchlistSymbols) {
      const authoritativePinKey = getWatchlistPinKey(symbol);
      keyLookup.set(authoritativePinKey, authoritativePinKey);
      keyLookup.set(createProvisionalInstrumentKey(symbol), authoritativePinKey);
    }

    return keyLookup;
  }, [watchlistSymbols]);
  const actionsDisabled = watchlistLoading || Boolean(watchlistError) || savingPinKey !== null;

  const resolvePinState = useCallback(
    (optimisticPinKey: string): WatchlistPinState => {
      const authoritativePinKey = pinKeyByOptimisticKey.get(optimisticPinKey);
      const pinKey = authoritativePinKey ?? optimisticPinKey;
      const saving = savingPinKey === pinKey || savingPinKey === optimisticPinKey;

      return {
        pinKey,
        pinned: authoritativePinKey !== undefined,
        saving,
        disabled: actionsDisabled || saving,
      };
    },
    [actionsDisabled, pinKeyByOptimisticKey, savingPinKey],
  );

  const getTrendingPinState = useCallback(
    (symbol: TrendingSymbol) => resolvePinState(createProvisionalInstrumentKey(createWatchlistInput(symbol))),
    [resolvePinState],
  );

  const getSearchResultPinState = useCallback(
    (result: MarketDataSymbolSearchResult) => resolvePinState(createProvisionalInstrumentKey(createSearchResultWatchlistInput(result))),
    [resolvePinState],
  );

  const getWatchlistSymbolPinState = useCallback(
    (symbol: WatchlistWorkflowSymbol) => resolvePinState(getWatchlistPinKey(symbol)),
    [resolvePinState],
  );

  const togglePin = useCallback(
    async (input: WatchlistSymbolInput) => {
      if (actionsDisabled) {
        return;
      }

      const optimisticPinKey = createProvisionalInstrumentKey(input);
      const authoritativePinKey = pinKeyByOptimisticKey.get(optimisticPinKey);
      const pinKey = authoritativePinKey ?? optimisticPinKey;
      setSavingPinKey(pinKey);

      try {
        const response = authoritativePinKey
          ? await unpinWatchlistInstrument(authoritativePinKey)
          : await pinWatchlistSymbol(input);
        applyWatchlistResponse(response);
      } catch (caughtError) {
        setWatchlistError(formatWatchlistWorkflowError(caughtError, false));
      } finally {
        setSavingPinKey(null);
      }
    },
    [actionsDisabled, applyWatchlistResponse, pinKeyByOptimisticKey],
  );

  const toggleTrendingPin = useCallback(
    async (symbol: TrendingSymbol) => {
      await togglePin(createWatchlistInput(symbol));
    },
    [togglePin],
  );

  const toggleSearchPin = useCallback(
    async (result: MarketDataSymbolSearchResult) => {
      await togglePin(createSearchResultWatchlistInput(result));
    },
    [togglePin],
  );

  const removePin = useCallback(
    async (symbol: WatchlistWorkflowSymbol) => {
      if (actionsDisabled) {
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
        setWatchlistError(formatWatchlistWorkflowError(caughtError, false));
      } finally {
        setSavingPinKey(null);
      }
    },
    [actionsDisabled, applyWatchlistResponse],
  );

  return {
    symbols: watchlistSymbols,
    source: watchlistSource,
    loading: watchlistLoading,
    error: watchlistError,
    savingPinKey,
    pinnedInstrumentKeys,
    actionsDisabled,
    retry: () => void loadWatchlist(),
    getTrendingPinState,
    getSearchResultPinState,
    getWatchlistSymbolPinState,
    toggleTrendingPin,
    toggleSearchPin,
    removePin,
  };
}

async function migrateCachedWatchlistAfterBackendLoad(response: WatchlistResponse): Promise<WatchlistResponse> {
  if (hasCompletedWatchlistMigration()) {
    return response;
  }

  const cachedSymbols = readCachedWatchlist();
  let nextResponse = response;

  if (cachedSymbols.length > 0) {
    const backendInstrumentKeys = new Set(
      response.symbols.flatMap((symbol) => [getWatchlistPinKey(symbol), createProvisionalInstrumentKey(symbol)]),
    );
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

export function formatWatchlistWorkflowError(caughtError: unknown, cachedSymbolsVisible: boolean): string {
  const message = caughtError instanceof Error ? caughtError.message : 'The watchlist backend is unavailable.';
  return cachedSymbolsVisible ? `${message} Cached legacy pins are shown read-only until the backend returns.` : message;
}
