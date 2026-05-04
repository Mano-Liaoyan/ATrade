'use client';

import { CHART_RANGE_DESCRIPTIONS, CHART_RANGE_LABELS, SUPPORTED_CHART_RANGES, type ChartRange } from '../types/marketData';

type TimeframeSelectorProps = {
  value: ChartRange;
  onChange: (chartRange: ChartRange) => void;
};

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className="timeframe-selector" aria-label="Chart range lookback controls" data-testid="chart-range-controls">
      <span className="timeframe-help" data-testid="chart-range-help">
        Lookback from now: 1D = past day, 1m = past month, 6m = past six months.
      </span>
      {SUPPORTED_CHART_RANGES.map((chartRange) => (
        <button
          aria-label={CHART_RANGE_DESCRIPTIONS[chartRange]}
          aria-pressed={chartRange === value}
          className={chartRange === value ? 'timeframe-button timeframe-button--active' : 'timeframe-button'}
          key={chartRange}
          title={CHART_RANGE_DESCRIPTIONS[chartRange]}
          type="button"
          onClick={() => onChange(chartRange)}
        >
          {CHART_RANGE_LABELS[chartRange]}
        </button>
      ))}
    </div>
  );
}
