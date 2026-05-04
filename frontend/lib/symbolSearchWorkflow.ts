'use client';

import { useEffect, useMemo, useState } from 'react';
import { searchSymbols } from './marketDataClient';
import type { MarketDataSymbolSearchResult } from '../types/marketData';

export const MinimumSymbolSearchQueryLength = 2;
export const SymbolSearchDebounceMs = 350;

export const DefaultSymbolSearchRequestLimit = 25;
export const MaximumSymbolSearchRequestLimit = 50;
export const DefaultSymbolSearchVisibleLimit = 5;
export const SymbolSearchVisibleResultIncrement = 5;

export type SymbolSearchFilterKey = 'exchange' | 'currency' | 'assetClass' | 'provider';

export const SymbolSearchFilterLabels: Record<SymbolSearchFilterKey, string> = {
  exchange: 'Market',
  currency: 'Currency',
  assetClass: 'Asset',
  provider: 'Provider',
};

export type SymbolSearchSelectedFilters = Partial<Record<SymbolSearchFilterKey, string>>;

export type SymbolSearchFilterOption = {
  value: string;
  label: string;
  count: number;
};

export type SymbolSearchAvailableFilters = Record<SymbolSearchFilterKey, SymbolSearchFilterOption[]>;

export type SymbolSearchResultViewModel = {
  query: string;
  allResults: MarketDataSymbolSearchResult[];
  rankedResults: MarketDataSymbolSearchResult[];
  filteredResults: MarketDataSymbolSearchResult[];
  visibleResults: MarketDataSymbolSearchResult[];
  bestMatch: MarketDataSymbolSearchResult | null;
  totalResultCount: number;
  filteredResultCount: number;
  visibleResultLimit: number;
  selectedFilters: SymbolSearchSelectedFilters;
  availableFilters: SymbolSearchAvailableFilters;
  canShowMore: boolean;
  canShowLess: boolean;
};

export type SymbolSearchWorkflowOptions = {
  limit?: number;
  assetClass?: string;
  initialQuery?: string;
  minimumQueryLength?: number;
};

const SymbolSearchFilterKeys: SymbolSearchFilterKey[] = ['exchange', 'currency', 'assetClass', 'provider'];

export function createSymbolSearchResultsViewModel({
  query,
  results,
  selectedFilters = {},
  visibleResultLimit = DefaultSymbolSearchVisibleLimit,
}: {
  query: string;
  results: MarketDataSymbolSearchResult[];
  selectedFilters?: SymbolSearchSelectedFilters;
  visibleResultLimit?: number;
}): SymbolSearchResultViewModel {
  const rankedResults = rankSymbolSearchResults(results, query);
  const normalizedFilters = normalizeSymbolSearchFilters(selectedFilters);
  const filteredResults = applySymbolSearchFilters(rankedResults, normalizedFilters);
  const boundedVisibleLimit = clampVisibleResultLimit(visibleResultLimit);
  const visibleResults = filteredResults.slice(0, boundedVisibleLimit);

  return {
    query,
    allResults: results,
    rankedResults,
    filteredResults,
    visibleResults,
    bestMatch: filteredResults[0] ?? null,
    totalResultCount: results.length,
    filteredResultCount: filteredResults.length,
    visibleResultLimit: boundedVisibleLimit,
    selectedFilters: normalizedFilters,
    availableFilters: buildAvailableSymbolSearchFilters(rankedResults),
    canShowMore: filteredResults.length > visibleResults.length,
    canShowLess: boundedVisibleLimit > DefaultSymbolSearchVisibleLimit && filteredResults.length > DefaultSymbolSearchVisibleLimit,
  };
}

export function rankSymbolSearchResults(results: MarketDataSymbolSearchResult[], query: string): MarketDataSymbolSearchResult[] {
  const normalizedQuery = normalizeSearchFacet(query);

  return results
    .map((result, index) => ({
      result,
      index,
      score: getSymbolSearchRankScore(result, normalizedQuery),
    }))
    .sort((left, right) => left.score - right.score || left.index - right.index)
    .map(({ result }) => result);
}

export function applySymbolSearchFilters(
  results: MarketDataSymbolSearchResult[],
  selectedFilters: SymbolSearchSelectedFilters,
): MarketDataSymbolSearchResult[] {
  const normalizedFilters = normalizeSymbolSearchFilters(selectedFilters);

  return results.filter((result) => SymbolSearchFilterKeys.every((key) => {
    const selectedValue = normalizedFilters[key];
    return !selectedValue || getResultFilterValue(result, key) === selectedValue;
  }));
}

export function buildAvailableSymbolSearchFilters(results: MarketDataSymbolSearchResult[]): SymbolSearchAvailableFilters {
  const counters = SymbolSearchFilterKeys.reduce((accumulator, key) => {
    accumulator[key] = new Map<string, number>();
    return accumulator;
  }, {} as Record<SymbolSearchFilterKey, Map<string, number>>);

  for (const result of results) {
    for (const key of SymbolSearchFilterKeys) {
      const value = getResultFilterValue(result, key);
      if (value) {
        counters[key].set(value, (counters[key].get(value) ?? 0) + 1);
      }
    }
  }

  return SymbolSearchFilterKeys.reduce((accumulator, key) => {
    accumulator[key] = Array.from(counters[key].entries())
      .map(([value, count]) => ({ value, label: formatFilterOptionLabel(key, value), count }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
    return accumulator;
  }, {} as SymbolSearchAvailableFilters);
}

export function clampSymbolSearchLimit(limit: number): number {
  if (!Number.isFinite(limit)) {
    return DefaultSymbolSearchRequestLimit;
  }

  return Math.min(Math.max(Math.trunc(limit), DefaultSymbolSearchVisibleLimit), MaximumSymbolSearchRequestLimit);
}

function clampVisibleResultLimit(limit: number): number {
  if (!Number.isFinite(limit)) {
    return DefaultSymbolSearchVisibleLimit;
  }

  return Math.min(Math.max(Math.trunc(limit), DefaultSymbolSearchVisibleLimit), MaximumSymbolSearchRequestLimit);
}

function normalizeSymbolSearchFilters(selectedFilters: SymbolSearchSelectedFilters): SymbolSearchSelectedFilters {
  return SymbolSearchFilterKeys.reduce((normalized, key) => {
    const value = normalizeSearchFacet(selectedFilters[key] ?? '');
    if (value) {
      normalized[key] = value;
    }

    return normalized;
  }, {} as SymbolSearchSelectedFilters);
}

function getSymbolSearchRankScore(result: MarketDataSymbolSearchResult, normalizedQuery: string): number {
  if (!normalizedQuery) {
    return 10;
  }

  const symbol = normalizeSearchFacet(result.symbol || result.identity.symbol);
  const providerSymbolId = normalizeSearchFacet(result.providerSymbolId ?? result.identity.providerSymbolId ?? '');
  const name = normalizeSearchFacet(result.name);

  if (symbol === normalizedQuery) {
    return 0;
  }

  if (providerSymbolId === normalizedQuery) {
    return 1;
  }

  if (symbol.startsWith(normalizedQuery)) {
    return 2;
  }

  if (name === normalizedQuery) {
    return 3;
  }

  if (name.startsWith(normalizedQuery)) {
    return 4;
  }

  if (symbol.includes(normalizedQuery)) {
    return 5;
  }

  if (name.includes(normalizedQuery)) {
    return 6;
  }

  return 7;
}

function getResultFilterValue(result: MarketDataSymbolSearchResult, key: SymbolSearchFilterKey): string {
  if (key === 'exchange') {
    return normalizeSearchFacet(result.exchange || result.identity.exchange);
  }

  if (key === 'currency') {
    return normalizeSearchFacet(result.currency || result.identity.currency);
  }

  if (key === 'assetClass') {
    return normalizeSearchFacet(result.assetClass || result.identity.assetClass);
  }

  return normalizeSearchFacet(result.provider || result.identity.provider);
}

function formatFilterOptionLabel(key: SymbolSearchFilterKey, value: string): string {
  if (key === 'assetClass' && value === 'STK') {
    return 'Stock';
  }

  if (key === 'provider') {
    return value.toUpperCase();
  }

  return value;
}

function normalizeSearchFacet(value: string): string {
  return value.trim().toUpperCase();
}

export type SymbolSearchWorkflow = {
  query: string;
  setQuery: (query: string) => void;
  searchedQuery: string;
  results: MarketDataSymbolSearchResult[];
  allResults: MarketDataSymbolSearchResult[];
  searchView: SymbolSearchResultViewModel;
  selectedFilters: SymbolSearchSelectedFilters;
  setFilter: (key: SymbolSearchFilterKey, value: string | null) => void;
  clearFilter: (key: SymbolSearchFilterKey) => void;
  clearFilters: () => void;
  showMoreResults: () => void;
  showLessResults: () => void;
  loading: boolean;
  error: string | null;
  validationMessage: string | null;
};

export function useSymbolSearchWorkflow({
  limit = DefaultSymbolSearchRequestLimit,
  assetClass = 'stock',
  initialQuery = '',
  minimumQueryLength = MinimumSymbolSearchQueryLength,
}: SymbolSearchWorkflowOptions): SymbolSearchWorkflow {
  const [query, setQuery] = useState(initialQuery);
  const [appliedInitialQuery, setAppliedInitialQuery] = useState(initialQuery.trim());
  const [searchedQuery, setSearchedQuery] = useState('');
  const [rawResults, setRawResults] = useState<MarketDataSymbolSearchResult[]>([]);
  const [selectedFilters, setSelectedFilters] = useState<SymbolSearchSelectedFilters>({});
  const [visibleResultLimit, setVisibleResultLimit] = useState(DefaultSymbolSearchVisibleLimit);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const boundedSearchLimit = clampSymbolSearchLimit(limit);

  const searchView = useMemo(
    () => createSymbolSearchResultsViewModel({
      query: searchedQuery,
      results: rawResults,
      selectedFilters,
      visibleResultLimit,
    }),
    [rawResults, searchedQuery, selectedFilters, visibleResultLimit],
  );

  useEffect(() => {
    const seededQuery = initialQuery.trim();
    if (seededQuery && seededQuery !== appliedInitialQuery) {
      setAppliedInitialQuery(seededQuery);
      setQuery(seededQuery);
    }
  }, [appliedInitialQuery, initialQuery]);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (trimmedQuery.length === 0) {
      setLoading(false);
      setError(null);
      setValidationMessage(null);
      setSearchedQuery('');
      setRawResults([]);
      resetSymbolSearchExploration(setSelectedFilters, setVisibleResultLimit);
      return;
    }

    if (trimmedQuery.length < minimumQueryLength) {
      setLoading(false);
      setError(null);
      setValidationMessage(`Type at least ${minimumQueryLength} characters to search IBKR stocks.`);
      setSearchedQuery('');
      setRawResults([]);
      resetSymbolSearchExploration(setSelectedFilters, setVisibleResultLimit);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    setValidationMessage(null);

    const timeout = window.setTimeout(() => {
      void searchSymbols(trimmedQuery, { assetClass, limit: boundedSearchLimit })
        .then((response) => {
          if (!active) {
            return;
          }

          setRawResults(response.results);
          setSearchedQuery(trimmedQuery);
          resetSymbolSearchExploration(setSelectedFilters, setVisibleResultLimit);
        })
        .catch((caughtError) => {
          if (!active) {
            return;
          }

          setRawResults([]);
          setSearchedQuery(trimmedQuery);
          resetSymbolSearchExploration(setSelectedFilters, setVisibleResultLimit);
          setError(formatSymbolSearchWorkflowError(caughtError));
        })
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
    }, SymbolSearchDebounceMs);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [assetClass, boundedSearchLimit, minimumQueryLength, query]);

  const setFilter = (key: SymbolSearchFilterKey, value: string | null) => {
    setSelectedFilters((currentFilters) => {
      const nextFilters = { ...currentFilters };
      const normalizedValue = normalizeSearchFacet(value ?? '');

      if (normalizedValue) {
        nextFilters[key] = normalizedValue;
      } else {
        delete nextFilters[key];
      }

      return nextFilters;
    });
    setVisibleResultLimit(DefaultSymbolSearchVisibleLimit);
  };

  const clearFilter = (key: SymbolSearchFilterKey) => {
    setSelectedFilters((currentFilters) => {
      const nextFilters = { ...currentFilters };
      delete nextFilters[key];
      return nextFilters;
    });
    setVisibleResultLimit(DefaultSymbolSearchVisibleLimit);
  };

  const clearFilters = () => {
    resetSymbolSearchExploration(setSelectedFilters, setVisibleResultLimit);
  };

  const showMoreResults = () => {
    setVisibleResultLimit((currentLimit) => Math.min(
      currentLimit + SymbolSearchVisibleResultIncrement,
      Math.max(searchView.filteredResultCount, DefaultSymbolSearchVisibleLimit),
    ));
  };

  const showLessResults = () => {
    setVisibleResultLimit(DefaultSymbolSearchVisibleLimit);
  };

  return {
    query,
    setQuery,
    searchedQuery,
    results: searchView.visibleResults,
    allResults: rawResults,
    searchView,
    selectedFilters: searchView.selectedFilters,
    setFilter,
    clearFilter,
    clearFilters,
    showMoreResults,
    showLessResults,
    loading,
    error,
    validationMessage,
  };
}

function resetSymbolSearchExploration(
  setSelectedFilters: (filters: SymbolSearchSelectedFilters) => void,
  setVisibleResultLimit: (limit: number) => void,
): void {
  setSelectedFilters({});
  setVisibleResultLimit(DefaultSymbolSearchVisibleLimit);
}

export function formatSymbolSearchWorkflowError(caughtError: unknown): string {
  return caughtError instanceof Error ? caughtError.message : 'IBKR stock search is unavailable.';
}
