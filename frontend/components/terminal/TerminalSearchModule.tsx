'use client';

import { Search } from 'lucide-react';

import {
  type TerminalMarketMonitorRow,
  useTerminalMarketMonitorWorkflow,
} from '@/lib/terminalMarketMonitorWorkflow';
import type { TerminalNavigationIntent } from '@/types/terminal';
import { MarketMonitorDetailPanel } from './MarketMonitorDetailPanel';
import { MarketMonitorFilters } from './MarketMonitorFilters';
import { MarketMonitorSearch } from './MarketMonitorSearch';
import { MarketMonitorTable } from './MarketMonitorTable';
import { MarketMonitorExplorationControls, MarketMonitorStateStrip } from './TerminalMarketMonitor';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

type TerminalSearchModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery?: string;
};

export function TerminalSearchModule({ onOpenIntent, searchQuery = '' }: TerminalSearchModuleProps) {
  const workflow = useTerminalMarketMonitorWorkflow({
    initialSearchQuery: searchQuery,
    initialSelectedFilters: { source: 'search' },
  });

  function openChart(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openChartIntent(row), buildSearchStatusMessage('CHART', row));
  }

  function openAnalysis(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openAnalysisIntent(row), buildSearchStatusMessage('ANALYSIS', row));
  }

  function openBacktest(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openBacktestIntent(row), buildSearchStatusMessage('BACKTEST', row));
  }

  const rankedCount = workflow.search.searchView.filteredResultCount;

  return (
    <section className="terminal-module terminal-module--search workspace-stack" data-testid="terminal-search-module" id="terminal-search" tabIndex={-1}>
      <TerminalPanel
        className="terminal-search-module__hero"
        eyebrow="Search-first workflow"
        title="Bounded stock search"
        description="Search puts the API-backed stock query first, then shows ranked results with exact provider identity and chart, pin, analysis, and backtest actions."
        actions={<TerminalStatusBadge tone={workflow.search.loading ? 'info' : workflow.search.error ? 'danger' : rankedCount > 0 ? 'success' : 'warning'} pulse={workflow.search.loading}>{workflow.search.loading ? 'Searching' : workflow.search.error ? 'Unavailable' : `${rankedCount} ranked`}</TerminalStatusBadge>}
      >
        <div className="terminal-search-module__intro" data-testid="terminal-search-primary-workflow">
          <div className="terminal-search-module__copy">
            <Search aria-hidden="true" />
            <div>
              <strong>Start with a stock or company query.</strong>
              <span>Results are bounded to the configured API limit, ranked locally, and never backed by a hard-coded browser catalog.</span>
            </div>
          </div>
          <MarketMonitorSearch
            autoFocus
            className="terminal-search-module__primary-search"
            error={workflow.search.error}
            loading={workflow.search.loading}
            onQueryChange={workflow.search.setQuery}
            query={workflow.search.query}
            resultCount={rankedCount}
            searchedQuery={workflow.search.searchedQuery}
            validationMessage={workflow.search.validationMessage}
          />
        </div>
      </TerminalPanel>

      <MarketMonitorStateStrip compact={false} workflow={workflow} />

      <TerminalPanel
        className="terminal-search-module__results"
        density="compact"
        eyebrow="Ranked results"
        title="Search result filters and actions"
        description="The default source filter keeps the table search-first; clear it only when you need saved or trending context in the same reusable monitor primitives."
        actions={<TerminalStatusBadge tone="info">Source: Search</TerminalStatusBadge>}
        tone="inset"
      >
        <div className="terminal-market-monitor__body">
          <MarketMonitorFilters
            availableFilters={workflow.view.availableFilters}
            compact={false}
            onClearFilter={workflow.clearFilter}
            onClearFilters={workflow.clearFilters}
            onFilterChange={workflow.setFilter}
            selectedFilters={workflow.view.selectedFilters}
          />

          <div className="terminal-market-monitor__grid">
            <div className="terminal-market-monitor__table-region">
              <MarketMonitorTable
                compact={false}
                onOpenAnalysis={openAnalysis}
                onOpenBacktest={openBacktest}
                onOpenChart={openChart}
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
              compact={false}
              onOpenAnalysis={openAnalysis}
              onOpenBacktest={openBacktest}
              onOpenChart={openChart}
              onTogglePin={(row) => void workflow.toggleRowPin(row)}
              row={workflow.view.selectedRow}
            />
          </div>
        </div>
      </TerminalPanel>
    </section>
  );
}

function buildSearchStatusMessage(moduleId: 'CHART' | 'ANALYSIS' | 'BACKTEST', row: TerminalMarketMonitorRow): string {
  const providerId = row.providerSymbolId ? ` provider id ${row.providerSymbolId}` : ' no provider id';
  const exchange = row.exchange ? ` on ${row.exchange}` : ' with market unavailable';
  return `Opening ${moduleId} for ranked search result ${row.symbol} (${row.provider.toUpperCase()}${providerId}${exchange}, ${row.currency}, ${row.assetClass}).`;
}
