'use client';

import type { TerminalNavigationIntent } from '@/types/terminal';
import { TerminalMarketMonitor } from './TerminalMarketMonitor';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge } from './TerminalStatusBadge';

type TerminalHomeModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery?: string;
};

export function TerminalHomeModule({ onOpenIntent, searchQuery = '' }: TerminalHomeModuleProps) {
  return (
    <section className="terminal-module terminal-module--home workspace-stack" data-testid="terminal-home-module" id="terminal-module-home" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Home"
        title="Paper workspace home"
        description="Paper-only module workspace with provider state, search, watchlist, chart, analysis, status, help, and the dense market monitor."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <div className="terminal-home-summary">
          <div>
            <span>Market monitor</span>
            <strong>Search · watch · trend</strong>
            <small>Unified bounded search, provider trending, and backend-owned exact pins.</small>
          </div>
          <div>
            <span>Identity</span>
            <strong>Exact handoff</strong>
            <small>Provider, provider ID, market, currency, and asset class stay on chart/analysis routes.</small>
          </div>
          <div>
            <span>Safety</span>
            <strong>No live orders</strong>
            <small>Orders are disabled by the paper-only safety contract.</small>
          </div>
        </div>
      </TerminalPanel>

      <TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />
    </section>
  );
}
