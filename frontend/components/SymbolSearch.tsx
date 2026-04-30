'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { searchSymbols } from '../lib/marketDataClient';
import { createWatchlistInstrumentKey, normalizeWatchlistAssetClass } from '../lib/watchlistClient';
import type { MarketDataSymbolSearchResult } from '../types/marketData';

type SymbolSearchProps = {
  title?: string;
  description?: string;
  limit?: number;
  pinnedInstrumentKeys?: string[];
  actionsDisabled?: boolean;
  savingPinKey?: string | null;
  onTogglePin?: (result: MarketDataSymbolSearchResult) => void;
  compact?: boolean;
};

const MinimumQueryLength = 2;

export function SymbolSearch({
  title = 'Search IBKR stocks',
  description = 'Find stocks from the IBKR/iBeam instrument universe, open a chart, or pin the exact provider-market result to your watchlist.',
  limit = 10,
  pinnedInstrumentKeys = [],
  actionsDisabled = false,
  savingPinKey = null,
  onTogglePin,
  compact = false,
}: SymbolSearchProps) {
  const [query, setQuery] = useState('');
  const [searchedQuery, setSearchedQuery] = useState('');
  const [results, setResults] = useState<MarketDataSymbolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const pinnedSet = useMemo(() => new Set(pinnedInstrumentKeys), [pinnedInstrumentKeys]);

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

    if (trimmedQuery.length < MinimumQueryLength) {
      setLoading(false);
      setError(null);
      setValidationMessage(`Type at least ${MinimumQueryLength} characters to search IBKR stocks.`);
      setSearchedQuery('');
      setResults([]);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    setValidationMessage(null);

    const timeout = window.setTimeout(() => {
      void searchSymbols(trimmedQuery, { assetClass: 'stock', limit })
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
          setError(caughtError instanceof Error ? caughtError.message : 'IBKR stock search is unavailable.');
        })
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
    }, 350);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [limit, query]);

  return (
    <section className={compact ? 'workspace-panel symbol-search-panel symbol-search-panel--compact' : 'workspace-panel symbol-search-panel'} data-testid="symbol-search">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">IBKR instrument search</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <span className="pill">IBKR/iBeam</span>
      </div>

      <label className="symbol-search-input-label" htmlFor={compact ? 'symbol-search-compact-query' : 'symbol-search-query'}>
        Symbol or company name
      </label>
      <input
        id={compact ? 'symbol-search-compact-query' : 'symbol-search-query'}
        className="symbol-search-input"
        type="search"
        value={query}
        autoComplete="off"
        placeholder="Type at least two characters"
        onChange={(event) => setQuery(event.target.value)}
      />

      {validationMessage ? <p className="symbol-search-help">{validationMessage}</p> : null}
      {loading ? <p className="symbol-search-help" role="status">Searching IBKR/iBeam contracts…</p> : null}
      {error ? (
        <div className="error-state symbol-search-message" role="alert">
          <strong>IBKR stock search unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}
      {!loading && !error && searchedQuery && results.length === 0 ? (
        <div className="empty-state symbol-search-message">
          <strong>No IBKR stock results found.</strong>
          <p>Try a different symbol or company name. No local fallback catalog is used.</p>
        </div>
      ) : null}

      {results.length > 0 ? (
        <ul className="symbol-search-results" aria-label="IBKR stock search results">
          {results.map((result) => {
            const symbol = getResultSymbol(result);
            const provider = result.provider || result.identity.provider;
            const providerSymbolId = result.providerSymbolId ?? result.identity.providerSymbolId;
            const pinKey = createSearchResultPinKey(result);
            const pinned = pinnedSet.has(pinKey);
            const isSaving = savingPinKey === pinKey;

            return (
              <li key={pinKey} aria-label={`${symbol} ${result.name} on ${result.exchange || result.identity.exchange}`}>
                <div>
                  <Link className="symbol-link" href={`/symbols/${encodeURIComponent(symbol)}`}>
                    {symbol}
                  </Link>
                  <p>{result.name}</p>
                  <span className="symbol-search-meta">
                    {formatAssetClass(result.assetClass)} · {result.exchange} · {result.currency} · {provider.toUpperCase()}
                    {providerSymbolId ? ` · ID ${providerSymbolId}` : ''}
                  </span>
                </div>
                <div className="symbol-search-actions">
                  <Link className="open-chart-link" href={`/symbols/${encodeURIComponent(symbol)}`}>
                    Open
                  </Link>
                  {onTogglePin ? (
                    <button
                      className={pinned ? 'pin-button pin-button--active' : 'pin-button'}
                      type="button"
                      aria-pressed={pinned}
                      disabled={actionsDisabled || isSaving}
                      onClick={() => onTogglePin(result)}
                    >
                      {isSaving ? (pinned ? 'Removing…' : 'Saving…') : pinned ? 'Pinned' : 'Pin result'}
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}

function createSearchResultPinKey(result: MarketDataSymbolSearchResult): string {
  const provider = result.provider || result.identity.provider;
  const providerSymbolId = result.providerSymbolId ?? result.identity.providerSymbolId;
  return createWatchlistInstrumentKey({
    symbol: getResultSymbol(result),
    provider,
    providerSymbolId,
    ibkrConid: parseIbkrConid(provider, providerSymbolId),
    exchange: result.exchange || result.identity.exchange,
    currency: result.currency || result.identity.currency,
    assetClass: normalizeWatchlistAssetClass(result.assetClass || result.identity.assetClass),
  });
}

function getResultSymbol(result: MarketDataSymbolSearchResult): string {
  return (result.symbol || result.identity.symbol).toUpperCase();
}

function parseIbkrConid(provider: string, providerSymbolId: string | null): number | null {
  if (provider.toLowerCase() !== 'ibkr' || !providerSymbolId || !/^\d+$/.test(providerSymbolId)) {
    return null;
  }

  return Number(providerSymbolId);
}

function formatAssetClass(assetClass: string): string {
  return assetClass.toUpperCase() === 'STK' ? 'Stock' : assetClass;
}
