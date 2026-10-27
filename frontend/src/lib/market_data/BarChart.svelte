<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).
     A live bar replaces the last candlestick or adds one after it (series.update), without a new fit of the view.

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo, and the text under the chart links to TradingView. -->
<script lang="ts">
  import {
    CandlestickSeries,
    createChart,
    type CandlestickData,
    type ChartOptions,
    type DeepPartial,
    type IChartApi,
    type ISeriesApi,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import { untrack } from 'svelte';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import type { Bar } from './bars';
  import { canDrawLiveBar } from './live_bars';

  const { bars, liveBar = null, label }: { bars: Bar[]; liveBar?: Bar | null; label: string } = $props();

  let chartContainer: HTMLDivElement;
  let chart: IChartApi | undefined = $state();
  let candlestickSeries: ISeriesApi<'Candlestick'> | undefined = $state();

  function toCandlestick(bar: Bar): CandlestickData<UTCTimestamp> {
    return { time: bar.time as UTCTimestamp, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
  }

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  // The colors of the light or the dark tokens. A change of the color scheme applies them again, without a new chart.
  function readThemeOptions(): DeepPartial<ChartOptions> {
    return {
      layout: {
        background: { color: readColor('--color-surface') },
        textColor: readColor('--color-text'),
      },
      grid: {
        vertLines: { color: readColor('--color-border') },
        horzLines: { color: readColor('--color-border') },
      },
    };
  }

  $effect(() => {
    const themeOptions = readThemeOptions();
    const createdChart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true },
      grid: themeOptions.grid,
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    candlestickSeries = createdChart.addSeries(CandlestickSeries);
    chart = createdChart;
    const endColorSchemeWatch = watchColorScheme(() => {
      createdChart.applyOptions(readThemeOptions());
    });
    return () => {
      endColorSchemeWatch();
      createdChart.remove();
      chart = undefined;
      candlestickSeries = undefined;
    };
  });

  $effect(() => {
    if (chart === undefined || candlestickSeries === undefined) {
      return;
    }
    candlestickSeries.setData(bars.map(toCandlestick));
    chart.timeScale().fitContent();
    // The live bar that came before the bars is drawn again. A new live bar does not run this effect.
    const currentLiveBar = untrack(() => liveBar);
    if (currentLiveBar !== null && canDrawLiveBar(bars, currentLiveBar)) {
      candlestickSeries.update(toCandlestick(currentLiveBar));
    }
  });

  $effect(() => {
    if (candlestickSeries === undefined || liveBar === null) {
      return;
    }
    if (canDrawLiveBar(untrack(() => bars), liveBar)) {
      candlestickSeries.update(toCandlestick(liveBar));
    }
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
