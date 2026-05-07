'use client';

import type { TerminalNavigationIntent } from '@/types/terminal';
import { TerminalMarketMonitor } from './TerminalMarketMonitor';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

type TerminalSearchModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery?: string;
};

export function TerminalSearchModule({ onOpenIntent, searchQuery = '' }: TerminalSearchModuleProps) {
  return (
    <section className="terminal-module terminal-module--search workspace-stack" data-testid="terminal-search-module" id="terminal-search" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Search"
        title="Bounded stock discovery"
        description="Search starts with the API-backed symbol query, ranked results, exact identity metadata, and chart or pin actions. Trending and saved rows stay secondary context."
        actions={<TerminalStatusBadge tone="info">Search first</TerminalStatusBadge>}
      >
        <p className="terminal-module-purpose-copy">Type a stock symbol or company name to query ATrade.Api with capped IBKR stock search limits; no browser-side provider calls or synthetic catalogs are used.</p>
      </TerminalPanel>
      <TerminalMarketMonitor initialSearchQuery={searchQuery} initialSelectedFilters={{ source: 'search' }} onOpenIntent={onOpenIntent} title={searchQuery ? `Search results · ${searchQuery}` : 'Search-first results'} />
    </section>
  );
}
