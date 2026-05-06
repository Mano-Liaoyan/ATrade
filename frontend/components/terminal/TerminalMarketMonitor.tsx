'use client';

import * as React from 'react';
import { RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  type TerminalMarketMonitorRow,
  type TerminalMarketMonitorWorkflow,
  useTerminalMarketMonitorWorkflow,
} from '@/lib/terminalMarketMonitorWorkflow';
import type { TerminalNavigationIntent } from '@/types/terminal';
import { MarketMonitorDetailPanel } from './MarketMonitorDetailPanel';
import { MarketMonitorFilters } from './MarketMonitorFilters';
import { MarketMonitorSearch } from './MarketMonitorSearch';
import { MarketMonitorTable } from './MarketMonitorTable';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type TerminalMarketMonitorProps = {
  className?: string;
  compact?: boolean;
  initialSearchQuery?: string;
  onOpenIntent?: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  title?: string;
};

export function TerminalMarketMonitor({
  className,
  compact = false,
  initialSearchQuery = '',
  onOpenIntent,
  title = 'Market monitor',
}: TerminalMarketMonitorProps) {
  const workflow = useTerminalMarketMonitorWorkflow({ initialSearchQuery });
  const handleOpenChart = React.useMemo(
    () => onOpenIntent
      ? (row: TerminalMarketMonitorRow) => onOpenIntent(workflow.openChartIntent(row), buildOpenStatusMessage('CHART', row))
      : undefined,
    [onOpenIntent, workflow],
  );
  const handleOpenAnalysis = React.useMemo(
    () => onOpenIntent
      ? (row: TerminalMarketMonitorRow) => onOpenIntent(workflow.openAnalysisIntent(row), buildOpenStatusMessage('ANALYSIS', row))
      : undefined,
    [onOpenIntent, workflow],
  );
  const handleOpenBacktest = React.useMemo(
    () => onOpenIntent
      ? (row: TerminalMarketMonitorRow) => onOpenIntent(workflow.openBacktestIntent(row), buildOpenStatusMessage('BACKTEST', row))
      : undefined,
    [onOpenIntent, workflow],
  );

  return (
    <section className={cn('terminal-market-monitor', compact && 'terminal-market-monitor--compact', className)} data-testid="terminal-market-monitor" aria-label="Market monitor">
      <TerminalPanel
        className="terminal-market-monitor__shell"
        density="compact"
        eyebrow="Market monitor"
        title={title}
        description="Dense watchlist, bounded search, and provider-backed trending rows with exact provider-market identity visible for every action."
        actions={(
          <div className="terminal-market-monitor__header-actions">
            <TerminalStatusBadge tone={workflow.trendingLoading || workflow.search.loading || workflow.watchlist.loading ? 'info' : workflow.providerState.trendingError || workflow.providerState.searchError || workflow.providerState.watchlistError ? 'warning' : 'success'} pulse={workflow.trendingLoading || workflow.search.loading || workflow.watchlist.loading}>
              {workflow.statusSummary}
            </TerminalStatusBadge>
            <Button onClick={workflow.reloadTrending} size="xs" type="button" variant="outline">
              <RefreshCw aria-hidden="true" />
              Reload trending
            </Button>
          </div>
        )}
      >
        <div className="terminal-market-monitor__body">
          <MarketMonitorSearch
            compact={compact}
            error={workflow.search.error}
            loading={workflow.search.loading}
            onQueryChange={workflow.search.setQuery}
            query={workflow.search.query}
            resultCount={workflow.search.searchView.filteredResultCount}
            searchedQuery={workflow.search.searchedQuery}
            validationMessage={workflow.search.validationMessage}
          />

          <MarketMonitorStateStrip compact={compact} workflow={workflow} />

          <MarketMonitorFilters
            availableFilters={workflow.view.availableFilters}
            compact={compact}
            onClearFilter={workflow.clearFilter}
            onClearFilters={workflow.clearFilters}
            onFilterChange={workflow.setFilter}
            selectedFilters={workflow.view.selectedFilters}
          />

          <div className="terminal-market-monitor__grid">
            <div className="terminal-market-monitor__table-region">
              <MarketMonitorTable
                compact={compact}
                onOpenAnalysis={handleOpenAnalysis}
                onOpenBacktest={handleOpenBacktest}
                onOpenChart={handleOpenChart}
                onSelectRow={workflow.selectRow}
                onSort={workflow.setSort}
                onTogglePin={(row) => void workflow.toggleRowPin(row)}
                rows={workflow.view.visibleRows}
                selectedRowId={workflow.view.selectedRowId}
                sort={workflow.sort}
              />
              <MarketMonitorExplorationControls workflow={workflow} />
            </div>

            <MarketMonitorDetailPanel
              compact={compact}
              onOpenAnalysis={handleOpenAnalysis}
              onOpenBacktest={handleOpenBacktest}
              onOpenChart={handleOpenChart}
              onTogglePin={(row) => void workflow.toggleRowPin(row)}
              row={workflow.view.selectedRow}
            />
          </div>
        </div>
      </TerminalPanel>
    </section>
  );
}

function MarketMonitorStateStrip({ compact, workflow }: { compact: boolean; workflow: TerminalMarketMonitorWorkflow }) {
  const states = [
    {
      label: 'Trending',
      badge: workflow.trendingLoading ? 'Loading' : workflow.trendingError ? 'Unavailable' : `${workflow.trendingSymbols.length} rows`,
      tone: workflow.trendingLoading ? 'info' : workflow.trendingError ? 'danger' : 'success',
      detail: workflow.trendingError ?? (workflow.trendingSource ? `${workflow.trendingSource}${workflow.trendingGeneratedAt ? ` · ${workflow.trendingGeneratedAt}` : ''}` : 'Provider scanner source pending'),
    },
    {
      label: 'Search',
      badge: workflow.search.loading ? 'Loading' : workflow.search.error ? 'Unavailable' : workflow.search.validationMessage ? 'Needs query' : `${workflow.search.searchView.filteredResultCount} ranked`,
      tone: workflow.search.loading ? 'info' : workflow.search.error ? 'danger' : workflow.search.validationMessage ? 'warning' : 'success',
      detail: workflow.search.error ?? workflow.search.validationMessage ?? 'Debounced, minimum-query, capped stock search through ATrade.Api.',
    },
    {
      label: 'Watchlist',
      badge: workflow.watchlist.loading ? 'Loading' : workflow.watchlist.error ? 'Fallback/error' : `${workflow.watchlist.symbols.length} pins`,
      tone: workflow.watchlist.loading ? 'info' : workflow.watchlist.error ? 'warning' : 'success',
      detail: workflow.watchlist.error ?? (workflow.providerState.watchlistCachedFallback ? 'Cached legacy pins are read-only until backend returns.' : 'Backend-owned exact Postgres pins through ATrade.Api.'),
    },
  ] as const;

  return (
    <div className={cn('market-monitor-state-strip', compact && 'market-monitor-state-strip--compact')} data-testid="market-monitor-state-strip">
      {states.map((state) => (
        <div className="market-monitor-state-strip__item" key={state.label} role={state.tone === 'danger' ? 'alert' : 'status'}>
          <div>
            <span>{state.label}</span>
            <TerminalStatusBadge tone={state.tone} pulse={state.badge === 'Loading'}>{state.badge}</TerminalStatusBadge>
          </div>
          <p>{state.detail}</p>
        </div>
      ))}
    </div>
  );
}

function MarketMonitorExplorationControls({ workflow }: { workflow: TerminalMarketMonitorWorkflow }) {
  return (
    <div className="market-monitor-exploration" data-testid="market-monitor-exploration-controls">
      <div>
        <strong>{workflow.view.visibleRows.length}</strong>
        <span>visible of {workflow.view.filteredRowCount} filtered · {workflow.view.totalRowCount} total rows</span>
      </div>
      <div className="market-monitor-exploration__actions">
        <Button disabled={!workflow.view.canShowLess} onClick={workflow.showLessRows} size="xs" type="button" variant="ghost">
          Show less
        </Button>
        <Button disabled={!workflow.view.canShowMore} onClick={workflow.showMoreRows} size="xs" type="button" variant="outline">
          Show more rows
        </Button>
      </div>
    </div>
  );
}

function buildOpenStatusMessage(moduleId: 'CHART' | 'ANALYSIS' | 'BACKTEST', row: TerminalMarketMonitorRow): string {
  const providerId = row.providerSymbolId ? ` provider id ${row.providerSymbolId}` : ' no provider id';
  const exchange = row.exchange ? ` on ${row.exchange}` : ' with market unavailable';
  return `Opening ${moduleId} for ${row.symbol} (${row.provider.toUpperCase()}${providerId}${exchange}, ${row.currency}, ${row.assetClass}).`;
}
