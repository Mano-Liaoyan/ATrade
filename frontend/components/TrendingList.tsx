'use client';

import Link from 'next/link';
import { createWatchlistInstrumentKey, normalizeWatchlistAssetClass } from '../lib/watchlistClient';
import type { TrendingSymbol } from '../types/marketData';

type TrendingListProps = {
  symbols: TrendingSymbol[];
  pinnedInstrumentKeys: string[];
  onTogglePin: (symbol: TrendingSymbol) => void;
  actionsDisabled?: boolean;
  savingPinKey?: string | null;
  source?: string | null;
};

export function TrendingList({ symbols, pinnedInstrumentKeys, onTogglePin, actionsDisabled = false, savingPinKey = null, source = null }: TrendingListProps) {
  const pinnedSet = new Set(pinnedInstrumentKeys);

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
          const pinKey = createTrendingPinKey(symbol);
          const pinned = pinnedSet.has(pinKey);
          const isSaving = savingPinKey === pinKey;

          return (
            <article className="symbol-card" key={pinKey}>
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

function createTrendingPinKey(symbol: TrendingSymbol): string {
  return createWatchlistInstrumentKey({
    symbol: symbol.symbol,
    provider: 'ibkr',
    exchange: symbol.exchange,
    currency: 'USD',
    assetClass: normalizeWatchlistAssetClass(symbol.assetClass),
  });
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
