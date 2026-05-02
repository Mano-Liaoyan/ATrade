'use client';

import Link from 'next/link';
import { createSymbolChartHref, getTrendingSymbolIdentity } from '../lib/instrumentIdentity';
import type { WatchlistPinState } from '../lib/watchlistWorkflow';
import type { TrendingSymbol } from '../types/marketData';

type TrendingListProps = {
  symbols: TrendingSymbol[];
  getPinState: (symbol: TrendingSymbol) => WatchlistPinState;
  onTogglePin: (symbol: TrendingSymbol) => void;
  source?: string | null;
};

export function TrendingList({ symbols, getPinState, onTogglePin, source = null }: TrendingListProps) {
  return (
    <section className="workspace-panel" aria-labelledby="trending-title" data-testid="trending-list">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Backend-driven market data</p>
          <h2 id="trending-title">Trending stocks and ETFs</h2>
        </div>
        <span className="pill">{formatSourceLabel(source)}</span>
      </div>

      <div className="symbol-grid">
        {symbols.map((symbol) => {
          const identity = getTrendingSymbolIdentity(symbol);
          const chartHref = createSymbolChartHref(identity);
          const pinState = getPinState(symbol);

          return (
            <article className="symbol-card" key={pinState.pinKey}>
              <div className="symbol-card__topline">
                <div>
                  <Link className="symbol-link" href={chartHref}>
                    {symbol.symbol}
                  </Link>
                  <p>{symbol.name}</p>
                </div>
                <button
                  className={pinState.pinned ? 'pin-button pin-button--active' : 'pin-button'}
                  type="button"
                  aria-pressed={pinState.pinned}
                  disabled={pinState.disabled}
                  onClick={() => onTogglePin(symbol)}
                >
                  {pinState.saving ? (pinState.pinned ? 'Removing…' : 'Saving…') : pinState.pinned ? 'Pinned' : 'Pin'}
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

              <Link className="open-chart-link" href={chartHref}>
                Open chart workspace
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function formatSourceLabel(source: string | null): string {
  if (!source) {
    return 'IBKR market-data factors';
  }

  if (source.includes('scanner')) {
    return 'IBKR scanner factors';
  }

  return `IBKR source: ${source}`;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}
