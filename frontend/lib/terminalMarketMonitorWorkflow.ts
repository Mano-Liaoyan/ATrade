'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from './marketDataClient';
import {
  createProvisionalInstrumentKey,
  createSymbolChartHref,
  getSearchResultIdentity,
  getTrendingSymbolIdentity,
  normalizeInstrumentIdentity,
  parseIbkrConid,
  type InstrumentIdentityInput,
  type NormalizedInstrumentIdentity,
} from './instrumentIdentity';
import {
  DefaultSymbolSearchRequestLimit,
  MinimumSymbolSearchQueryLength,
  clampSymbolSearchLimit,
  type SymbolSearchWorkflow,
  useSymbolSearchWorkflow,
} from './symbolSearchWorkflow';
import { getWatchlistPinKey, type WatchlistSymbol } from './watchlistClient';
import { type WatchlistPinState, type WatchlistWorkflow, useWatchlistWorkflow } from './watchlistWorkflow';
import type { MarketDataSymbolIdentity, MarketDataSymbolSearchResult, TrendingSymbol } from '../types/marketData';
import type { EnabledTerminalModuleId, TerminalNavigationIntent } from '../types/terminal';

export const DefaultTerminalMarketMonitorSearchLimit = DefaultSymbolSearchRequestLimit;
export const DefaultTerminalMarketMonitorVisibleRowLimit = 18;
export const TerminalMarketMonitorVisibleRowIncrement = 12;

export type TerminalMarketMonitorRowSource = 'trending' | 'search' | 'watchlist';
export type TerminalMarketMonitorSortDirection = 'asc' | 'desc';
export type TerminalMarketMonitorSortKey =
  | 'source'
  | 'rank'
  | 'symbol'
  | 'name'
  | 'provider'
  | 'providerSymbolId'
  | 'exchange'
  | 'currency'
  | 'assetClass'
  | 'saved'
  | 'score'
  | 'changePercent';

export type TerminalMarketMonitorFilterKey = 'source' | 'provider' | 'exchange' | 'currency' | 'assetClass' | 'saved';

export type TerminalMarketMonitorSelectedFilters = Partial<Record<TerminalMarketMonitorFilterKey, string>>;

export type TerminalMarketMonitorSortState = {
  key: TerminalMarketMonitorSortKey;
  direction: TerminalMarketMonitorSortDirection;
};

export type TerminalMarketMonitorFilterOption = {
  value: string;
  label: string;
  count: number;
};

export type TerminalMarketMonitorAvailableFilters = Record<TerminalMarketMonitorFilterKey, TerminalMarketMonitorFilterOption[]>;

type TerminalMarketMonitorBaseRow = {
  id: string;
  instrumentKey: string;
  pinKey: string;
  source: TerminalMarketMonitorRowSource;
  sourceLabel: string;
  sourceRank: number;
  symbol: string;
  name: string | null;
  provider: string;
  providerSymbolId: string | null;
  ibkrConid: number | null;
  exchange: string | null;
  currency: string;
  assetClass: string;
  identity: NormalizedInstrumentIdentity;
  exactIdentity: MarketDataSymbolIdentity;
  chartHref: string;
  analysisHref: string;
  backtestHref: string;
  chartIntent: TerminalNavigationIntent;
  analysisIntent: TerminalNavigationIntent;
  backtestIntent: TerminalNavigationIntent;
  pinState: WatchlistPinState;
  saved: boolean;
  saving: boolean;
  disabled: boolean;
  score: number | null;
  rankLabel: string;
  lastPrice: number | null;
  changePercent: number | null;
  reasons: string[];
};

export type TerminalMarketMonitorTrendingRow = TerminalMarketMonitorBaseRow & {
  source: 'trending';
  trendingSymbol: TrendingSymbol;
};

export type TerminalMarketMonitorSearchRow = TerminalMarketMonitorBaseRow & {
  source: 'search';
  searchResult: MarketDataSymbolSearchResult;
  searchQuery: string;
};

export type TerminalMarketMonitorWatchlistRow = TerminalMarketMonitorBaseRow & {
  source: 'watchlist';
  watchlistSymbol: WatchlistSymbol;
};

export type TerminalMarketMonitorRow =
  | TerminalMarketMonitorTrendingRow
  | TerminalMarketMonitorSearchRow
  | TerminalMarketMonitorWatchlistRow;

export type TerminalMarketMonitorViewModel = {
  allRows: TerminalMarketMonitorRow[];
  filteredRows: TerminalMarketMonitorRow[];
  visibleRows: TerminalMarketMonitorRow[];
  selectedRow: TerminalMarketMonitorRow | null;
  selectedRowId: string | null;
  selectedFilters: TerminalMarketMonitorSelectedFilters;
  availableFilters: TerminalMarketMonitorAvailableFilters;
  sort: TerminalMarketMonitorSortState;
  totalRowCount: number;
  filteredRowCount: number;
  visibleRowLimit: number;
  canShowMore: boolean;
  canShowLess: boolean;
  sources: {
    trending: number;
    search: number;
    watchlist: number;
  };
};

export type TerminalMarketMonitorWorkflowOptions = {
  initialSearchQuery?: string;
  searchLimit?: number;
  minimumQueryLength?: number;
  initialSort?: TerminalMarketMonitorSortState;
};

export type TerminalMarketMonitorProviderState = {
  searchValidationMessage: string | null;
  searchError: string | null;
  watchlistError: string | null;
  watchlistSource: WatchlistWorkflow['source'];
  watchlistCachedFallback: boolean;
  trendingError: string | null;
};

export type TerminalMarketMonitorWorkflow = {
  trendingSymbols: TrendingSymbol[];
  trendingSource: string | null;
  trendingGeneratedAt: string | null;
  trendingLoading: boolean;
  trendingError: string | null;
  reloadTrending: () => void;
  search: SymbolSearchWorkflow;
  watchlist: WatchlistWorkflow;
  providerState: TerminalMarketMonitorProviderState;
  view: TerminalMarketMonitorViewModel;
  sort: TerminalMarketMonitorSortState;
  setSort: (key: TerminalMarketMonitorSortKey) => void;
  selectedFilters: TerminalMarketMonitorSelectedFilters;
  setFilter: (key: TerminalMarketMonitorFilterKey, value: string | null) => void;
  clearFilter: (key: TerminalMarketMonitorFilterKey) => void;
  clearFilters: () => void;
  selectRow: (rowId: string | null) => void;
  showMoreRows: () => void;
  showLessRows: () => void;
  toggleRowPin: (row: TerminalMarketMonitorRow) => Promise<void>;
  openChartIntent: (row: TerminalMarketMonitorRow) => TerminalNavigationIntent;
  openAnalysisIntent: (row: TerminalMarketMonitorRow) => TerminalNavigationIntent;
  openBacktestIntent: (row: TerminalMarketMonitorRow) => TerminalNavigationIntent;
  statusSummary: string;
};

const DefaultMonitorSort: TerminalMarketMonitorSortState = {
  key: 'rank',
  direction: 'asc',
};

const SourceOrder: Record<TerminalMarketMonitorRowSource, number> = {
  watchlist: 0,
  search: 1,
  trending: 2,
};

const EmptyAvailableFilters: TerminalMarketMonitorAvailableFilters = {
  source: [],
  provider: [],
  exchange: [],
  currency: [],
  assetClass: [],
  saved: [],
};

export function useTerminalMarketMonitorWorkflow({
  initialSearchQuery = '',
  searchLimit = DefaultTerminalMarketMonitorSearchLimit,
  minimumQueryLength = MinimumSymbolSearchQueryLength,
  initialSort = DefaultMonitorSort,
}: TerminalMarketMonitorWorkflowOptions = {}): TerminalMarketMonitorWorkflow {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [trendingSource, setTrendingSource] = useState<string | null>(null);
  const [trendingGeneratedAt, setTrendingGeneratedAt] = useState<string | null>(null);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const [trendingError, setTrendingError] = useState<string | null>(null);
  const [selectedFilters, setSelectedFilters] = useState<TerminalMarketMonitorSelectedFilters>({});
  const [sort, setSortState] = useState<TerminalMarketMonitorSortState>(initialSort);
  const [selectedRowId, setSelectedRowId] = useState<string | null>(null);
  const [visibleRowLimit, setVisibleRowLimit] = useState(DefaultTerminalMarketMonitorVisibleRowLimit);

  const boundedSearchLimit = clampSymbolSearchLimit(searchLimit);
  const search = useSymbolSearchWorkflow({
    limit: boundedSearchLimit,
    assetClass: 'stock',
    initialQuery: initialSearchQuery,
    minimumQueryLength,
  });
  const watchlist = useWatchlistWorkflow();

  const loadTrending = useCallback(async () => {
    setTrendingLoading(true);
    setTrendingError(null);

    try {
      const response = await getTrendingSymbols();
      setTrendingSymbols(response.symbols);
      setTrendingSource(response.source);
      setTrendingGeneratedAt(response.generatedAt);
    } catch (caughtError) {
      setTrendingSymbols([]);
      setTrendingSource(null);
      setTrendingGeneratedAt(null);
      setTrendingError(formatTerminalMarketMonitorError(caughtError));
    } finally {
      setTrendingLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTrending();
  }, [loadTrending]);

  const allRows = useMemo(
    () => [
      ...trendingSymbols.map((symbol, index) => createTrendingMonitorRow({
        symbol,
        index,
        sourceLabel: trendingSource,
        pinState: watchlist.getTrendingPinState(symbol),
      })),
      ...search.searchView.filteredResults.map((result, index) => createSearchMonitorRow({
        result,
        index,
        query: search.searchedQuery,
        pinState: watchlist.getSearchResultPinState(result),
      })),
      ...watchlist.symbols.map((symbol, index) => createWatchlistMonitorRow({
        symbol,
        index,
        sourceLabel: watchlist.source,
        pinState: watchlist.getWatchlistSymbolPinState(symbol),
      })),
    ],
    [
      search.searchView.filteredResults,
      search.searchedQuery,
      trendingSource,
      trendingSymbols,
      watchlist,
    ],
  );

  const view = useMemo(
    () => createTerminalMarketMonitorViewModel({
      rows: allRows,
      selectedFilters,
      sort,
      selectedRowId,
      visibleRowLimit,
    }),
    [allRows, selectedFilters, selectedRowId, sort, visibleRowLimit],
  );

  useEffect(() => {
    if (view.filteredRows.length === 0) {
      if (selectedRowId !== null) {
        setSelectedRowId(null);
      }
      return;
    }

    if (!selectedRowId || !view.filteredRows.some((row) => row.id === selectedRowId)) {
      setSelectedRowId(view.filteredRows[0].id);
    }
  }, [selectedRowId, view.filteredRows]);

  const setSort = useCallback((key: TerminalMarketMonitorSortKey) => {
    setSortState((currentSort) => ({
      key,
      direction: currentSort.key === key
        ? toggleSortDirection(currentSort.direction)
        : getDefaultSortDirection(key),
    }));
  }, []);

  const setFilter = useCallback((key: TerminalMarketMonitorFilterKey, value: string | null) => {
    setSelectedFilters((currentFilters) => {
      const nextFilters = { ...currentFilters };
      const normalizedValue = normalizeMonitorFilterValue(key, value ?? '');

      if (normalizedValue) {
        nextFilters[key] = normalizedValue;
      } else {
        delete nextFilters[key];
      }

      return nextFilters;
    });
    setVisibleRowLimit(DefaultTerminalMarketMonitorVisibleRowLimit);
  }, []);

  const clearFilter = useCallback((key: TerminalMarketMonitorFilterKey) => {
    setSelectedFilters((currentFilters) => {
      const nextFilters = { ...currentFilters };
      delete nextFilters[key];
      return nextFilters;
    });
    setVisibleRowLimit(DefaultTerminalMarketMonitorVisibleRowLimit);
  }, []);

  const clearFilters = useCallback(() => {
    setSelectedFilters({});
    setVisibleRowLimit(DefaultTerminalMarketMonitorVisibleRowLimit);
  }, []);

  const showMoreRows = useCallback(() => {
    setVisibleRowLimit((currentLimit) => Math.min(
      currentLimit + TerminalMarketMonitorVisibleRowIncrement,
      Math.max(view.filteredRowCount, DefaultTerminalMarketMonitorVisibleRowLimit),
    ));
  }, [view.filteredRowCount]);

  const showLessRows = useCallback(() => {
    setVisibleRowLimit(DefaultTerminalMarketMonitorVisibleRowLimit);
  }, []);

  const toggleRowPin = useCallback(
    async (row: TerminalMarketMonitorRow) => {
      if (row.source === 'trending') {
        await watchlist.toggleTrendingPin(row.trendingSymbol);
        return;
      }

      if (row.source === 'search') {
        await watchlist.toggleSearchPin(row.searchResult);
        return;
      }

      await watchlist.removePin(row.watchlistSymbol);
    },
    [watchlist],
  );

  const providerState = useMemo<TerminalMarketMonitorProviderState>(
    () => ({
      searchValidationMessage: search.validationMessage,
      searchError: search.error,
      watchlistError: watchlist.error,
      watchlistSource: watchlist.source,
      watchlistCachedFallback: watchlist.source === 'cache',
      trendingError,
    }),
    [search.error, search.validationMessage, trendingError, watchlist.error, watchlist.source],
  );

  const statusSummary = useMemo(
    () => buildTerminalMarketMonitorStatusSummary({
      trendingLoading,
      trendingError,
      trendingCount: trendingSymbols.length,
      searchLoading: search.loading,
      searchError: search.error,
      searchCount: search.searchView.filteredResultCount,
      watchlistLoading: watchlist.loading,
      watchlistError: watchlist.error,
      watchlistCount: watchlist.symbols.length,
    }),
    [
      search.error,
      search.loading,
      search.searchView.filteredResultCount,
      trendingError,
      trendingLoading,
      trendingSymbols.length,
      watchlist.error,
      watchlist.loading,
      watchlist.symbols.length,
    ],
  );

  return {
    trendingSymbols,
    trendingSource,
    trendingGeneratedAt,
    trendingLoading,
    trendingError,
    reloadTrending: () => void loadTrending(),
    search,
    watchlist,
    providerState,
    view,
    sort,
    setSort,
    selectedFilters: view.selectedFilters,
    setFilter,
    clearFilter,
    clearFilters,
    selectRow: setSelectedRowId,
    showMoreRows,
    showLessRows,
    toggleRowPin,
    openChartIntent: createChartNavigationIntent,
    openAnalysisIntent: createAnalysisNavigationIntent,
    openBacktestIntent: createBacktestNavigationIntent,
    statusSummary,
  };
}

export function createTerminalMarketMonitorViewModel({
  rows,
  selectedFilters = {},
  sort = DefaultMonitorSort,
  selectedRowId = null,
  visibleRowLimit = DefaultTerminalMarketMonitorVisibleRowLimit,
}: {
  rows: TerminalMarketMonitorRow[];
  selectedFilters?: TerminalMarketMonitorSelectedFilters;
  sort?: TerminalMarketMonitorSortState;
  selectedRowId?: string | null;
  visibleRowLimit?: number;
}): TerminalMarketMonitorViewModel {
  const normalizedFilters = normalizeMonitorFilters(selectedFilters);
  const filteredRows = rows
    .filter((row) => rowMatchesFilters(row, normalizedFilters))
    .toSorted((left, right) => compareMonitorRows(left, right, sort));
  const boundedVisibleLimit = clampVisibleRowLimit(visibleRowLimit);
  const visibleRows = filteredRows.slice(0, boundedVisibleLimit);
  const selectedRow = filteredRows.find((row) => row.id === selectedRowId) ?? visibleRows[0] ?? null;

  return {
    allRows: rows,
    filteredRows,
    visibleRows,
    selectedRow,
    selectedRowId: selectedRow?.id ?? null,
    selectedFilters: normalizedFilters,
    availableFilters: buildAvailableMonitorFilters(rows),
    sort,
    totalRowCount: rows.length,
    filteredRowCount: filteredRows.length,
    visibleRowLimit: boundedVisibleLimit,
    canShowMore: filteredRows.length > visibleRows.length,
    canShowLess: boundedVisibleLimit > DefaultTerminalMarketMonitorVisibleRowLimit && filteredRows.length > DefaultTerminalMarketMonitorVisibleRowLimit,
    sources: countMonitorSources(rows),
  };
}

export function createTrendingMonitorRow({
  symbol,
  index,
  sourceLabel,
  pinState,
}: {
  symbol: TrendingSymbol;
  index: number;
  sourceLabel: string | null;
  pinState: WatchlistPinState;
}): TerminalMarketMonitorTrendingRow {
  const identity = getTrendingSymbolIdentity(symbol);
  const rank = index + 1;
  const row = createBaseMonitorRow({
    source: 'trending',
    sourceLabel: sourceLabel ?? 'provider trending',
    sourceRank: rank,
    identity,
    name: symbol.name,
    pinState,
    score: symbol.score,
    rankLabel: `TRD ${rank}`,
    lastPrice: finiteNumberOrNull(symbol.lastPrice),
    changePercent: finiteNumberOrNull(symbol.changePercent),
    reasons: symbol.reasons,
  });

  return {
    ...row,
    source: 'trending',
    trendingSymbol: symbol,
  };
}

export function createSearchMonitorRow({
  result,
  index,
  query,
  pinState,
}: {
  result: MarketDataSymbolSearchResult;
  index: number;
  query: string;
  pinState: WatchlistPinState;
}): TerminalMarketMonitorSearchRow {
  const identity = getSearchResultIdentity(result);
  const rank = index + 1;
  const row = createBaseMonitorRow({
    source: 'search',
    sourceLabel: query ? `search:${query}` : 'bounded search',
    sourceRank: rank,
    identity,
    name: result.name,
    pinState,
    score: rank,
    rankLabel: `SRCH ${rank}`,
    lastPrice: null,
    changePercent: null,
    reasons: [],
  });

  return {
    ...row,
    source: 'search',
    searchResult: result,
    searchQuery: query,
  };
}

export function createWatchlistMonitorRow({
  symbol,
  index,
  sourceLabel,
  pinState,
}: {
  symbol: WatchlistSymbol;
  index: number;
  sourceLabel: string;
  pinState: WatchlistPinState;
}): TerminalMarketMonitorWatchlistRow {
  const identity = normalizeInstrumentIdentity({
    symbol: symbol.symbol,
    provider: symbol.provider,
    providerSymbolId: symbol.providerSymbolId,
    ibkrConid: symbol.ibkrConid,
    exchange: symbol.exchange,
    currency: symbol.currency,
    assetClass: symbol.assetClass,
  });
  const rank = Number.isFinite(symbol.sortOrder) ? symbol.sortOrder + 1 : index + 1;
  const row = createBaseMonitorRow({
    source: 'watchlist',
    sourceLabel: sourceLabel === 'cache' ? 'cached watchlist fallback' : 'backend watchlist',
    sourceRank: rank,
    identity,
    name: symbol.name,
    pinState,
    score: null,
    rankLabel: `PIN ${rank}`,
    lastPrice: null,
    changePercent: null,
    reasons: [],
    instrumentKey: getWatchlistPinKey(symbol),
  });

  return {
    ...row,
    source: 'watchlist',
    watchlistSymbol: symbol,
  };
}

export function createChartNavigationIntent(row: TerminalMarketMonitorRow): TerminalNavigationIntent {
  return createRowNavigationIntent(row, 'CHART');
}

export function createAnalysisNavigationIntent(row: TerminalMarketMonitorRow): TerminalNavigationIntent {
  return createRowNavigationIntent(row, 'ANALYSIS');
}

export function createBacktestNavigationIntent(row: TerminalMarketMonitorRow): TerminalNavigationIntent {
  return createRowNavigationIntent(row, 'BACKTEST');
}

export function formatTerminalMarketMonitorError(caughtError: unknown): string {
  return caughtError instanceof Error ? caughtError.message : 'Provider-backed market monitor data is unavailable.';
}

function createBaseMonitorRow({
  source,
  sourceLabel,
  sourceRank,
  identity,
  name,
  pinState,
  score,
  rankLabel,
  lastPrice,
  changePercent,
  reasons,
  instrumentKey = createProvisionalInstrumentKey(identity),
}: {
  source: TerminalMarketMonitorRowSource;
  sourceLabel: string;
  sourceRank: number;
  identity: NormalizedInstrumentIdentity;
  name: string | null;
  pinState: WatchlistPinState;
  score: number | null;
  rankLabel: string;
  lastPrice: number | null;
  changePercent: number | null;
  reasons: string[];
  instrumentKey?: string;
}): TerminalMarketMonitorBaseRow {
  const exactIdentity = toMarketDataSymbolIdentity(identity);
  const chartHref = createSymbolChartHref(identity);
  const analysisHref = createModuleHref(identity, 'ANALYSIS');
  const backtestHref = createModuleHref(identity, 'BACKTEST');
  const pinKey = pinState.pinKey || instrumentKey;
  const rowId = `${source}:${pinKey}:${sourceRank}`;
  const base = {
    id: rowId,
    instrumentKey,
    pinKey,
    source,
    sourceLabel,
    sourceRank,
    symbol: identity.symbol,
    name,
    provider: identity.provider,
    providerSymbolId: identity.providerSymbolId,
    ibkrConid: identity.ibkrConid ?? parseIbkrConid(identity.provider, identity.providerSymbolId),
    exchange: identity.exchange,
    currency: identity.currency,
    assetClass: identity.assetClass,
    identity,
    exactIdentity,
    chartHref,
    analysisHref,
    backtestHref,
    pinState,
    saved: pinState.pinned,
    saving: pinState.saving,
    disabled: pinState.disabled,
    score,
    rankLabel,
    lastPrice,
    changePercent,
    reasons,
  };

  return {
    ...base,
    chartIntent: createRowNavigationIntentFromBase(base, 'CHART'),
    analysisIntent: createRowNavigationIntentFromBase(base, 'ANALYSIS'),
    backtestIntent: createRowNavigationIntentFromBase(base, 'BACKTEST'),
  };
}

function createRowNavigationIntent(row: TerminalMarketMonitorRow, moduleId: Extract<EnabledTerminalModuleId, 'CHART' | 'ANALYSIS' | 'BACKTEST'>): TerminalNavigationIntent {
  return createRowNavigationIntentFromBase(row, moduleId);
}

function createRowNavigationIntentFromBase(
  row: Pick<TerminalMarketMonitorBaseRow, 'analysisHref' | 'backtestHref' | 'chartHref' | 'exactIdentity' | 'symbol'>,
  moduleId: Extract<EnabledTerminalModuleId, 'CHART' | 'ANALYSIS' | 'BACKTEST'>,
): TerminalNavigationIntent {
  return {
    moduleId,
    route: moduleId === 'ANALYSIS' ? row.analysisHref : moduleId === 'BACKTEST' ? row.backtestHref : row.chartHref,
    focusTargetId: moduleId === 'ANALYSIS' ? 'terminal-analysis' : moduleId === 'BACKTEST' ? 'terminal-backtest' : 'terminal-chart',
    symbol: row.symbol,
    identity: row.exactIdentity,
    chartRange: '1D',
  };
}

function createModuleHref(identity: InstrumentIdentityInput, moduleId: Extract<EnabledTerminalModuleId, 'ANALYSIS' | 'BACKTEST'>): string {
  const chartHref = createSymbolChartHref(identity);
  const [path, query = ''] = chartHref.split('?');
  const params = new URLSearchParams(query);
  params.set('module', moduleId);
  const serialized = params.toString();
  return serialized ? `${path}?${serialized}` : path;
}

function toMarketDataSymbolIdentity(identity: NormalizedInstrumentIdentity): MarketDataSymbolIdentity {
  return {
    symbol: identity.symbol,
    provider: identity.provider,
    providerSymbolId: identity.providerSymbolId,
    assetClass: identity.assetClass,
    exchange: identity.exchange ?? '',
    currency: identity.currency,
  };
}

function rowMatchesFilters(row: TerminalMarketMonitorRow, filters: TerminalMarketMonitorSelectedFilters): boolean {
  return (Object.entries(filters) as [TerminalMarketMonitorFilterKey, string][]).every(([key, value]) => {
    if (!value) {
      return true;
    }

    return getMonitorFilterValue(row, key) === value;
  });
}

function buildAvailableMonitorFilters(rows: TerminalMarketMonitorRow[]): TerminalMarketMonitorAvailableFilters {
  if (rows.length === 0) {
    return EmptyAvailableFilters;
  }

  const counters = (Object.keys(EmptyAvailableFilters) as TerminalMarketMonitorFilterKey[]).reduce((accumulator, key) => {
    accumulator[key] = new Map<string, number>();
    return accumulator;
  }, {} as Record<TerminalMarketMonitorFilterKey, Map<string, number>>);

  for (const row of rows) {
    for (const key of Object.keys(counters) as TerminalMarketMonitorFilterKey[]) {
      const value = getMonitorFilterValue(row, key);
      if (value) {
        counters[key].set(value, (counters[key].get(value) ?? 0) + 1);
      }
    }
  }

  return (Object.keys(counters) as TerminalMarketMonitorFilterKey[]).reduce((accumulator, key) => {
    accumulator[key] = Array.from(counters[key].entries())
      .map(([value, count]) => ({ value, label: formatMonitorFilterLabel(key, value), count }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
    return accumulator;
  }, {} as TerminalMarketMonitorAvailableFilters);
}

function getMonitorFilterValue(row: TerminalMarketMonitorRow, key: TerminalMarketMonitorFilterKey): string {
  switch (key) {
    case 'source':
      return row.source;
    case 'provider':
      return normalizeTextFacet(row.provider);
    case 'exchange':
      return normalizeTextFacet(row.exchange ?? '');
    case 'currency':
      return normalizeTextFacet(row.currency);
    case 'assetClass':
      return normalizeTextFacet(row.assetClass);
    case 'saved':
      return row.saved ? 'saved' : 'unsaved';
    default:
      return '';
  }
}

function normalizeMonitorFilters(filters: TerminalMarketMonitorSelectedFilters): TerminalMarketMonitorSelectedFilters {
  return (Object.entries(filters) as [TerminalMarketMonitorFilterKey, string][]).reduce((normalized, [key, value]) => {
    const normalizedValue = normalizeMonitorFilterValue(key, value);
    if (normalizedValue) {
      normalized[key] = normalizedValue;
    }

    return normalized;
  }, {} as TerminalMarketMonitorSelectedFilters);
}

function normalizeMonitorFilterValue(key: TerminalMarketMonitorFilterKey, value: string): string {
  if (key === 'source') {
    const normalized = value.trim().toLowerCase();
    return normalized === 'trending' || normalized === 'search' || normalized === 'watchlist' ? normalized : '';
  }

  if (key === 'saved') {
    const normalized = value.trim().toLowerCase();
    return normalized === 'saved' || normalized === 'unsaved' ? normalized : '';
  }

  return normalizeTextFacet(value);
}

function normalizeTextFacet(value: string): string {
  return value.trim().toUpperCase();
}

function formatMonitorFilterLabel(key: TerminalMarketMonitorFilterKey, value: string): string {
  if (key === 'source') {
    return value === 'watchlist' ? 'Watchlist' : value === 'search' ? 'Search' : 'Trending';
  }

  if (key === 'saved') {
    return value === 'saved' ? 'Saved pins' : 'Not saved';
  }

  if (key === 'provider') {
    return value.toUpperCase();
  }

  if (key === 'assetClass' && value === 'STK') {
    return 'Stock';
  }

  return value;
}

function compareMonitorRows(left: TerminalMarketMonitorRow, right: TerminalMarketMonitorRow, sort: TerminalMarketMonitorSortState): number {
  const direction = sort.direction === 'asc' ? 1 : -1;
  const compared = compareMonitorValues(getSortValue(left, sort.key), getSortValue(right, sort.key));

  if (compared !== 0) {
    return compared * direction;
  }

  return SourceOrder[left.source] - SourceOrder[right.source]
    || left.sourceRank - right.sourceRank
    || left.symbol.localeCompare(right.symbol);
}

function getSortValue(row: TerminalMarketMonitorRow, key: TerminalMarketMonitorSortKey): string | number | boolean | null {
  switch (key) {
    case 'source':
      return SourceOrder[row.source];
    case 'rank':
      return row.sourceRank;
    case 'symbol':
      return row.symbol;
    case 'name':
      return row.name ?? '';
    case 'provider':
      return row.provider;
    case 'providerSymbolId':
      return row.providerSymbolId ?? '';
    case 'exchange':
      return row.exchange ?? '';
    case 'currency':
      return row.currency;
    case 'assetClass':
      return row.assetClass;
    case 'saved':
      return row.saved;
    case 'score':
      return row.score;
    case 'changePercent':
      return row.changePercent;
    default:
      return null;
  }
}

function compareMonitorValues(left: string | number | boolean | null, right: string | number | boolean | null): number {
  if (left === null && right === null) {
    return 0;
  }

  if (left === null) {
    return 1;
  }

  if (right === null) {
    return -1;
  }

  if (typeof left === 'number' && typeof right === 'number') {
    return left - right;
  }

  if (typeof left === 'boolean' && typeof right === 'boolean') {
    return Number(right) - Number(left);
  }

  return String(left).localeCompare(String(right));
}

function toggleSortDirection(direction: TerminalMarketMonitorSortDirection): TerminalMarketMonitorSortDirection {
  return direction === 'asc' ? 'desc' : 'asc';
}

function getDefaultSortDirection(key: TerminalMarketMonitorSortKey): TerminalMarketMonitorSortDirection {
  return key === 'score' || key === 'changePercent' || key === 'saved' ? 'desc' : 'asc';
}

function clampVisibleRowLimit(limit: number): number {
  if (!Number.isFinite(limit)) {
    return DefaultTerminalMarketMonitorVisibleRowLimit;
  }

  return Math.max(DefaultTerminalMarketMonitorVisibleRowLimit, Math.trunc(limit));
}

function countMonitorSources(rows: TerminalMarketMonitorRow[]): TerminalMarketMonitorViewModel['sources'] {
  return rows.reduce(
    (counts, row) => {
      counts[row.source] += 1;
      return counts;
    },
    { trending: 0, search: 0, watchlist: 0 },
  );
}

function finiteNumberOrNull(value: number): number | null {
  return Number.isFinite(value) ? value : null;
}

function buildTerminalMarketMonitorStatusSummary({
  trendingLoading,
  trendingError,
  trendingCount,
  searchLoading,
  searchError,
  searchCount,
  watchlistLoading,
  watchlistError,
  watchlistCount,
}: {
  trendingLoading: boolean;
  trendingError: string | null;
  trendingCount: number;
  searchLoading: boolean;
  searchError: string | null;
  searchCount: number;
  watchlistLoading: boolean;
  watchlistError: string | null;
  watchlistCount: number;
}): string {
  const trendingStatus = trendingLoading ? 'trending loading' : trendingError ? 'trending unavailable' : `${trendingCount} trending`;
  const searchStatus = searchLoading ? 'search loading' : searchError ? 'search unavailable' : `${searchCount} search`;
  const watchlistStatus = watchlistLoading ? 'watchlist loading' : watchlistError ? 'watchlist fallback/error' : `${watchlistCount} pins`;

  return `${trendingStatus} · ${searchStatus} · ${watchlistStatus}`;
}
