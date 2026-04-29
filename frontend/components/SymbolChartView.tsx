'use client';

import { useCallback, useEffect, useState } from 'react';
import { getCandles, getIndicators } from '../lib/marketDataClient';
import { connectMarketDataStream, type MarketDataStreamState, type MarketDataStreamSubscription } from '../lib/marketDataStream';
import type { CandleSeriesResponse, IndicatorResponse, MarketDataUpdate, OhlcvCandle, Timeframe } from '../types/marketData';
import { BrokerPaperStatus } from './BrokerPaperStatus';
import { CandlestickChart } from './CandlestickChart';
import { IndicatorPanel } from './IndicatorPanel';
import { TimeframeSelector } from './TimeframeSelector';

type SymbolChartViewProps = {
  symbol: string;
};

export function SymbolChartView({ symbol }: SymbolChartViewProps) {
  const normalizedSymbol = symbol.toUpperCase();
  const [timeframe, setTimeframe] = useState<Timeframe>('1D');
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
        getCandles(normalizedSymbol, timeframe),
        getIndicators(normalizedSymbol, timeframe),
      ]);
      setCandles(candleResponse);
      setIndicators(indicatorResponse);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'IBKR chart data is unavailable.');
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, [normalizedSymbol, timeframe]);

  useEffect(() => {
    void refreshChartData(true);
  }, [refreshChartData]);

  useEffect(() => {
    let active = true;
    let subscription: MarketDataStreamSubscription | null = null;
    let fallbackTimer: number | undefined;

    async function startStream() {
      try {
        subscription = await connectMarketDataStream({
          symbol: normalizedSymbol,
          timeframe,
          onStateChange: (state) => {
            if (active) {
              setStreamState(state);
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
        fallbackTimer = window.setInterval(() => void refreshChartData(false), 15_000);
      }
    }

    void startStream();

    return () => {
      active = false;
      if (fallbackTimer !== undefined) {
        window.clearInterval(fallbackTimer);
      }
      if (subscription) {
        void subscription.stop();
      }
    };
  }, [normalizedSymbol, timeframe, refreshChartData]);

  return (
    <div className="symbol-chart-layout">
      <section className="workspace-panel chart-view" data-testid="chart-workspace">
        <div className="panel-heading chart-heading">
          <div>
            <p className="eyebrow">Interactive candlestick chart</p>
            <h1>{normalizedSymbol} chart workspace</h1>
          </div>
          <div className="chart-actions">
            <span className={streamState === 'connected' ? 'stream-pill stream-pill--connected' : 'stream-pill'} data-testid="stream-state">
              SignalR {streamState}
            </span>
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
          </div>
        </div>

        {loading ? <div className="loading-state" role="status">Loading OHLC candlestick chart data…</div> : null}
        {!loading && error ? (
          <div className="error-state" role="alert">
            <strong>IBKR chart data unavailable.</strong>
            <p>{error}</p>
            <button className="primary-button" type="button" onClick={() => void refreshChartData(true)}>
              Retry chart data
            </button>
          </div>
        ) : null}
        {!loading && !error && candles ? <CandlestickChart candles={candles} indicators={indicators} /> : null}

        <IndicatorPanel indicators={indicators} />

        <div className="chart-footer-note">
          <p>
            HTTP candles/indicators are refreshed from IBKR/iBeam on demand. SignalR applies IBKR snapshot updates when `/hubs/market-data` is reachable;
            if streaming is unavailable this view falls back to HTTP polling without synthetic fallback data.
          </p>
          {candles ? (
            <p>Current candle source: {formatSourceLabel(candles.source)}.</p>
          ) : null}
          {streamState === 'unavailable' ? (
            <p>Streaming snapshots are unavailable; polling continues against the IBKR/iBeam HTTP provider.</p>
          ) : null}
          {latestUpdate ? (
            <p>
              Last market-data stream update: {latestUpdate.symbol} {latestUpdate.timeframe} close {latestUpdate.close.toFixed(2)} from {formatSourceLabel(latestUpdate.source)}.
            </p>
          ) : null}
        </div>
      </section>

      <BrokerPaperStatus />
    </div>
  );
}

function formatSourceLabel(source: string): string {
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
