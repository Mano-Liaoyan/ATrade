<!-- Equity curve: one line point at the end of each bar. Times are UNIX timestamps (UTC).

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo, and the text under the chart links to TradingView. -->
<script lang="ts">
  import { createChart, LineSeries, type LineData, type UTCTimestamp } from 'lightweight-charts';
  import type { EquityPoint } from './backtest_api';

  const { equityCurve, label }: { equityCurve: EquityPoint[]; label: string } = $props();

  const MILLISECONDS_PER_SECOND = 1000;

  let chartContainer: HTMLDivElement;

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  $effect(() => {
    const chart = createChart(chartContainer, {
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
    const lineSeries = chart.addSeries(LineSeries, { color: readColor('--color-text') });
    const linePoints: LineData<UTCTimestamp>[] = equityCurve.map((point) => ({
      time: (Date.parse(point.time_utc) / MILLISECONDS_PER_SECOND) as UTCTimestamp,
      value: Number(point.equity_usd),
    }));
    lineSeries.setData(linePoints);
    chart.timeScale().fitContent();
    return () => {
      chart.remove();
    };
  });
</script>

<figure class="equity-chart">
  <div class="chart-canvas" role="img" aria-label={label} bind:this={chartContainer}></div>
  <figcaption class="chart-attribution">
    Chart by <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView</a>
    Lightweight Charts™
  </figcaption>
</figure>

<style>
  .equity-chart {
    margin: 0;
  }

  .chart-canvas {
    position: relative;
    height: min(24rem, 50vh);
    min-height: 12rem;
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
