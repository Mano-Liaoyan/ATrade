'use client';

import type { ComponentType } from 'react';
import { Activity, BarChart3, Bookmark, FlaskConical, LineChart, Search, ServerPulse } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { createTerminalModuleRoute } from '@/lib/terminalRoutes';
import {
  type TerminalMarketMonitorRow,
  type TerminalMarketMonitorWorkflow,
  useTerminalMarketMonitorWorkflow,
} from '@/lib/terminalMarketMonitorWorkflow';
import type { EnabledTerminalModuleId, TerminalNavigationIntent } from '@/types/terminal';
import { TerminalPanel } from './TerminalPanel';
import { TerminalProviderDiagnostics } from './TerminalProviderDiagnostics';
import { TerminalStatusBadge, type TerminalStatusTone } from './TerminalStatusBadge';

type TerminalHomeModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery?: string;
};

type HomeQuickAction = {
  moduleId: EnabledTerminalModuleId;
  label: string;
  description: string;
  icon: ComponentType<{ 'aria-hidden'?: boolean }>;
  tone: TerminalStatusTone;
};

const HomeQuickActions: HomeQuickAction[] = [
  { moduleId: 'SEARCH', label: '/search', description: 'Find stocks with bounded API-backed search.', icon: Search, tone: 'info' },
  { moduleId: 'WATCHLIST', label: '/watchlist', description: 'Manage backend-stored exact pins.', icon: Bookmark, tone: 'success' },
  { moduleId: 'CHART', label: '/chart', description: 'Open stored stocks or exact chart routes.', icon: BarChart3, tone: 'info' },
  { moduleId: 'ANALYSIS', label: '/analysis', description: 'Run provider-neutral analysis only.', icon: FlaskConical, tone: 'neutral' },
  { moduleId: 'BACKTEST', label: '/backtest', description: 'Create paper-capital saved runs.', icon: Activity, tone: 'warning' },
  { moduleId: 'STATUS', label: '/status', description: 'Inspect API and provider readiness.', icon: ServerPulse, tone: 'neutral' },
];

export function TerminalHomeModule({ onOpenIntent, searchQuery = '' }: TerminalHomeModuleProps) {
  const workflow = useTerminalMarketMonitorWorkflow({ initialSearchQuery: searchQuery });
  const trendingRows = workflow.view.allRows.filter((row) => row.source === 'trending').slice(0, 4);
  const watchlistRows = workflow.view.allRows.filter((row) => row.source === 'watchlist').slice(0, 4);

  function openModule(moduleId: EnabledTerminalModuleId, label: string) {
    onOpenIntent(
      { moduleId, route: createTerminalModuleRoute(moduleId) },
      `Opening ${label} from the Home dashboard.`,
    );
  }

  function openChart(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openChartIntent(row), buildHomeRowStatusMessage('CHART', row));
  }

  function openAnalysis(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openAnalysisIntent(row), buildHomeRowStatusMessage('ANALYSIS', row));
  }

  function openBacktest(row: TerminalMarketMonitorRow) {
    onOpenIntent(workflow.openBacktestIntent(row), buildHomeRowStatusMessage('BACKTEST', row));
  }

  return (
    <section className="terminal-module terminal-module--home workspace-stack" data-testid="terminal-home-module" id="terminal-module-home" tabIndex={-1}>
      <TerminalPanel
        className="terminal-home-dashboard__hero"
        eyebrow="Home dashboard"
        title="Paper trading command overview"
        description="Home summarizes provider/API reachability, paper-only safety, workflow shortcuts, and compact market context without duplicating the full search or watchlist workspaces."
        actions={<TerminalStatusBadge tone="success">Paper only · no orders</TerminalStatusBadge>}
      >
        <div className="terminal-home-status-grid" data-testid="terminal-home-status-grid">
          <HomeStatusTile label="ATrade.Api boundary" badge="API only" tone="success" detail="Browser data stays behind committed ATrade.Api clients; Home does not call providers, databases, or broker runtimes directly." />
          <HomeStatusTile label="Provider scanner" badge={workflow.trendingLoading ? 'Checking' : workflow.trendingError ? 'Unavailable' : `${workflow.trendingSymbols.length} rows`} tone={workflow.trendingLoading ? 'info' : workflow.trendingError ? 'warning' : 'success'} detail={workflow.trendingError ?? (workflow.trendingSource ? `${workflow.trendingSource}${workflow.trendingGeneratedAt ? ` · ${workflow.trendingGeneratedAt}` : ''}` : 'Provider trending source pending.')} />
          <HomeStatusTile label="Stored stocks" badge={workflow.watchlist.loading ? 'Loading' : workflow.watchlist.error ? 'Fallback/error' : `${workflow.watchlist.symbols.length} pins`} tone={workflow.watchlist.loading ? 'info' : workflow.watchlist.error ? 'warning' : 'success'} detail={workflow.watchlist.error ?? (workflow.providerState.watchlistCachedFallback ? 'Cached legacy pins are read-only until backend preferences load.' : 'Backend-owned exact Postgres pins through ATrade.Api.')} />
          <HomeStatusTile label="Paper safety" badge="No order entry" tone="success" detail="Orders, buy/sell tickets, broker execution, and live-trading controls are not rendered in this workspace." />
        </div>
      </TerminalPanel>

      <TerminalPanel
        className="terminal-home-dashboard__actions"
        density="compact"
        eyebrow="Quick actions"
        title="Continue a paper workflow"
        description="Each shortcut opens a canonical route; symbol-specific chart, analysis, and backtest routes still require exact row identity from Search or Watchlist."
      >
        <div className="terminal-home-quick-actions" data-testid="terminal-home-quick-actions">
          {HomeQuickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Button className="terminal-home-quick-actions__item" key={action.moduleId} onClick={() => openModule(action.moduleId, action.label)} size="sm" type="button" variant={action.moduleId === 'SEARCH' ? 'amber' : 'terminal'}>
                <Icon aria-hidden="true" />
                <span className="terminal-home-quick-actions__copy">
                  <strong>{action.label}</strong>
                  <small>{action.description}</small>
                </span>
                <TerminalStatusBadge tone={action.tone}>{action.moduleId}</TerminalStatusBadge>
              </Button>
            );
          })}
        </div>
      </TerminalPanel>

      <div className="terminal-home-preview-grid" data-testid="terminal-home-preview-grid">
        <HomePreviewPanel
          actionLabel="Open Search"
          emptyDetail={workflow.trendingError ?? (workflow.trendingLoading ? 'Provider scanner is still loading.' : 'No provider trending rows are available; Home does not substitute demo symbols.')}
          emptyTitle={workflow.trendingLoading ? 'Loading provider trending…' : workflow.trendingError ? 'Trending unavailable.' : 'No trending rows returned.'}
          eyebrow="Market context"
          onAction={() => openModule('SEARCH', '/search')}
          onOpenAnalysis={openAnalysis}
          onOpenBacktest={openBacktest}
          onOpenChart={openChart}
          rows={trendingRows}
          title="Provider trending preview"
        />
        <HomePreviewPanel
          actionLabel={workflow.watchlist.symbols.length > 0 ? 'Open Watchlist' : 'Add from Search'}
          emptyDetail={workflow.watchlist.error ?? (workflow.watchlist.loading ? 'Stored stocks are still loading from ATrade.Api.' : 'No backend-stored stocks are saved yet. Use Search to pin exact provider instruments.')}
          emptyTitle={workflow.watchlist.loading ? 'Loading stored stocks…' : workflow.watchlist.error ? 'Stored stocks unavailable.' : 'No stored stocks yet.'}
          eyebrow="Stored stocks"
          onAction={() => openModule(workflow.watchlist.symbols.length > 0 ? 'WATCHLIST' : 'SEARCH', workflow.watchlist.symbols.length > 0 ? '/watchlist' : '/search')}
          onOpenAnalysis={openAnalysis}
          onOpenBacktest={openBacktest}
          onOpenChart={openChart}
          rows={watchlistRows}
          title="Watchlist preview"
        />
      </div>

      <TerminalProviderDiagnostics
        analysisStateLabel="Open ANALYSIS for configured engine discovery; Home never fabricates signals."
        marketDataSourceLabel="Home previews reuse provider/search/watchlist source labels from ATrade.Api payloads."
        signalRStateLabel="Live streams are reported inside chart/backtest workspaces, not faked on Home."
      />
    </section>
  );
}

function HomeStatusTile({ badge, detail, label, tone }: { badge: string; detail: string; label: string; tone: TerminalStatusTone }) {
  return (
    <div className="terminal-home-status-grid__item">
      <div>
        <span>{label}</span>
        <TerminalStatusBadge tone={tone} pulse={badge === 'Checking' || badge === 'Loading'}>{badge}</TerminalStatusBadge>
      </div>
      <p>{detail}</p>
    </div>
  );
}

function HomePreviewPanel({
  actionLabel,
  emptyDetail,
  emptyTitle,
  eyebrow,
  onAction,
  onOpenAnalysis,
  onOpenBacktest,
  onOpenChart,
  rows,
  title,
}: {
  actionLabel: string;
  emptyDetail: string;
  emptyTitle: string;
  eyebrow: string;
  onAction: () => void;
  onOpenAnalysis: (row: TerminalMarketMonitorRow) => void;
  onOpenBacktest: (row: TerminalMarketMonitorRow) => void;
  onOpenChart: (row: TerminalMarketMonitorRow) => void;
  rows: TerminalMarketMonitorRow[];
  title: string;
}) {
  return (
    <TerminalPanel
      className="terminal-home-preview terminal-scroll-owned"
      data-scroll-owner={`home-${eyebrow.toLowerCase().replace(/\s+/g, '-')}`}
      data-testid={`terminal-home-${eyebrow.toLowerCase().replace(/\s+/g, '-')}-preview`}
      density="compact"
      eyebrow={eyebrow}
      title={title}
      description="Compact truthful context only — open the dedicated module for the full sortable/filterable table."
      actions={<Button onClick={onAction} size="xs" type="button" variant="outline">{actionLabel}</Button>}
      tone="inset"
    >
      {rows.length === 0 ? (
        <div className="terminal-home-preview__empty" role="status">
          <strong>{emptyTitle}</strong>
          <span>{emptyDetail}</span>
        </div>
      ) : (
        <ul className="terminal-home-preview__list">
          {rows.map((row) => (
            <li className="terminal-home-preview__row" key={row.id}>
              <div>
                <strong>{row.symbol}</strong>
                <span>{row.name ?? 'Name unavailable'}</span>
                <small>{row.provider.toUpperCase()} · {row.providerSymbolId ?? 'provider id unavailable'} · {row.exchange ?? 'market unavailable'} · {row.currency} · {row.assetClass}</small>
              </div>
              <div className="terminal-home-preview__row-actions">
                <Button aria-label={`Open chart for ${row.symbol}`} onClick={() => onOpenChart(row)} size="xs" type="button" variant="terminal">
                  <BarChart3 aria-hidden="true" />
                  Chart
                </Button>
                <Button aria-label={`Open analysis for ${row.symbol}`} onClick={() => onOpenAnalysis(row)} size="xs" type="button" variant="outline">
                  <LineChart aria-hidden="true" />
                  Analysis
                </Button>
                <Button aria-label={`Open backtest for ${row.symbol}`} onClick={() => onOpenBacktest(row)} size="xs" type="button" variant="outline">
                  <Activity aria-hidden="true" />
                  Backtest
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </TerminalPanel>
  );
}

function buildHomeRowStatusMessage(moduleId: 'CHART' | 'ANALYSIS' | 'BACKTEST', row: TerminalMarketMonitorRow): string {
  const providerId = row.providerSymbolId ? ` provider id ${row.providerSymbolId}` : ' no provider id';
  const exchange = row.exchange ? ` on ${row.exchange}` : ' with market unavailable';
  return `Opening ${moduleId} for ${row.symbol} from Home preview (${row.provider.toUpperCase()}${providerId}${exchange}, ${row.currency}, ${row.assetClass}).`;
}
