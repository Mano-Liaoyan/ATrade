'use client';

import {
  CandlestickData,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramData,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  LineData,
  LineSeries,
  Time,
  UTCTimestamp,
  createChart,
} from 'lightweight-charts';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { CandleSeriesResponse, IndicatorResponse, OhlcvCandle } from '../types/marketData';

type CandlestickChartProps = {
  candles: CandleSeriesResponse;
  indicators: IndicatorResponse | null;
};

type LegendSnapshot = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

export function CandlestickChart({ candles, indicators }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [legend, setLegend] = useState<LegendSnapshot | null>(() => toLegendSnapshot(candles.candles.at(-1)));

  const chartData = useMemo(
    () => candles.candles.map(toCandlestickData),
    [candles],
  );

  const volumeData = useMemo(
    () => candles.candles.map(toVolumeData),
    [candles],
  );

  const sma20Data = useMemo(
    () => indicators?.movingAverages.map((point) => ({ time: toChartTime(point.time), value: point.sma20 }) satisfies LineData<Time>) ?? [],
    [indicators],
  );

  const sma50Data = useMemo(
    () => indicators?.movingAverages.map((point) => ({ time: toChartTime(point.time), value: point.sma50 }) satisfies LineData<Time>) ?? [],
    [indicators],
  );

  useEffect(() => {
    setLegend(toLegendSnapshot(candles.candles.at(-1)));
  }, [candles]);

  useEffect(() => {
    if (!containerRef.current || chartData.length === 0) {
      return;
    }

    const chart: IChartApi = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#0f1b2e' },
        textColor: '#cbd5e1',
      },
      grid: {
        horzLines: { color: 'rgba(148, 163, 184, 0.14)' },
        vertLines: { color: 'rgba(148, 163, 184, 0.12)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: 'rgba(148, 163, 184, 0.24)',
      },
      timeScale: {
        borderColor: 'rgba(148, 163, 184, 0.24)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      borderUpColor: '#34d399',
      wickUpColor: '#34d399',
      downColor: '#fb7185',
      borderDownColor: '#fb7185',
      wickDownColor: '#fb7185',
    });
    candleSeries.setData(chartData);

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: 'rgba(56, 189, 248, 0.28)',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });
    volumeSeries.setData(volumeData);

    const sma20Series = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2, title: 'SMA 20' });
    sma20Series.setData(sma20Data);

    const sma50Series = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2, title: 'SMA 50' });
    sma50Series.setData(sma50Data);

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) {
        setLegend(toLegendSnapshot(candles.candles.at(-1)));
        return;
      }

      const seriesData = param.seriesData.get(candleSeries) as CandlestickData<Time> | undefined;
      if (!seriesData) {
        return;
      }

      setLegend({
        time: formatChartTime(seriesData.time),
        open: seriesData.open,
        high: seriesData.high,
        low: seriesData.low,
        close: seriesData.close,
      });
    });

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [candles, chartData, volumeData, sma20Data, sma50Data]);

  return (
    <div className="chart-shell" data-testid="candlestick-chart">
      <div className="chart-legend" aria-live="polite" data-testid="chart-legend">
        <strong>{candles.symbol}</strong>
        <span>{candles.timeframe}</span>
        {legend ? (
          <>
            <span>{legend.time}</span>
            <span>O {legend.open.toFixed(2)}</span>
            <span>H {legend.high.toFixed(2)}</span>
            <span>L {legend.low.toFixed(2)}</span>
            <span>C {legend.close.toFixed(2)}</span>
          </>
        ) : null}
      </div>
      <div className="chart-container" ref={containerRef} />
      <p className="chart-help">Mouse wheel / pinch to zoom, drag to pan, and move the crosshair for OHLC legend values.</p>
    </div>
  );
}

function toCandlestickData(candle: OhlcvCandle): CandlestickData<Time> {
  return {
    time: toChartTime(candle.time),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };
}

function toVolumeData(candle: OhlcvCandle): HistogramData<Time> {
  return {
    time: toChartTime(candle.time),
    value: candle.volume,
    color: candle.close >= candle.open ? 'rgba(52, 211, 153, 0.28)' : 'rgba(251, 113, 133, 0.28)',
  };
}

function toChartTime(value: string): UTCTimestamp {
  return Math.floor(Date.parse(value) / 1000) as UTCTimestamp;
}

function toLegendSnapshot(candle: OhlcvCandle | undefined): LegendSnapshot | null {
  if (!candle) {
    return null;
  }

  return {
    time: formatChartTime(toChartTime(candle.time)),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };
}

function formatChartTime(time: Time): string {
  if (typeof time === 'number') {
    return new Date(time * 1000).toISOString().replace('T', ' ').slice(0, 16);
  }

  if (typeof time === 'string') {
    return time;
  }

  return `${time.year}-${String(time.month).padStart(2, '0')}-${String(time.day).padStart(2, '0')}`;
}
