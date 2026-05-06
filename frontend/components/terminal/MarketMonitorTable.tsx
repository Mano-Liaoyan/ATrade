'use client';

import * as React from 'react';
import Link from 'next/link';
import { Activity, ArrowDownAZ, ArrowDownZA, BarChart3, FlaskConical, Pin, PinOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type {
  TerminalMarketMonitorRow,
  TerminalMarketMonitorSortKey,
  TerminalMarketMonitorSortState,
} from '@/lib/terminalMarketMonitorWorkflow';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type MarketMonitorTableProps = {
  className?: string;
  compact?: boolean;
  onOpenAnalysis?: (row: TerminalMarketMonitorRow) => void;
  onOpenBacktest?: (row: TerminalMarketMonitorRow) => void;
  onOpenChart?: (row: TerminalMarketMonitorRow) => void;
  onSelectRow: (rowId: string) => void;
  onSort: (key: TerminalMarketMonitorSortKey) => void;
  onTogglePin: (row: TerminalMarketMonitorRow) => void;
  rows: TerminalMarketMonitorRow[];
  selectedRowId: string | null;
  sort: TerminalMarketMonitorSortState;
};

type SortColumn = {
  key: TerminalMarketMonitorSortKey;
  label: string;
  className?: string;
};

const SortColumns: SortColumn[] = [
  { key: 'rank', label: 'Rank' },
  { key: 'symbol', label: 'Symbol' },
  { key: 'name', label: 'Name', className: 'market-monitor-table__name-column' },
  { key: 'provider', label: 'Provider' },
  { key: 'providerSymbolId', label: 'Provider ID' },
  { key: 'exchange', label: 'Market' },
  { key: 'currency', label: 'CCY' },
  { key: 'assetClass', label: 'Asset' },
  { key: 'source', label: 'Source' },
  { key: 'score', label: 'Score' },
  { key: 'changePercent', label: 'Δ%' },
  { key: 'saved', label: 'Pin' },
];

export function MarketMonitorTable({
  className,
  compact = false,
  onOpenAnalysis,
  onOpenBacktest,
  onOpenChart,
  onSelectRow,
  onSort,
  onTogglePin,
  rows,
  selectedRowId,
  sort,
}: MarketMonitorTableProps) {
  return (
    <section
      className={cn('market-monitor-table-shell', compact && 'market-monitor-table-shell--compact', className)}
      data-scroll-owner="market-monitor-table"
      data-scrollbars="vertical horizontal"
      data-testid="market-monitor-table"
      aria-label="Market monitor rows"
    >
      <ScrollArea className="market-monitor-table-scroll" data-scroll-axis="vertical horizontal" type="always">
        <table className="market-monitor-table">
          <caption>
            Dense market monitor combining backend watchlist pins, bounded ranked search results, and provider-backed trending rows.
          </caption>
          <thead>
            <tr>
              {SortColumns.map((column) => (
                <th aria-sort={getAriaSort(column.key, sort)} className={column.className} key={column.key} scope="col">
                  <button className="market-monitor-table__sort" onClick={() => onSort(column.key)} type="button">
                    <span>{column.label}</span>
                    {sort.key === column.key ? (
                      sort.direction === 'asc' ? <ArrowDownAZ aria-hidden="true" /> : <ArrowDownZA aria-hidden="true" />
                    ) : null}
                  </button>
                </th>
              ))}
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={SortColumns.length + 1}>
                  <div className="market-monitor-table__empty" role="status">
                    <strong>No instruments in the current monitor view.</strong>
                    <span>Load provider trending, type a bounded search query, adjust filters, or add backend watchlist pins.</span>
                  </div>
                </td>
              </tr>
            ) : rows.map((row) => {
              const selected = row.id === selectedRowId;
              return (
                <tr
                  aria-selected={selected}
                  className={cn(selected && 'market-monitor-table__row--selected')}
                  data-monitor-row-source={row.source}
                  data-selected={selected ? 'true' : 'false'}
                  data-testid="market-monitor-row"
                  key={row.id}
                >
                  <td>
                    <button className="market-monitor-table__select" onClick={() => onSelectRow(row.id)} type="button">
                      <span>{row.rankLabel}</span>
                      <small>{formatSourceLabel(row.source)}</small>
                    </button>
                  </td>
                  <td>
                    <button className="market-monitor-table__symbol" onClick={() => onSelectRow(row.id)} type="button">
                      {row.symbol}
                    </button>
                  </td>
                  <td className="market-monitor-table__name-column">
                    <span className="market-monitor-table__name">{row.name ?? 'Name unavailable'}</span>
                  </td>
                  <td><IdentityChip>{row.provider.toUpperCase()}</IdentityChip></td>
                  <td><code>{row.providerSymbolId ? formatProviderId(row.provider, row.providerSymbolId) : '—'}</code></td>
                  <td><code>{row.exchange ?? '—'}</code></td>
                  <td><code>{row.currency}</code></td>
                  <td><code>{row.assetClass}</code></td>
                  <td>
                    <div className="market-monitor-table__source">
                      <TerminalStatusBadge tone={getSourceTone(row.source)}>{formatSourceLabel(row.source)}</TerminalStatusBadge>
                      <small>{row.sourceLabel}</small>
                    </div>
                  </td>
                  <td><code>{row.score === null ? '—' : formatScore(row.score)}</code></td>
                  <td>
                    <span className={cn('market-monitor-table__change', row.changePercent !== null && row.changePercent >= 0 && 'market-monitor-table__change--positive', row.changePercent !== null && row.changePercent < 0 && 'market-monitor-table__change--negative')}>
                      {row.changePercent === null ? '—' : `${row.changePercent.toFixed(2)}%`}
                    </span>
                  </td>
                  <td>
                    <TerminalStatusBadge tone={row.saved ? 'success' : row.saving ? 'warning' : 'neutral'} pulse={row.saving}>
                      {row.saving ? 'Saving' : row.saved ? 'Saved' : 'Not saved'}
                    </TerminalStatusBadge>
                  </td>
                  <td>
                    <div className="market-monitor-table__actions">
                      <Button
                        aria-label={`${row.saved ? 'Unpin' : 'Pin'} ${row.symbol}`}
                        disabled={row.disabled}
                        onClick={() => onTogglePin(row)}
                        size="xs"
                        type="button"
                        variant={row.saved ? 'ghost' : 'amber'}
                      >
                        {row.saved ? <PinOff aria-hidden="true" /> : <Pin aria-hidden="true" />}
                        {row.saved ? 'Unpin' : 'Pin'}
                      </Button>
                      <MarketMonitorLinkButton href={row.chartHref} label={`Open chart for ${row.symbol}`} onClick={onOpenChart ? () => onOpenChart(row) : undefined}>
                        <BarChart3 aria-hidden="true" />
                        Chart
                      </MarketMonitorLinkButton>
                      <MarketMonitorLinkButton href={row.analysisHref} label={`Open analysis for ${row.symbol}`} onClick={onOpenAnalysis ? () => onOpenAnalysis(row) : undefined} variant="outline">
                        <FlaskConical aria-hidden="true" />
                        Analysis
                      </MarketMonitorLinkButton>
                      <MarketMonitorLinkButton href={row.backtestHref} label={`Open backtest for ${row.symbol}`} onClick={onOpenBacktest ? () => onOpenBacktest(row) : undefined} variant="outline">
                        <Activity aria-hidden="true" />
                        Backtest
                      </MarketMonitorLinkButton>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ScrollArea>
    </section>
  );
}

function MarketMonitorLinkButton({
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
      <Button aria-label={label} onClick={onClick} size="xs" type="button" variant={variant}>
        {children}
      </Button>
    );
  }

  return (
    <Button aria-label={label} asChild size="xs" variant={variant}>
      <Link href={href}>{children}</Link>
    </Button>
  );
}

function IdentityChip({ children }: { children: React.ReactNode }) {
  return <span className="market-monitor-table__identity-chip">{children}</span>;
}

function getAriaSort(key: TerminalMarketMonitorSortKey, sort: TerminalMarketMonitorSortState): 'none' | 'ascending' | 'descending' {
  if (sort.key !== key) {
    return 'none';
  }

  return sort.direction === 'asc' ? 'ascending' : 'descending';
}

function formatProviderId(provider: string, providerSymbolId: string): string {
  return provider.toLowerCase() === 'ibkr' ? `IBKR ${providerSymbolId}` : `${provider.toUpperCase()} ${providerSymbolId}`;
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? String(score) : score.toFixed(2);
}

function formatSourceLabel(source: TerminalMarketMonitorRow['source']): string {
  if (source === 'watchlist') {
    return 'Watchlist';
  }

  return source === 'search' ? 'Search' : 'Trending';
}

function getSourceTone(source: TerminalMarketMonitorRow['source']): 'info' | 'success' | 'warning' {
  if (source === 'watchlist') {
    return 'success';
  }

  return source === 'search' ? 'info' : 'warning';
}
