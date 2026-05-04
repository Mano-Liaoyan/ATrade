'use client';

import * as React from 'react';
import { Search, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { MinimumSymbolSearchQueryLength } from '@/lib/symbolSearchWorkflow';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export type MarketMonitorSearchProps = {
  className?: string;
  compact?: boolean;
  error: string | null;
  loading: boolean;
  onQueryChange: (query: string) => void;
  query: string;
  resultCount: number;
  searchedQuery: string;
  validationMessage: string | null;
};

export function MarketMonitorSearch({
  className,
  compact = false,
  error,
  loading,
  onQueryChange,
  query,
  resultCount,
  searchedQuery,
  validationMessage,
}: MarketMonitorSearchProps) {
  const searchInputId = React.useId();
  const searchStatusId = React.useId();
  const trimmedQuery = query.trim();

  return (
    <section
      className={cn('market-monitor-search', compact && 'market-monitor-search--compact', className)}
      data-testid="market-monitor-search"
      aria-labelledby={`${searchInputId}-label`}
    >
      <div className="market-monitor-search__field">
        <label id={`${searchInputId}-label`} htmlFor={searchInputId}>
          <span className="market-monitor-search__label">Bounded IBKR stock search</span>
          <span className="market-monitor-search__hint">Minimum {MinimumSymbolSearchQueryLength} chars · capped API request · ranked locally</span>
        </label>
        <div className="market-monitor-search__control">
          <Search aria-hidden="true" className="market-monitor-search__icon" />
          <Input
            aria-describedby={searchStatusId}
            autoComplete="off"
            className="market-monitor-search__input"
            data-testid="market-monitor-search-input"
            id={searchInputId}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="SEARCH AAPL, MSFT, BRK.B…"
            spellCheck={false}
            value={query}
          />
          {trimmedQuery ? (
            <Button
              aria-label="Clear market monitor search"
              className="market-monitor-search__clear"
              onClick={() => onQueryChange('')}
              size="icon"
              type="button"
              variant="ghost"
            >
              <X aria-hidden="true" />
            </Button>
          ) : null}
        </div>
      </div>

      <div className="market-monitor-search__status" id={searchStatusId} aria-live="polite">
        <TerminalStatusBadge tone={loading ? 'info' : error ? 'danger' : validationMessage ? 'warning' : resultCount > 0 ? 'success' : 'neutral'} pulse={loading}>
          {loading ? 'Searching' : error ? 'Search unavailable' : validationMessage ? 'Waiting for query' : searchedQuery ? `${resultCount} ranked` : 'Ready'}
        </TerminalStatusBadge>
        <span>
          {error ?? validationMessage ?? (searchedQuery ? `Showing ranked results for ${searchedQuery}.` : 'Type a command or query; all browser data flows through ATrade.Api.')}
        </span>
      </div>
    </section>
  );
}
