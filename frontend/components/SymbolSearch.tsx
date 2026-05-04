'use client';

import Link from 'next/link';
import { createSymbolChartHref, getSearchResultIdentity } from '../lib/instrumentIdentity';
import { DefaultSymbolSearchRequestLimit, SymbolSearchFilterLabels, useSymbolSearchWorkflow, type SymbolSearchFilterKey } from '../lib/symbolSearchWorkflow';
import type { WatchlistPinState } from '../lib/watchlistWorkflow';
import type { MarketDataSymbolSearchResult } from '../types/marketData';
import { MarketLogo } from './MarketLogo';

const VisibleSymbolSearchFilterKeys: SymbolSearchFilterKey[] = ['exchange', 'currency', 'assetClass'];

type SymbolSearchProps = {
  title?: string;
  description?: string;
  limit?: number;
  initialQuery?: string;
  getPinState?: (result: MarketDataSymbolSearchResult) => WatchlistPinState;
  onTogglePin?: (result: MarketDataSymbolSearchResult) => void;
  compact?: boolean;
};

export function SymbolSearch({
  title = 'Search IBKR stocks',
  description = 'Find stocks from the IBKR/iBeam instrument universe, open a chart, or pin the exact provider-market result to your watchlist.',
  limit = DefaultSymbolSearchRequestLimit,
  initialQuery = '',
  getPinState,
  onTogglePin,
  compact = false,
}: SymbolSearchProps) {
  const search = useSymbolSearchWorkflow({ initialQuery, limit });
  const searchView = search.searchView;
  const visibleResults = searchView.visibleResults;
  const hasResults = searchView.totalResultCount > 0;
  const hasSelectedFilters = Object.keys(searchView.selectedFilters).length > 0;
  const resultListId = compact ? 'symbol-search-compact-results' : 'symbol-search-results';
  const panelClassName = compact
    ? 'workspace-panel terminal-data-panel symbol-search-panel symbol-search-panel--compact'
    : 'workspace-panel terminal-data-panel symbol-search-panel';

  return (
    <section className={panelClassName} data-testid="symbol-search">
      <div className="panel-heading terminal-panel-heading">
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
        value={search.query}
        autoComplete="off"
        placeholder="Type at least two characters"
        onChange={(event) => search.setQuery(event.target.value)}
      />

      {search.validationMessage ? <p className="symbol-search-help">{search.validationMessage}</p> : null}
      {search.loading ? <p className="symbol-search-help" role="status">Searching IBKR/iBeam contracts…</p> : null}
      {search.error ? (
        <div className="error-state symbol-search-message" role="alert">
          <strong>IBKR stock search unavailable.</strong>
          <p>{search.error}</p>
        </div>
      ) : null}
      {!search.loading && !search.error && search.searchedQuery && searchView.totalResultCount === 0 ? (
        <div className="empty-state symbol-search-message">
          <strong>No IBKR stock results found.</strong>
          <p>Try a different symbol or company name. No local fallback catalog is used.</p>
        </div>
      ) : null}

      {hasResults ? (
        <div className="symbol-search-summary" aria-live="polite">
          <div className="symbol-search-result-count">
            <span className="pill">Ranked results</span>
            <strong>{formatResultCount(searchView.filteredResultCount, searchView.totalResultCount)}</strong>
          </div>
          {searchView.bestMatch ? (
            <BestMatchSummary result={searchView.bestMatch} />
          ) : null}
        </div>
      ) : null}

      {hasResults ? (
        <div className="symbol-search-filters" aria-label="Narrow IBKR search results by market metadata">
          <div className="symbol-search-filter-heading">
            <span>Refine by market metadata</span>
            {hasSelectedFilters ? (
              <button className="symbol-search-filter-clear" type="button" onClick={search.clearFilters}>
                Clear filters
              </button>
            ) : null}
          </div>
          {VisibleSymbolSearchFilterKeys.map((filterKey) => {
            const options = searchView.availableFilters[filterKey];
            if (options.length <= 1) {
              return null;
            }

            return (
              <div className="symbol-search-filter-group" key={filterKey}>
                <span>{SymbolSearchFilterLabels[filterKey]}</span>
                <div className="symbol-search-filter-options">
                  {options.map((option) => {
                    const active = searchView.selectedFilters[filterKey] === option.value;

                    return (
                      <button
                        className={active ? 'symbol-search-filter-chip symbol-search-filter-chip--active' : 'symbol-search-filter-chip'}
                        type="button"
                        aria-pressed={active}
                        key={option.value}
                        onClick={() => (active ? search.clearFilter(filterKey) : search.setFilter(filterKey, option.value))}
                      >
                        {option.label}
                        <span>{option.count}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {hasResults && visibleResults.length === 0 ? (
        <div className="empty-state symbol-search-message">
          <strong>No results match the selected metadata filters.</strong>
          <p>Clear filters or choose another market, currency, or asset chip to restore the ranked IBKR result list.</p>
        </div>
      ) : null}

      {visibleResults.length > 0 ? (
        <ul id={resultListId} className="symbol-search-results" aria-label="Ranked IBKR stock search results">
          {visibleResults.map((result) => {
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
            const isBestMatch = result === searchView.bestMatch;

            return (
              <li className={isBestMatch ? 'terminal-result-row terminal-result-row--best' : 'terminal-result-row'} key={pinState?.pinKey ?? chartHref} aria-label={accessibleLabel}>
                <div>
                  <div className="symbol-search-result-title">
                    <Link className="symbol-link" href={chartHref}>
                      {symbol}
                    </Link>
                    {isBestMatch ? <span className="symbol-search-best-badge">Best match</span> : null}
                  </div>
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

      {hasResults && (searchView.canShowMore || searchView.canShowLess) ? (
        <div className="symbol-search-explore-controls">
          <span>
            Showing {visibleResults.length} of {searchView.filteredResultCount} ranked match{searchView.filteredResultCount === 1 ? '' : 'es'}.
          </span>
          <div>
            {searchView.canShowMore ? (
              <button className="symbol-search-explore-button" type="button" aria-controls={resultListId} onClick={search.showMoreResults}>
                Show more results
              </button>
            ) : null}
            {searchView.canShowLess ? (
              <button className="symbol-search-explore-button" type="button" aria-controls={resultListId} onClick={search.showLessResults}>
                Show less
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function BestMatchSummary({ result }: { result: MarketDataSymbolSearchResult }) {
  const identity = getSearchResultIdentity(result);
  const providerIdLabel = formatProviderId(identity.provider, identity.providerSymbolId);

  return (
    <div className="symbol-search-best-match">
      <span>Best match</span>
      <strong>{identity.symbol}</strong>
      <small>
        {result.name} · Market {identity.exchange ?? 'Unknown'} · {identity.currency} · {formatAssetClass(identity.assetClass)}
        {providerIdLabel ? ` · ${providerIdLabel}` : ''}
      </small>
    </div>
  );
}

function formatResultCount(filteredResultCount: number, totalResultCount: number): string {
  if (filteredResultCount === totalResultCount) {
    return `${totalResultCount} result${totalResultCount === 1 ? '' : 's'} returned`;
  }

  return `${filteredResultCount} of ${totalResultCount} results shown by filters`;
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
