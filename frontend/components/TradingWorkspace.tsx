'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getTrendingSymbols } from '../lib/marketDataClient';
import { useWatchlistWorkflow } from '../lib/watchlistWorkflow';
import type { TrendingSymbol } from '../types/marketData';
import { SymbolSearch } from './SymbolSearch';
import { TerminalWorkspaceShell } from './TerminalWorkspaceShell';
import { TrendingList } from './TrendingList';
import { Watchlist } from './Watchlist';

export function TradingWorkspace() {
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [marketDataLoading, setMarketDataLoading] = useState(true);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [marketDataSource, setMarketDataSource] = useState<string | null>(null);
  const watchlist = useWatchlistWorkflow();

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

  useEffect(() => {
    void loadTrendingSymbols();
  }, [loadTrendingSymbols]);

  const sortedTrendingSymbols = useMemo(
    () => [...trendingSymbols].sort((left, right) => right.score - left.score),
    [trendingSymbols],
  );

  const marketDataStatus = marketDataLoading
    ? 'Loading IBKR/iBeam'
    : marketDataError
      ? 'Provider unavailable'
      : `${sortedTrendingSymbols.length} provider symbols`;
  const watchlistStatus = watchlist.loading
    ? 'Loading pins'
    : watchlist.error
      ? 'Backend unavailable'
      : `${watchlist.symbols.length} saved pins`;

  return (
    <section className="workspace-stack" data-testid="trading-workspace">
      <TerminalWorkspaceShell
        workspaceId="home-workspace"
        eyebrow="Next.js Bootstrap Slice"
        title="ATrade Frontend Home"
        subtitle="Aspire AppHost Frontend Contract"
        description="Trading workspace MVP for trending stocks and ETFs, backend-saved watchlists, symbol navigation, and the interactive paper-trading chart view."
        navigationLabel="Trading workspace navigation"
        navigationItems={[
          {
            id: 'workspace-search',
            label: 'Search',
            href: '#workspace-search',
            description: 'IBKR stock lookup and exact identity handoff',
            badge: '⌘1',
          },
          {
            id: 'workspace-trending',
            label: 'Trending',
            href: '#workspace-trending',
            description: 'Provider-backed scanner factors',
            badge: '⌘2',
          },
          {
            id: 'workspace-watchlist',
            label: 'Watchlist',
            href: '#workspace-watchlist',
            description: 'Postgres-backed saved pins',
            badge: '⌘3',
          },
          {
            id: 'workspace-provider',
            label: 'Provider context',
            href: '#workspace-provider',
            description: 'Paper-only provider state and safety notes',
            badge: 'safe',
          },
        ]}
        commandItems={[
          { label: 'Open search', href: '#workspace-search' },
          { label: 'Trending board', href: '#workspace-trending' },
          { label: 'Saved pins', href: '#workspace-watchlist' },
        ]}
        statusItems={[
          { label: 'Mode', value: 'Paper only', tone: 'positive' },
          { label: 'Market data', value: marketDataStatus, tone: marketDataError ? 'warning' : 'default' },
          { label: 'Watchlist', value: watchlistStatus, tone: watchlist.error ? 'warning' : 'default' },
        ]}
        context={{
          eyebrow: 'Workspace context',
          title: 'Provider and safety map',
          description: 'Paper-only workspace consuming IBKR/iBeam market data and Postgres-backed workspace watchlists through ATrade.Api.',
          metrics: [
            { label: 'Market source', value: formatMarketDataSource(marketDataSource), tone: marketDataError ? 'warning' : 'default' },
            { label: 'Watchlist source', value: watchlist.source === 'backend' ? 'Postgres' : 'Cached snapshot' },
            { label: 'Identity model', value: 'Exact provider-market pins', tone: 'positive' },
          ],
          cards: [
            {
              label: 'Paper guardrail',
              title: 'No live broker actions',
              description: 'This terminal-style shell exposes search, watchlist, charts, and analysis entry points only; it does not add order placement controls.',
              tone: 'warning',
            },
            {
              label: 'Provider truth',
              title: 'No synthetic fallback data',
              description: 'Unavailable IBKR/iBeam market data remains visible as provider-state copy instead of being replaced by fake market data.',
            },
          ],
          children: (
            <div className="terminal-context-panel__section" id="workspace-watchlist">
              <Watchlist
                symbols={watchlist.symbols}
                trendingSymbols={sortedTrendingSymbols}
                loading={watchlist.loading}
                error={watchlist.error}
                source={watchlist.source}
                getPinState={watchlist.getWatchlistSymbolPinState}
                onRetry={watchlist.retry}
                onRemove={(symbol) => void watchlist.removePin(symbol)}
              />
            </div>
          ),
        }}
      >
        <div id="workspace-search" className="terminal-panel-anchor">
          <SymbolSearch
            getPinState={watchlist.getSearchResultPinState}
            onTogglePin={(result) => void watchlist.toggleSearchPin(result)}
          />
        </div>

        <section id="workspace-trending" className="terminal-panel-anchor workspace-stack" aria-label="Trending provider-backed symbols">
          {marketDataLoading ? (
            <div className="workspace-panel loading-state" role="status">
              Loading IBKR/iBeam trending stocks and ETFs…
            </div>
          ) : null}

          {!marketDataLoading && marketDataError ? (
            <div className="workspace-panel error-state" role="alert">
              <strong>IBKR market data unavailable.</strong>
              <p>{marketDataError}</p>
              <button className="primary-button" type="button" onClick={() => void loadTrendingSymbols()}>
                Retry IBKR market data
              </button>
            </div>
          ) : null}

          {!marketDataLoading && !marketDataError && sortedTrendingSymbols.length === 0 ? (
            <div className="workspace-panel empty-state">
              <strong>No trending symbols returned.</strong>
              <p>The IBKR/iBeam provider responded, but no stocks or ETFs were available for the workspace.</p>
            </div>
          ) : null}

          {!marketDataLoading && !marketDataError && sortedTrendingSymbols.length > 0 ? (
            <TrendingList
              symbols={sortedTrendingSymbols}
              getPinState={watchlist.getTrendingPinState}
              source={marketDataSource}
              onTogglePin={(symbol) => void watchlist.toggleTrendingPin(symbol)}
            />
          ) : null}
        </section>

        <div id="workspace-provider" className="workspace-status-row terminal-provider-status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          <span>Paper-only provider context: IBKR/iBeam market data and backend watchlists stay behind ATrade.Api.</span>
        </div>
      </TerminalWorkspaceShell>
    </section>
  );
}

function formatMarketDataSource(source: string | null): string {
  if (!source) {
    return 'IBKR/iBeam';
  }

  if (source.includes('scanner')) {
    return 'IBKR scanner';
  }

  return source.includes('ibkr') ? 'IBKR/iBeam' : source;
}
