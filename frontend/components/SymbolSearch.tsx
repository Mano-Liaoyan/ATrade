'use client';

import Link from 'next/link';
import { createSymbolChartHref, getSearchResultIdentity } from '../lib/instrumentIdentity';
import { useSymbolSearchWorkflow } from '../lib/symbolSearchWorkflow';
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

export function SymbolSearch({
  title = 'Search IBKR stocks',
  description = 'Find stocks from the IBKR/iBeam instrument universe, open a chart, or pin the exact provider-market result to your watchlist.',
  limit = 10,
  getPinState,
  onTogglePin,
  compact = false,
}: SymbolSearchProps) {
  const search = useSymbolSearchWorkflow({ limit });
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
      {!search.loading && !search.error && search.searchedQuery && search.results.length === 0 ? (
        <div className="empty-state symbol-search-message">
          <strong>No IBKR stock results found.</strong>
          <p>Try a different symbol or company name. No local fallback catalog is used.</p>
        </div>
      ) : null}

      {search.results.length > 0 ? (
        <ul className="symbol-search-results" aria-label="IBKR stock search results">
          {search.results.map((result) => {
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
              <li className="terminal-result-row" key={pinState?.pinKey ?? chartHref} aria-label={accessibleLabel}>
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
