'use client';

import type { IndicatorResponse } from '../types/marketData';

type IndicatorPanelProps = {
  indicators: IndicatorResponse | null;
};

export function IndicatorPanel({ indicators }: IndicatorPanelProps) {
  const latestMovingAverage = indicators?.movingAverages.at(-1);
  const latestRsi = indicators?.rsi.at(-1);
  const latestMacd = indicators?.macd.at(-1);

  return (
    <aside className="indicator-panel" aria-label="Moving average RSI and MACD indicator support" data-testid="indicator-panel">
      <div>
        <span className="indicator-label">SMA 20</span>
        <strong>{formatNumber(latestMovingAverage?.sma20)}</strong>
      </div>
      <div>
        <span className="indicator-label">SMA 50</span>
        <strong>{formatNumber(latestMovingAverage?.sma50)}</strong>
      </div>
      <div>
        <span className="indicator-label">RSI</span>
        <strong>{formatNumber(latestRsi?.value)}</strong>
      </div>
      <div>
        <span className="indicator-label">MACD</span>
        <strong>{formatNumber(latestMacd?.macd)}</strong>
        <small>Signal {formatNumber(latestMacd?.signal)} · Hist {formatNumber(latestMacd?.histogram)}</small>
      </div>
    </aside>
  );
}

function formatNumber(value: number | undefined): string {
  return typeof value === 'number' ? value.toFixed(2) : '—';
}
