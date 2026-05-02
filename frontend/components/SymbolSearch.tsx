'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { searchSymbols } from '../lib/marketDataClient';
import { createSymbolChartHref, getSearchResultIdentity } from '../lib/instrumentIdentity';
import type { WatchlistPinState } from '../lib/watchlistWorkflow';
import type { MarketDataSymbolSearchResult } from '../types/marketData';
import { MarketLogo } from './MarketLogo';

type SymbolSearchProps = {
  title?: string;
  description?: string;
  limit?: number;
  getPinState?: (result: MarketDataSymbolSearchResult) => WatchlistPinState;
  onTogglePin?: (result: MarketDataSymbolSearchResult) => void;
  compact?: boolean;
};

const MinimumQueryLength = 2;

export function SymbolSearch({
  title = 'Search IBKR stocks',
  description = 'Find stocks from the IBKR/iBeam instrument universe, open a chart, or pin the exact provider-market result to your watchlist.',
  limit = 10,
  getPinState,
  onTogglePin,
  compact = false,
}: SymbolSearchProps) {
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
            const identity = getSearchResultIdentity(result);
            const symbol = identity.symbol;
            const provider = identity.provider;
            const providerSymbolId = identity.providerSymbolId;
            const exchange = identity.exchange ?? '';
            const currency = identity.currency;
            const assetClass = identity.assetClass;
            const chartHref = createSymbolChartHref(identity);
            const pinState = getPinState?.(result);
            const providerIdLabel = formatProviderId(provider, providerSymbolId);
            const accessibleLabel = `${symbol} ${result.name} on ${exchange}, ${currency}, ${formatAssetClass(assetClass)}, ${provider.toUpperCase()}${providerIdLabel ? `, ${providerIdLabel}` : ''}`;

            return (
              <li key={pinState?.pinKey ?? chartHref} aria-label={accessibleLabel}>
                <div>
                  <Link className="symbol-link" href={chartHref}>
                    {symbol}
                  </Link>
                  <p>{result.name}</p>
                  <div className="instrument-identity-row">
                    <MarketLogo exchange={exchange} provider={provider} compact />
                    <span className="symbol-search-meta">
                      Provider {provider.toUpperCase()} · Market {exchange} · {currency} · {formatAssetClass(assetClass)}
                      {providerIdLabel ? ` · ${providerIdLabel}` : ''}
                    </span>
                  </div>
                </div>
                <div className="symbol-search-actions">
                  <Link className="open-chart-link" href={chartHref}>
                    Open
                  </Link>
                  {onTogglePin && pinState ? (
                    <button
                      className={pinState.pinned ? 'pin-button pin-button--active' : 'pin-button'}
                      type="button"
                      aria-pressed={pinState.pinned}
                      disabled={pinState.disabled}
                      onClick={() => onTogglePin(result)}
                    >
                      {pinState.saving ? (pinState.pinned ? 'Removing…' : 'Saving…') : pinState.pinned ? 'Pinned' : 'Pin result'}
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

function formatProviderId(provider: string, providerSymbolId: string | null): string {
  if (!providerSymbolId) {
    return '';
  }

  return provider.toLowerCase() === 'ibkr' ? `IBKR conid ${providerSymbolId}` : `${provider.toUpperCase()} ID ${providerSymbolId}`;
}

function formatAssetClass(assetClass: string): string {
  return assetClass.toUpperCase() === 'STK' ? 'Stock' : assetClass;
}
