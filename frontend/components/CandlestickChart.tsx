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
  type MouseEventParams,
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

const FallbackChartWidth = 640;
const MinimumChartWidth = 1;
const MinimumChartHeight = 420;
const FallbackChartHeight = 440;

const ChartColors = {
  background: '#090806',
  text: '#e9e4d8',
  grid: 'rgba(126, 118, 102, 0.2)',
  axis: 'rgba(126, 118, 102, 0.34)',
  up: '#36bf73',
  down: '#e35d6a',
  upVolume: 'rgba(54, 191, 115, 0.28)',
  downVolume: 'rgba(227, 93, 106, 0.28)',
  neutralVolume: 'rgba(196, 124, 28, 0.28)',
  smaFast: '#ee9f22',
  smaSlow: '#9aa8ba',
} as const;

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
    const container = containerRef.current;
    if (!container || chartData.length === 0) {
      return;
    }

    const initialSize = measureChartContainer(container);
    const chart: IChartApi = createChart(container, {
      autoSize: false,
      width: initialSize.width,
      height: initialSize.height,
      layout: {
        background: { type: ColorType.Solid, color: ChartColors.background },
        textColor: ChartColors.text,
      },
      grid: {
        horzLines: { color: ChartColors.grid },
        vertLines: { color: ChartColors.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: ChartColors.axis,
      },
      timeScale: {
        borderColor: ChartColors.axis,
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

    const resizeAndFitChart = () => {
      const nextSize = measureChartContainer(container);
      chart.resize(nextSize.width, nextSize.height, true);
      chart.timeScale().fitContent();
    };

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: ChartColors.up,
      borderUpColor: ChartColors.up,
      wickUpColor: ChartColors.up,
      downColor: ChartColors.down,
      borderDownColor: ChartColors.down,
      wickDownColor: ChartColors.down,
    });
    candleSeries.setData(chartData);

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: ChartColors.neutralVolume,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });
    volumeSeries.setData(volumeData);

    const sma20Series = chart.addSeries(LineSeries, { color: ChartColors.smaFast, lineWidth: 2, title: 'SMA 20' });
    sma20Series.setData(sma20Data);

    const sma50Series = chart.addSeries(LineSeries, { color: ChartColors.smaSlow, lineWidth: 2, title: 'SMA 50' });
    sma50Series.setData(sma50Data);

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
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
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);

    let resizeAnimationFrame: number | null = null;
    const scheduleResizeAndFit = () => {
      if (resizeAnimationFrame !== null) {
        window.cancelAnimationFrame(resizeAnimationFrame);
      }

      resizeAnimationFrame = window.requestAnimationFrame(() => {
        resizeAnimationFrame = null;
        resizeAndFitChart();
      });
    };

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(scheduleResizeAndFit);
      resizeObserver.observe(container);
    }

    window.addEventListener('resize', scheduleResizeAndFit);
    chart.timeScale().fitContent();
    scheduleResizeAndFit();

    return () => {
      if (resizeAnimationFrame !== null) {
        window.cancelAnimationFrame(resizeAnimationFrame);
      }
      resizeObserver?.disconnect();
      window.removeEventListener('resize', scheduleResizeAndFit);
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
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

function measureChartContainer(container: HTMLDivElement): { width: number; height: number } {
  const bounds = container.getBoundingClientRect();
  const parentBounds = container.parentElement?.getBoundingClientRect();
  const width = Math.floor(bounds.width || container.clientWidth || parentBounds?.width || FallbackChartWidth);
  const height = Math.floor(bounds.height || container.clientHeight || FallbackChartHeight);

  return {
    width: Math.max(MinimumChartWidth, width),
    height: Math.max(MinimumChartHeight, height),
  };
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
    color: candle.close >= candle.open ? ChartColors.upVolume : ChartColors.downVolume,
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
