'use client';

import * as React from 'react';
import { SlidersHorizontal } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type {
  TerminalMarketMonitorAvailableFilters,
  TerminalMarketMonitorFilterKey,
  TerminalMarketMonitorSelectedFilters,
} from '@/lib/terminalMarketMonitorWorkflow';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export const MarketMonitorFilterOrder: TerminalMarketMonitorFilterKey[] = ['source', 'saved', 'provider', 'exchange', 'currency', 'assetClass'];

const MarketMonitorFilterLabels: Record<TerminalMarketMonitorFilterKey, string> = {
  source: 'Source',
  saved: 'Pin state',
  provider: 'Provider',
  exchange: 'Market',
  currency: 'Currency',
  assetClass: 'Asset',
};

export type MarketMonitorFiltersProps = {
  availableFilters: TerminalMarketMonitorAvailableFilters;
  className?: string;
  compact?: boolean;
  onClearFilter: (key: TerminalMarketMonitorFilterKey) => void;
  onClearFilters: () => void;
  onFilterChange: (key: TerminalMarketMonitorFilterKey, value: string | null) => void;
  selectedFilters: TerminalMarketMonitorSelectedFilters;
};

export function MarketMonitorFilters({
  availableFilters,
  className,
  compact = false,
  onClearFilter,
  onClearFilters,
  onFilterChange,
  selectedFilters,
}: MarketMonitorFiltersProps) {
  const selectedCount = Object.keys(selectedFilters).length;

  return (
    <section className={cn('market-monitor-filters', compact && 'market-monitor-filters--compact', className)} data-testid="market-monitor-filters" aria-label="Market monitor filters">
      <div className="market-monitor-filters__header">
        <p className="market-monitor-filters__eyebrow"><SlidersHorizontal aria-hidden="true" /> Filter rows</p>
        <div className="market-monitor-filters__actions">
          <TerminalStatusBadge tone={selectedCount > 0 ? 'info' : 'neutral'}>{selectedCount} active</TerminalStatusBadge>
          <Button aria-label="Clear all market monitor filters" disabled={selectedCount === 0} onClick={onClearFilters} size="xs" type="button" variant="ghost">
            Clear all
          </Button>
        </div>
      </div>

      <div className="market-monitor-filters__groups" aria-label="Available market monitor filter groups">
        {MarketMonitorFilterOrder.map((key) => {
          const options = availableFilters[key];
          const selectedValue = selectedFilters[key];

          if (options.length === 0) {
            return null;
          }

          return (
            <fieldset className="market-monitor-filters__group" key={key}>
              <legend>{MarketMonitorFilterLabels[key]}</legend>
              <div className="market-monitor-filters__chips">
                {options.map((option) => {
                  const active = selectedValue === option.value;

                  return (
                    <Button
                      aria-pressed={active}
                      className="market-monitor-filters__chip"
                      data-monitor-filter-key={key}
                      data-monitor-filter-value={option.value}
                      key={option.value}
                      onClick={() => {
                        if (active) {
                          onClearFilter(key);
                        } else {
                          onFilterChange(key, option.value);
                        }
                      }}
                      size="xs"
                      type="button"
                      variant={active ? 'default' : 'outline'}
                    >
                      {option.label}
                      <span aria-label={`${option.count} rows`}>{option.count}</span>
                    </Button>
                  );
                })}
              </div>
            </fieldset>
          );
        })}
      </div>
    </section>
  );
}
