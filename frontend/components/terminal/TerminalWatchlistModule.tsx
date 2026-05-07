'use client';

import type { TerminalNavigationIntent } from '@/types/terminal';
import { TerminalMarketMonitor } from './TerminalMarketMonitor';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

type TerminalWatchlistModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
};

export function TerminalWatchlistModule({ onOpenIntent }: TerminalWatchlistModuleProps) {
  return (
    <section className="terminal-module terminal-module--watchlist workspace-stack" data-testid="terminal-watchlist-module" id="terminal-watchlist" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Watchlist"
        title="Saved stocks workspace"
        description="Watchlist starts from backend-owned exact provider pins and keeps manage/remove, chart, analysis, and backtest actions close to saved identity metadata."
        actions={<TerminalStatusBadge tone="success">Backend pins</TerminalStatusBadge>}
      >
        <p className="terminal-module-purpose-copy">Stored stocks come from ATrade.Api workspace preferences; browser localStorage is never authoritative for saved instruments.</p>
      </TerminalPanel>
      <TerminalMarketMonitor initialSelectedFilters={{ source: 'watchlist' }} onOpenIntent={onOpenIntent} title="Saved stocks monitor" />
    </section>
  );
}
