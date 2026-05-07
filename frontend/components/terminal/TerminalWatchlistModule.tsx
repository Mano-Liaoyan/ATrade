'use client';

import { Bookmark, Search } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { createTerminalModuleRoute } from '@/lib/terminalRoutes';
import {
  type TerminalMarketMonitorRow,
  useTerminalMarketMonitorWorkflow,
} from '@/lib/terminalMarketMonitorWorkflow';
import type { TerminalNavigationIntent } from '@/types/terminal';
import { MarketMonitorDetailPanel } from './MarketMonitorDetailPanel';
import { MarketMonitorFilters } from './MarketMonitorFilters';
import { MarketMonitorTable } from './MarketMonitorTable';
import { MarketMonitorExplorationControls, MarketMonitorStateStrip } from './TerminalMarketMonitor';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

type TerminalWatchlistModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
};

export function TerminalWatchlistModule({ onOpenIntent }: TerminalWatchlistModuleProps) {
  const workflow = useTerminalMarketMonitorWorkflow({ initialSelectedFilters: { source: 'watchlist' } });
  const storedCount = workflow.watchlist.symbols.length;
  const savedRows = workflow.view.allRows.filter((row) => row.source === 'watchlist');

  function openSearch() {
    onOpenIntent(
      { moduleId: 'SEARCH', route: createTerminalModuleRoute('SEARCH') },
      'Opening Search to add exact provider instruments to the backend watchlist.',
    );
  }

  function openChart(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openChartIntent(row), buildWatchlistStatusMessage('CHART', row));
  }

  function openAnalysis(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openAnalysisIntent(row), buildWatchlistStatusMessage('ANALYSIS', row));
  }

  function openBacktest(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openBacktestIntent(row), buildWatchlistStatusMessage('BACKTEST', row));
  }

  return (
    <section className="terminal-module terminal-module--watchlist workspace-stack" data-testid="terminal-watchlist-module" id="terminal-watchlist" tabIndex={-1}>
      <TerminalPanel
        className="terminal-watchlist-module__hero"
        data-testid="terminal-watchlist-saved-first-workflow"
        eyebrow="Saved-stocks workflow"
        title="Backend watchlist pins"
        description="Watchlist starts with instruments saved through ATrade.Api workspace preferences, then keeps remove/manage, exact identity, chart, analysis, and backtest actions beside each pin."
        actions={<TerminalStatusBadge tone={workflow.watchlist.loading ? 'info' : workflow.watchlist.error ? 'warning' : 'success'} pulse={workflow.watchlist.loading}>{workflow.watchlist.loading ? 'Loading pins' : workflow.watchlist.error ? 'Fallback/error' : `${storedCount} saved`}</TerminalStatusBadge>}
      >
        <div className="terminal-watchlist-module__summary" data-watchlist-source={workflow.watchlist.source}>
          <div>
            <Bookmark aria-hidden="true" />
            <div>
              <strong>Backend stored pins first.</strong>
              <span>{workflow.providerState.watchlistCachedFallback ? 'Cached legacy pins are shown read-only until backend authority returns.' : 'Postgres-backed workspace preferences own pinKey and instrumentKey metadata.'}</span>
            </div>
          </div>
          <div className="terminal-watchlist-module__manage-actions">
            {workflow.watchlist.error ? <Button onClick={workflow.watchlist.retry} size="xs" type="button" variant="outline">Retry watchlist</Button> : null}
            <Button onClick={openSearch} size="xs" type="button" variant="amber">
              <Search aria-hidden="true" />
              Add stocks in Search
            </Button>
          </div>
        </div>
      </TerminalPanel>

      <MarketMonitorStateStrip compact={false} workflow={workflow} />

      {workflow.watchlist.error || (!workflow.watchlist.loading && storedCount === 0) ? (
        <TerminalPanel
          className="terminal-watchlist-module__empty-state"
          density="compact"
          eyebrow={workflow.watchlist.error ? 'Stored stocks unavailable' : 'Empty watchlist'}
          title={workflow.watchlist.error ? 'Backend pins cannot be loaded' : 'No saved stocks yet'}
          description={workflow.watchlist.error ?? 'Use bounded Search to pin exact provider-market instruments into the backend watchlist.'}
          actions={<Button onClick={openSearch} size="xs" type="button" variant="outline">Open Search</Button>}
          tone="inset"
        >
          <p>{workflow.watchlist.error ? 'Cached fallback rows remain explicitly labeled when available; no browser-only watchlist becomes authoritative.' : 'The table below remains filtered to saved stocks and will stay empty until ATrade.Api returns backend pins.'}</p>
        </TerminalPanel>
      ) : null}

      <TerminalPanel
        className="terminal-watchlist-module__pins"
        density="compact"
        eyebrow="Stored pins"
        title="Saved stocks table"
        description="Rows default to the Watchlist source filter so saved instruments lead; remove exact pins here or open chart, analysis, and backtest workflows with preserved identity metadata."
        actions={<TerminalStatusBadge tone="success">Source: Watchlist</TerminalStatusBadge>}
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
              row={workflow.view.selectedRow ?? savedRows[0] ?? null}
            />
          </div>
        </div>
      </TerminalPanel>
    </section>
  );
}

function buildWatchlistStatusMessage(moduleId: 'CHART' | 'ANALYSIS' | 'BACKTEST', row: TerminalMarketMonitorRow): string {
  const providerId = row.providerSymbolId ? ` provider id ${row.providerSymbolId}` : ' no provider id';
  const exchange = row.exchange ? ` on ${row.exchange}` : ' with market unavailable';
  return `Opening ${moduleId} for saved stock ${row.symbol} (${row.provider.toUpperCase()}${providerId}${exchange}, ${row.currency}, ${row.assetClass}).`;
}
