'use client';

import * as React from 'react';
import Link from 'next/link';
import { Activity, BarChart3, FlaskConical, Pin, PinOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { TerminalMarketMonitorRow } from '@/lib/terminalMarketMonitorWorkflow';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type MarketMonitorDetailPanelProps = {
  className?: string;
  compact?: boolean;
  onOpenAnalysis?: (row: TerminalMarketMonitorRow) => void;
  onOpenBacktest?: (row: TerminalMarketMonitorRow) => void;
  onOpenChart?: (row: TerminalMarketMonitorRow) => void;
  onTogglePin: (row: TerminalMarketMonitorRow) => void;
  row: TerminalMarketMonitorRow | null;
};

export function MarketMonitorDetailPanel({
  className,
  compact = false,
  onOpenAnalysis,
  onOpenBacktest,
  onOpenChart,
  onTogglePin,
  row,
}: MarketMonitorDetailPanelProps) {
  if (!row) {
    return (
      <TerminalPanel
        className={cn('market-monitor-detail', compact && 'market-monitor-detail--compact', className)}
        data-testid="market-monitor-detail-panel"
        density="compact"
        eyebrow="Selection"
        title="No instrument selected"
        description="Select a market monitor row to inspect exact provider identity and route chart or analysis actions."
        tone="inset"
      >
        <div className="market-monitor-detail__empty" role="status">
          <strong>No row selected.</strong>
          <span>Trending, search, and watchlist states remain visible without fabricating a selected instrument.</span>
        </div>
      </TerminalPanel>
    );
  }

  return (
    <TerminalPanel
      className={cn('market-monitor-detail', compact && 'market-monitor-detail--compact', className)}
      data-testid="market-monitor-detail-panel"
      density="compact"
      eyebrow="Selected instrument"
      title={`${row.symbol} · ${row.provider.toUpperCase()} identity`}
      description="Exact provider-market identity is preserved for chart, analysis, and backend watchlist pin actions."
      tone="inset"
      actions={(
        <div className="market-monitor-detail__badges">
          <TerminalStatusBadge tone={row.saved ? 'success' : 'neutral'}>{row.saved ? 'Pinned' : 'Not pinned'}</TerminalStatusBadge>
          <TerminalStatusBadge tone={row.source === 'watchlist' ? 'success' : row.source === 'search' ? 'info' : 'warning'}>{formatSource(row.source)}</TerminalStatusBadge>
        </div>
      )}
    >
      <div className="market-monitor-detail__body">
        <div className="market-monitor-detail__hero">
          <div>
            <p>{row.rankLabel}</p>
            <h3>{row.symbol}</h3>
            <span>{row.name ?? 'Name unavailable'}</span>
          </div>
          <div className="market-monitor-detail__quote">
            <span>Last</span>
            <strong>{row.lastPrice === null ? '—' : formatCurrency(row.lastPrice, row.currency)}</strong>
            <small className={cn(row.changePercent !== null && row.changePercent >= 0 && 'market-monitor-detail__change--positive', row.changePercent !== null && row.changePercent < 0 && 'market-monitor-detail__change--negative')}>
              {row.changePercent === null ? 'Change unavailable' : `${row.changePercent.toFixed(2)}%`}
            </small>
          </div>
        </div>

        <dl className="market-monitor-detail__identity" data-testid="market-monitor-exact-identity">
          <IdentityItem label="Provider" value={row.provider.toUpperCase()} />
          <IdentityItem label="Provider ID" value={row.providerSymbolId ?? 'Unavailable'} code />
          <IdentityItem label="IBKR conid" value={row.ibkrConid === null ? 'Unavailable' : String(row.ibkrConid)} code />
          <IdentityItem label="Symbol" value={row.symbol} code />
          <IdentityItem label="Exchange" value={row.exchange ?? 'Unavailable'} code />
          <IdentityItem label="Currency" value={row.currency} code />
          <IdentityItem label="Asset class" value={row.assetClass} code />
          <IdentityItem label="Pin key" value={row.pinKey} code />
          <IdentityItem label="Source" value={row.sourceLabel} />
          <IdentityItem label="Score/rank" value={row.score === null ? row.rankLabel : `${row.rankLabel} · score ${formatScore(row.score)}`} />
        </dl>

        {row.reasons.length > 0 ? (
          <div className="market-monitor-detail__reasons">
            <strong>Provider reasons</strong>
            <ul>
              {row.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          </div>
        ) : null}

        <div className="market-monitor-detail__actions">
          <Button
            disabled={row.disabled}
            onClick={() => onTogglePin(row)}
            size="sm"
            type="button"
            variant={row.saved ? 'ghost' : 'amber'}
          >
            {row.saved ? <PinOff aria-hidden="true" /> : <Pin aria-hidden="true" />}
            {row.saving ? 'Saving pin…' : row.saved ? 'Remove exact pin' : 'Save exact pin'}
          </Button>
          <DetailActionButton href={row.chartHref} label={`Open chart for ${row.symbol}`} onClick={onOpenChart ? () => onOpenChart(row) : undefined}>
            <BarChart3 aria-hidden="true" />
            Open chart
          </DetailActionButton>
          <DetailActionButton href={row.analysisHref} label={`Open analysis for ${row.symbol}`} onClick={onOpenAnalysis ? () => onOpenAnalysis(row) : undefined} variant="outline">
            <FlaskConical aria-hidden="true" />
            Open analysis
          </DetailActionButton>
          <DetailActionButton href={row.backtestHref} label={`Open backtest for ${row.symbol}`} onClick={onOpenBacktest ? () => onOpenBacktest(row) : undefined} variant="outline">
            <Activity aria-hidden="true" />
            Open backtest
          </DetailActionButton>
        </div>
      </div>
    </TerminalPanel>
  );
}

function IdentityItem({ label, value, code = false }: { label: string; value: string; code?: boolean }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{code ? <code>{value}</code> : value}</dd>
    </div>
  );
}

function DetailActionButton({
  children,
  href,
  label,
  onClick,
  variant = 'terminal',
}: {
  children: React.ReactNode;
  href: string;
  label: string;
  onClick?: () => void;
  variant?: 'terminal' | 'outline';
}) {
  if (onClick) {
    return (
      <Button aria-label={label} onClick={onClick} size="sm" type="button" variant={variant}>
        {children}
      </Button>
    );
  }

  return (
    <Button aria-label={label} asChild size="sm" variant={variant}>
      <Link href={href}>{children}</Link>
    </Button>
  );
}

function formatSource(source: TerminalMarketMonitorRow['source']): string {
  if (source === 'watchlist') {
    return 'Backend watchlist';
  }

  return source === 'search' ? 'Bounded search' : 'Trending';
}

function formatCurrency(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('en-US', { currency, style: 'currency', maximumFractionDigits: 2 }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? String(score) : score.toFixed(2);
}
