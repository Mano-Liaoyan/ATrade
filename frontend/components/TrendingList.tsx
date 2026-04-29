'use client';

import Link from 'next/link';
import type { TrendingSymbol } from '../types/marketData';

type TrendingListProps = {
  symbols: TrendingSymbol[];
  pinnedSymbols: string[];
  onTogglePin: (symbol: TrendingSymbol) => void;
  actionsDisabled?: boolean;
  savingSymbol?: string | null;
};

export function TrendingList({ symbols, pinnedSymbols, onTogglePin, actionsDisabled = false, savingSymbol = null }: TrendingListProps) {
  const pinnedSet = new Set(pinnedSymbols.map((symbol) => symbol.toUpperCase()));

  return (
    <section className="workspace-panel" aria-labelledby="trending-title" data-testid="trending-list">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Backend-driven market data</p>
          <h2 id="trending-title">Trending stocks and ETFs</h2>
        </div>
        <span className="pill">IBKR scanner factors</span>
      </div>

      <div className="symbol-grid">
        {symbols.map((symbol) => {
          const pinned = pinnedSet.has(symbol.symbol);
          const isSaving = savingSymbol === symbol.symbol.toUpperCase();

          return (
            <article className="symbol-card" key={symbol.symbol}>
              <div className="symbol-card__topline">
                <div>
                  <Link className="symbol-link" href={`/symbols/${encodeURIComponent(symbol.symbol)}`}>
                    {symbol.symbol}
                  </Link>
                  <p>{symbol.name}</p>
                </div>
                <button
                  className={pinned ? 'pin-button pin-button--active' : 'pin-button'}
                  type="button"
                  aria-pressed={pinned}
                  disabled={actionsDisabled || isSaving}
                  onClick={() => onTogglePin(symbol)}
                >
                  {isSaving ? (pinned ? 'Removing…' : 'Saving…') : pinned ? 'Pinned' : 'Pin'}
                </button>
              </div>

              <dl className="metric-row">
                <div>
                  <dt>Type</dt>
                  <dd>{symbol.assetClass}</dd>
                </div>
                <div>
                  <dt>Last</dt>
                  <dd>{formatCurrency(symbol.lastPrice)}</dd>
                </div>
                <div>
                  <dt>Score</dt>
                  <dd>{symbol.score.toFixed(1)}</dd>
                </div>
              </dl>

              <div className="factor-strip" aria-label={`${symbol.symbol} trending factor breakdown`}>
                <span>Volume {symbol.factors.volumeSpike.toFixed(2)}x</span>
                <span>Momentum {symbol.factors.priceMomentum.toFixed(2)}%</span>
                <span>Volatility {symbol.factors.volatility.toFixed(2)}%</span>
              </div>

              <Link className="open-chart-link" href={`/symbols/${encodeURIComponent(symbol.symbol)}`}>
                Open chart workspace
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}
