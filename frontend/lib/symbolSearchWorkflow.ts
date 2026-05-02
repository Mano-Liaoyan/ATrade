'use client';

import { useEffect, useState } from 'react';
import { searchSymbols } from './marketDataClient';
import type { MarketDataSymbolSearchResult } from '../types/marketData';

export const MinimumSymbolSearchQueryLength = 2;
export const SymbolSearchDebounceMs = 350;

export type SymbolSearchWorkflowOptions = {
  limit: number;
  assetClass?: string;
  minimumQueryLength?: number;
};

export type SymbolSearchWorkflow = {
  query: string;
  setQuery: (query: string) => void;
  searchedQuery: string;
  results: MarketDataSymbolSearchResult[];
  loading: boolean;
  error: string | null;
  validationMessage: string | null;
};

export function useSymbolSearchWorkflow({
  limit,
  assetClass = 'stock',
  minimumQueryLength = MinimumSymbolSearchQueryLength,
}: SymbolSearchWorkflowOptions): SymbolSearchWorkflow {
  const [query, setQuery] = useState('');
  const [searchedQuery, setSearchedQuery] = useState('');
  const [results, setResults] = useState<MarketDataSymbolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (trimmedQuery.length === 0) {
      setLoading(false);
      setError(null);
      setValidationMessage(null);
      setSearchedQuery('');
      setResults([]);
      return;
    }

    if (trimmedQuery.length < minimumQueryLength) {
      setLoading(false);
      setError(null);
      setValidationMessage(`Type at least ${minimumQueryLength} characters to search IBKR stocks.`);
      setSearchedQuery('');
      setResults([]);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    setValidationMessage(null);

    const timeout = window.setTimeout(() => {
      void searchSymbols(trimmedQuery, { assetClass, limit })
        .then((response) => {
          if (!active) {
            return;
          }

          setResults(response.results);
          setSearchedQuery(trimmedQuery);
        })
        .catch((caughtError) => {
          if (!active) {
            return;
          }

          setResults([]);
          setSearchedQuery(trimmedQuery);
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
  }, [assetClass, limit, minimumQueryLength, query]);

  return {
    query,
    setQuery,
    searchedQuery,
    results,
    loading,
    error,
    validationMessage,
  };
}

export function formatSymbolSearchWorkflowError(caughtError: unknown): string {
  return caughtError instanceof Error ? caughtError.message : 'IBKR stock search is unavailable.';
}
