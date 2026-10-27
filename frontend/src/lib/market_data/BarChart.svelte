<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo, and the text under the chart links to TradingView. -->
<script lang="ts">
  import {
    CandlestickSeries,
    createChart,
    type CandlestickData,
    type IChartApi,
    type ISeriesApi,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import type { Bar } from './bars';

  const { bars, label }: { bars: Bar[]; label: string } = $props();

  let chartContainer: HTMLDivElement;
  let chart: IChartApi | undefined = $state();
  let candlestickSeries: ISeriesApi<'Candlestick'> | undefined = $state();

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  $effect(() => {
    const createdChart = createChart(chartContainer, {
      autoSize: true,
      layout: {
        attributionLogo: true,
        background: { color: readColor('--color-surface') },
        textColor: readColor('--color-text'),
      },
      grid: {
        vertLines: { color: readColor('--color-border') },
        horzLines: { color: readColor('--color-border') },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    candlestickSeries = createdChart.addSeries(CandlestickSeries);
    chart = createdChart;
    return () => {
      createdChart.remove();
      chart = undefined;
      candlestickSeries = undefined;
    };
  });

  $effect(() => {
    if (chart === undefined || candlestickSeries === undefined) {
      return;
    }
    const candlesticks: CandlestickData<UTCTimestamp>[] = bars.map((bar) => ({
      time: bar.time as UTCTimestamp,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));
    candlestickSeries.setData(candlesticks);
    chart.timeScale().fitContent();
  });
</script>

<figure class="bar-chart">
  <div class="chart-canvas" role="img" aria-label={label} bind:this={chartContainer}></div>
  <figcaption class="chart-attribution">
    Chart by <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView</a>
    Lightweight Charts™
  </figcaption>
</figure>

<style>
  .bar-chart {
    margin: 0;
  }

  .chart-canvas {
    position: relative;
    height: min(32rem, 60vh);
    min-height: 16rem;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .chart-attribution {
    margin-top: 0.25rem;
    color: var(--color-muted);
    font-size: 0.75rem;
  }
</style>
