'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getCandles, getIndicators } from './marketDataClient';
import { normalizeInstrumentIdentity, type InstrumentIdentityInput, type NormalizedInstrumentIdentity } from './instrumentIdentity';
import { connectMarketDataStream, type MarketDataStreamState, type MarketDataStreamSubscription } from './marketDataStream';
import type { CandleSeriesResponse, IndicatorResponse, MarketDataUpdate, OhlcvCandle, Timeframe } from '../types/marketData';

export const ChartPollingFallbackMs = 15_000;

export type SymbolChartWorkflowOptions = {
  symbol: string;
  identity?: InstrumentIdentityInput | null;
  initialTimeframe?: Timeframe;
  pollingFallbackMs?: number;
};

export type SymbolChartWorkflow = {
  normalizedSymbol: string;
  chartIdentity: NormalizedInstrumentIdentity | null;
  timeframe: Timeframe;
  setTimeframe: (timeframe: Timeframe) => void;
  candles: CandleSeriesResponse | null;
  indicators: IndicatorResponse | null;
  latestUpdate: MarketDataUpdate | null;
  streamState: MarketDataStreamState;
  loading: boolean;
  error: string | null;
  refreshChartData: (showLoading?: boolean) => Promise<void>;
};

export function useSymbolChartWorkflow({
  symbol,
  identity = null,
  initialTimeframe = '1D',
  pollingFallbackMs = ChartPollingFallbackMs,
}: SymbolChartWorkflowOptions): SymbolChartWorkflow {
  const normalizedSymbol = symbol.toUpperCase();
  const chartIdentity = useMemo(
    () => (identity ? normalizeInstrumentIdentity({ ...identity, symbol: normalizedSymbol }) : null),
    [identity, normalizedSymbol],
  );
  const [timeframe, setTimeframe] = useState<Timeframe>(initialTimeframe);
  const [candles, setCandles] = useState<CandleSeriesResponse | null>(null);
  const [indicators, setIndicators] = useState<IndicatorResponse | null>(null);
  const [latestUpdate, setLatestUpdate] = useState<MarketDataUpdate | null>(null);
  const [streamState, setStreamState] = useState<MarketDataStreamState>('connecting');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshChartData = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);

    try {
      const [candleResponse, indicatorResponse] = await Promise.all([
        getCandles(normalizedSymbol, timeframe, chartIdentity),
        getIndicators(normalizedSymbol, timeframe, chartIdentity),
      ]);
      setCandles(candleResponse);
      setIndicators(indicatorResponse);
    } catch (caughtError) {
      setError(formatChartDataWorkflowError(caughtError));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, [chartIdentity, normalizedSymbol, timeframe]);

  useEffect(() => {
    void refreshChartData(true);
  }, [refreshChartData]);

  useEffect(() => {
    let active = true;
    let subscription: MarketDataStreamSubscription | null = null;
    let fallbackTimer: number | undefined;

    const stopPollingFallback = () => {
      if (fallbackTimer !== undefined) {
        window.clearInterval(fallbackTimer);
        fallbackTimer = undefined;
      }
    };

    const startPollingFallback = () => {
      if (!active || fallbackTimer !== undefined) {
        return;
      }

      fallbackTimer = window.setInterval(() => void refreshChartData(false), pollingFallbackMs);
    };

    async function startStream() {
      try {
        subscription = await connectMarketDataStream({
          symbol: normalizedSymbol,
          timeframe,
          onStateChange: (state) => {
            if (!active) {
              return;
            }

            setStreamState(state);
            if (state === 'connected') {
              stopPollingFallback();
            } else if (state === 'closed' || state === 'unavailable') {
              startPollingFallback();
            }
          },
          onUpdate: (update) => {
            if (!active) {
              return;
            }

            setLatestUpdate(update);
            setCandles((current) => applyMarketDataUpdate(current, update));
          },
        });
      } catch {
        if (!active) {
          return;
        }

        setStreamState('unavailable');
        startPollingFallback();
      }
    }

    void startStream();

    return () => {
      active = false;
      stopPollingFallback();
      if (subscription) {
        void subscription.stop();
      }
    };
  }, [normalizedSymbol, pollingFallbackMs, timeframe, refreshChartData]);

  return {
    normalizedSymbol,
    chartIdentity,
    timeframe,
    setTimeframe,
    candles,
    indicators,
    latestUpdate,
    streamState,
    loading,
    error,
    refreshChartData,
  };
}

export function formatChartDataWorkflowError(caughtError: unknown): string {
  return caughtError instanceof Error ? caughtError.message : 'IBKR chart data is unavailable.';
}

export function formatMarketDataSourceLabel(source: string | null | undefined): string {
  if (!source) {
    return 'IBKR/iBeam';
  }

  if (source.includes('ibkr')) {
    return 'IBKR/iBeam';
  }

  return source;
}

function applyMarketDataUpdate(current: CandleSeriesResponse | null, update: MarketDataUpdate): CandleSeriesResponse | null {
  if (!current || current.symbol !== update.symbol || current.timeframe !== update.timeframe) {
    return current;
  }

  const updatedCandle: OhlcvCandle = {
    time: update.time,
    open: update.open,
    high: update.high,
    low: update.low,
    close: update.close,
    volume: update.volume,
  };

  const candleIndex = current.candles.findIndex((candle) => candle.time === update.time);
  const candles = [...current.candles];
  if (candleIndex >= 0) {
    candles[candleIndex] = updatedCandle;
  } else {
    candles.push(updatedCandle);
  }

  return {
    ...current,
    candles: candles.slice(-240),
  };
}
