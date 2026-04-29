'use client';

import Link from 'next/link';
import type { TrendingSymbol } from '../types/marketData';

type WatchlistProps = {
  symbols: string[];
  trendingSymbols: TrendingSymbol[];
  onRemove: (symbol: string) => void;
};

export function Watchlist({ symbols, trendingSymbols, onRemove }: WatchlistProps) {
  const bySymbol = new Map(trendingSymbols.map((symbol) => [symbol.symbol, symbol]));

  return (
    <section className="workspace-panel watchlist-panel" aria-labelledby="watchlist-title" data-testid="watchlist-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Local browser preference</p>
          <h2 id="watchlist-title">Personal watchlist</h2>
        </div>
        <span className="pill">localStorage</span>
      </div>

      {symbols.length === 0 ? (
        <div className="empty-state">
          <strong>No pinned symbols yet.</strong>
          <p>Pin a trending stock or ETF to keep it in this browser's MVP watchlist.</p>
        </div>
      ) : (
        <ul className="watchlist">
          {symbols.map((symbol) => {
            const details = bySymbol.get(symbol);

            return (
              <li key={symbol}>
                <div>
                  <Link className="symbol-link" href={`/symbols/${encodeURIComponent(symbol)}`}>
                    {symbol}
                  </Link>
                  <p>{details?.name ?? 'Pinned symbol'}</p>
                </div>
                <button className="text-button" type="button" onClick={() => onRemove(symbol)}>
                  Remove
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
