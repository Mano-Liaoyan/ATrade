'use client';

import { SUPPORTED_TIMEFRAMES, type Timeframe } from '../types/marketData';

type TimeframeSelectorProps = {
  value: Timeframe;
  onChange: (timeframe: Timeframe) => void;
};

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className="timeframe-selector" aria-label="Chart timeframe controls" data-testid="timeframe-controls">
      {SUPPORTED_TIMEFRAMES.map((timeframe) => (
        <button
          aria-pressed={timeframe === value}
          className={timeframe === value ? 'timeframe-button timeframe-button--active' : 'timeframe-button'}
          key={timeframe}
          type="button"
          onClick={() => onChange(timeframe)}
        >
          {timeframe}
        </button>
      ))}
    </div>
  );
}
