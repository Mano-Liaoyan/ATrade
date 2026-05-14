'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import {
  normalizeInstrumentIdentity,
  type InstrumentIdentityInput,
  type NormalizedInstrumentIdentity,
} from '@/lib/instrumentIdentity';
import { createTerminalModuleRoute, createTerminalSymbolRoute } from '@/lib/terminalRoutes';
import { useTerminalChartWorkspaceWorkflow } from '@/lib/terminalChartWorkspaceWorkflow';
import { getWatchlistPinKey, type WatchlistSymbol } from '@/lib/watchlistClient';
import { useWatchlistWorkflow } from '@/lib/watchlistWorkflow';
import type { ChartRange } from '@/types/marketData';
import type { EnabledTerminalModuleId, TerminalNavigationIntent } from '@/types/terminal';
import { TerminalChartWorkspace } from './TerminalChartWorkspace';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type TerminalChartLandingModuleProps = {
  initialChartRange: ChartRange;
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
};

type StoredStockCandidate = {
  id: string;
  pinKey: string;
  rank: number;
  symbol: string;
  name: string | null;
  sourceLabel: string;
  identity: NormalizedInstrumentIdentity;
  routeIdentity: InstrumentIdentityInput;
  chartHref: string;
  analysisHref: string;
  backtestHref: string;
};

export function TerminalChartLandingModule({
  initialChartRange,
  onOpenIntent,
}: TerminalChartLandingModuleProps) {
  const watchlist = useWatchlistWorkflow();
  const candidates = useMemo(
    () => watchlist.symbols.map((symbol, index) => createStoredStockCandidate(symbol, index, watchlist.source, initialChartRange)),
    [initialChartRange, watchlist.source, watchlist.symbols],
  );
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedCandidateId((currentCandidateId) => {
      if (candidates.length === 0) {
        return null;
      }

      if (currentCandidateId && candidates.some((candidate) => candidate.id === currentCandidateId)) {
        return currentCandidateId;
      }

      return candidates[0].id;
    });
  }, [candidates]);

  const selectedCandidate = candidates.find((candidate) => candidate.id === selectedCandidateId) ?? candidates[0] ?? null;
  const landingState = createLandingState({
    candidateCount: candidates.length,
    loading: watchlist.loading,
    error: watchlist.error,
    source: watchlist.source,
  });

  const openCandidate = (candidate: StoredStockCandidate, moduleId: Extract<EnabledTerminalModuleId, 'CHART' | 'ANALYSIS' | 'BACKTEST'>) => {
    const route = moduleId === 'CHART' ? candidate.chartHref : moduleId === 'ANALYSIS' ? candidate.analysisHref : candidate.backtestHref;
    onOpenIntent(
      {
        moduleId,
        route,
        focusTargetId: moduleId === 'CHART' ? 'terminal-chart' : moduleId === 'ANALYSIS' ? 'terminal-analysis' : 'terminal-backtest',
        symbol: candidate.symbol,
        identity: candidate.routeIdentity,
        chartRange: initialChartRange,
      },
      `Opening ${moduleId} for stored stock ${candidate.symbol} with ${formatIdentitySummary(candidate.identity)}.`,
    );
  };

  return (
    <section className="terminal-module terminal-module--chart terminal-chart-landing terminal-module-scroll-surface workspace-stack" data-testid="terminal-chart-landing-module" id="terminal-chart" tabIndex={-1}>
      <TerminalPanel
        className="terminal-chart-landing__panel"
        eyebrow="Chart"
        title="Stored stocks"
        description="Select a stored stock for the default chart."
        actions={(
          <div className="terminal-chart-landing__status-actions">
            <TerminalStatusBadge tone={landingState.tone} pulse={watchlist.loading}>{landingState.badge}</TerminalStatusBadge>
            <Button onClick={watchlist.retry} size="xs" type="button" variant="outline">Reload stored stocks</Button>
          </div>
        )}
      >
        <div className="terminal-chart-landing__body">
          <StoredStocksSelector
            candidates={candidates}
            landingState={landingState}
            onOpenCandidate={openCandidate}
            onSelectCandidate={setSelectedCandidateId}
            selectedCandidateId={selectedCandidate?.id ?? null}
          />

          <section className="terminal-chart-landing__chart-region terminal-scroll-owned" data-scroll-owner="chart-landing-region" data-testid="stored-stock-chart-region">
            {selectedCandidate ? (
              <StoredStockChart key={selectedCandidate.id} candidate={selectedCandidate} initialChartRange={initialChartRange} />
            ) : (
              <StoredStocksEmptyState error={watchlist.error} loading={watchlist.loading} source={watchlist.source} />
            )}
          </section>
        </div>
      </TerminalPanel>
    </section>
  );
}

function StoredStocksSelector({
  candidates,
  landingState,
  onOpenCandidate,
  onSelectCandidate,
  selectedCandidateId,
}: {
  candidates: StoredStockCandidate[];
  landingState: StoredStocksLandingState;
  onOpenCandidate: (candidate: StoredStockCandidate, moduleId: Extract<EnabledTerminalModuleId, 'CHART' | 'ANALYSIS' | 'BACKTEST'>) => void;
  onSelectCandidate: (candidateId: string) => void;
  selectedCandidateId: string | null;
}) {
  return (
    <aside className="terminal-chart-landing__selector terminal-scroll-owned" data-scroll-owner="stored-stocks-selector" data-testid="stored-stocks-selector" data-watchlist-source={landingState.source} aria-label="Stored stocks selector">
      <div className="terminal-chart-landing__selector-heading">
        <div>
          <p className="eyebrow">Backend watchlist</p>
          <h2>Stored stocks selector</h2>
        </div>
        <TerminalStatusBadge tone={landingState.tone} pulse={landingState.loading}>{landingState.badge}</TerminalStatusBadge>
      </div>
      <p className="terminal-chart-landing__state-copy" role={landingState.error && !landingState.hasCandidates ? 'alert' : 'status'}>
        {landingState.copy}
      </p>

      {candidates.length > 0 ? (
        <div className="terminal-chart-landing__list" role="list" aria-label="Stored watchlist stocks">
          {candidates.map((candidate, index) => {
            const selected = candidate.id === selectedCandidateId;

            return (
              <article className={selected ? 'terminal-chart-landing__stock terminal-chart-landing__stock--selected' : 'terminal-chart-landing__stock'} data-testid="stored-stock-option" key={candidate.id} role="listitem">
                <button
                  aria-current={selected ? 'true' : undefined}
                  className="terminal-chart-landing__stock-button"
                  onClick={() => onSelectCandidate(candidate.id)}
                  type="button"
                >
                  <span>
                    <strong>{candidate.symbol}</strong>
                    <small>{candidate.name ?? 'Stored watchlist instrument'}</small>
                  </span>
                  <span className="terminal-chart-landing__stock-meta">
                    <code>{candidate.identity.provider.toUpperCase()}</code>
                    <code>{candidate.identity.providerSymbolId ?? 'no-provider-id'}</code>
                    <code>{candidate.identity.exchange ?? 'market-unavailable'}</code>
                  </span>
                  {index === 0 ? <em data-testid="stored-stock-default-candidate">Default chart candidate</em> : null}
                </button>

                <div className="terminal-chart-landing__route-actions" data-testid="stored-stock-route-handoff" data-chart-href={candidate.chartHref} data-analysis-href={candidate.analysisHref} data-backtest-href={candidate.backtestHref}>
                  <LandingRouteButton href={candidate.chartHref} label={`Open canonical chart route for ${candidate.symbol}`} onClick={() => onOpenCandidate(candidate, 'CHART')}>Chart</LandingRouteButton>
                  <LandingRouteButton href={candidate.analysisHref} label={`Open canonical analysis route for ${candidate.symbol}`} onClick={() => onOpenCandidate(candidate, 'ANALYSIS')} variant="outline">Analysis</LandingRouteButton>
                  <LandingRouteButton href={candidate.backtestHref} label={`Open canonical backtest route for ${candidate.symbol}`} onClick={() => onOpenCandidate(candidate, 'BACKTEST')} variant="outline">Backtest</LandingRouteButton>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <StoredStocksLinks state={landingState} />
      )}
    </aside>
  );
}

function StoredStockChart({ candidate, initialChartRange }: { candidate: StoredStockCandidate; initialChartRange: ChartRange }) {
  const chart = useTerminalChartWorkspaceWorkflow({
    symbol: candidate.symbol,
    identity: candidate.identity,
    initialChartRange,
  });

  return (
    <div className="terminal-chart-landing__selected-chart" data-testid="stored-stock-default-chart" data-selected-symbol={candidate.symbol} data-selected-provider={candidate.identity.provider} data-selected-provider-symbol-id={candidate.identity.providerSymbolId ?? ''}>
      <div className="terminal-chart-landing__selected-heading">
        <div>
          <p className="eyebrow">Selected stored stock</p>
          <h2>{candidate.symbol} default chart</h2>
          <p>{formatIdentitySummary(candidate.identity)}. Provider-unavailable and empty candles stay visible.</p>
        </div>
        <TerminalStatusBadge tone="info">{candidate.sourceLabel}</TerminalStatusBadge>
      </div>
      <TerminalChartWorkspace chart={chart} className="terminal-chart-landing__workspace" identity={candidate.identity} includeAnalysis={false} />
    </div>
  );
}

function StoredStocksEmptyState({ error, loading, source }: { error: string | null; loading: boolean; source: 'backend' | 'cache' }) {
  if (loading) {
    return <div className="loading-state" role="status">Loading stored stocks…</div>;
  }

  const unavailable = Boolean(error);

  return (
    <div className={unavailable ? 'error-state' : 'empty-state'} data-testid={unavailable ? 'stored-stocks-unavailable-state' : 'stored-stocks-empty-state'} role={unavailable ? 'alert' : 'status'}>
      <strong>{unavailable ? 'Stored stocks unavailable.' : 'No stored stocks yet.'}</strong>
      <p>
        {unavailable
          ? `${error} ${source === 'cache' ? 'No cached pins available.' : 'No stored stocks available.'}`
          : 'Pin a stock from Search or Watchlist.'}
      </p>
      <div className="terminal-chart-landing__empty-actions">
        <Button asChild size="sm" variant="terminal"><Link href={createTerminalModuleRoute('SEARCH')}>Open Search</Link></Button>
        <Button asChild size="sm" variant="outline"><Link href={createTerminalModuleRoute('WATCHLIST')}>Open Watchlist</Link></Button>
      </div>
    </div>
  );
}

function StoredStocksLinks({ state }: { state: StoredStocksLandingState }) {
  const unavailable = Boolean(state.error);

  return (
    <div className="terminal-chart-landing__links" data-testid={unavailable ? 'stored-stocks-unavailable-state' : 'stored-stocks-empty-state'} role={unavailable ? 'alert' : 'status'}>
      <strong>{unavailable ? 'Stored stocks cannot be loaded.' : 'Stored stocks list is empty.'}</strong>
      <p>{state.copy}</p>
      <div className="terminal-chart-landing__empty-actions">
        <Button asChild size="sm" variant="terminal"><Link href={createTerminalModuleRoute('SEARCH')}>Find stocks in Search</Link></Button>
        <Button asChild size="sm" variant="outline"><Link href={createTerminalModuleRoute('WATCHLIST')}>Review Watchlist</Link></Button>
      </div>
    </div>
  );
}

function LandingRouteButton({
  children,
  href,
  label,
  onClick,
  variant = 'terminal',
}: {
  children: ReactNode;
  href: string;
  label: string;
  onClick: () => void;
  variant?: 'terminal' | 'outline';
}) {
  return (
    <Button aria-label={label} onClick={onClick} size="xs" type="button" variant={variant}>
      <span data-href={href}>{children}</span>
    </Button>
  );
}

type StoredStocksLandingState = {
  badge: string;
  copy: string;
  error: string | null;
  hasCandidates: boolean;
  loading: boolean;
  source: 'backend' | 'cache';
  tone: 'info' | 'success' | 'warning';
};

function createLandingState({
  candidateCount,
  loading,
  error,
  source,
}: {
  candidateCount: number;
  loading: boolean;
  error: string | null;
  source: 'backend' | 'cache';
}): StoredStocksLandingState {
  if (loading) {
    return {
      badge: 'Loading stored stocks',
      copy: 'Loading stored stocks.',
      error,
      hasCandidates: candidateCount > 0,
      loading,
      source,
      tone: 'info',
    };
  }

  if (error && candidateCount > 0) {
    return {
      badge: 'Cached fallback',
      copy: `${error} Cached fallback shown.`,
      error,
      hasCandidates: true,
      loading,
      source,
      tone: 'warning',
    };
  }

  if (error) {
    return {
      badge: 'Stored stocks unavailable',
      copy: `${error} Stored stocks unavailable.`,
      error,
      hasCandidates: false,
      loading,
      source,
      tone: 'warning',
    };
  }

  if (candidateCount === 0) {
    return {
      badge: 'No stored stocks',
      copy: 'No stored stocks yet.',
      error,
      hasCandidates: false,
      loading,
      source,
      tone: 'warning',
    };
  }

  return {
    badge: `${candidateCount} stored`,
    copy: 'Default chart uses the first stored stock; select another to change it.',
    error,
    hasCandidates: true,
    loading,
    source,
    tone: 'success',
  };
}

function createStoredStockCandidate(symbol: WatchlistSymbol, index: number, source: 'backend' | 'cache', chartRange: ChartRange): StoredStockCandidate {
  const identity = normalizeInstrumentIdentity({
    symbol: symbol.symbol,
    provider: symbol.provider,
    providerSymbolId: symbol.providerSymbolId,
    ibkrConid: symbol.ibkrConid,
    exchange: symbol.exchange,
    currency: symbol.currency,
    assetClass: symbol.assetClass,
  });
  const pinKey = getWatchlistPinKey(symbol);
  const rank = Number.isFinite(symbol.sortOrder) ? symbol.sortOrder + 1 : index + 1;

  return {
    id: pinKey,
    pinKey,
    rank,
    symbol: identity.symbol,
    name: symbol.name,
    sourceLabel: source === 'cache' ? 'cached fallback' : 'backend watchlist',
    identity,
    routeIdentity: toRouteIdentity(identity),
    chartHref: createTerminalSymbolRoute('CHART', identity, { chartRange }),
    analysisHref: createTerminalSymbolRoute('ANALYSIS', identity, { chartRange }),
    backtestHref: createTerminalSymbolRoute('BACKTEST', identity, { chartRange }),
  };
}

function toRouteIdentity(identity: NormalizedInstrumentIdentity): InstrumentIdentityInput {
  return {
    symbol: identity.symbol,
    provider: identity.provider,
    providerSymbolId: identity.providerSymbolId,
    ibkrConid: identity.ibkrConid,
    assetClass: identity.assetClass,
    exchange: identity.exchange,
    currency: identity.currency,
  };
}

function formatIdentitySummary(identity: InstrumentIdentityInput): string {
  const normalized = normalizeInstrumentIdentity(identity);
  const providerId = normalized.providerSymbolId ? `provider id ${normalized.providerSymbolId}` : 'no provider id';
  const ibkrConid = normalized.ibkrConid === null ? 'IBKR conid unavailable' : `IBKR conid ${normalized.ibkrConid}`;
  const market = normalized.exchange ? `market ${normalized.exchange}` : 'market unavailable';

  return `${normalized.provider.toUpperCase()} ${providerId}, ${ibkrConid}, ${market}, ${normalized.currency}, ${normalized.assetClass}`;
}
