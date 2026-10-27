<!-- Equity curves on one chart: one line point at the end of each bar. Times are UNIX timestamps (UTC).
     One curve is a backtest result. Two curves are a comparison (ComparisonView). The second curve is a dashed line
     in the accent color, so the user can tell the curves apart without color. A legend names each curve.

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo, and the text under the chart links to TradingView. -->
<script module lang="ts">
  import type { EquityPoint } from './backtest_api';

  export interface EquityCurve {
    name: string;
    points: EquityPoint[];
  }
</script>

<script lang="ts">
  import { createChart, LineSeries, LineStyle, type LineData, type UTCTimestamp } from 'lightweight-charts';

  const { curves, label }: { curves: EquityCurve[]; label: string } = $props();

  const MILLISECONDS_PER_SECOND = 1000;
  interface CurveStyle {
    colorVariable: string;
    lineStyle: LineStyle;
  }

  const FIRST_CURVE_STYLE: CurveStyle = { colorVariable: '--color-text', lineStyle: LineStyle.Solid };
  const CURVE_STYLES: CurveStyle[] = [FIRST_CURVE_STYLE, { colorVariable: '--color-accent', lineStyle: LineStyle.Dashed }];

  let chartContainer: HTMLDivElement;

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  function readCurveStyle(curveIndex: number): CurveStyle {
    return CURVE_STYLES[curveIndex % CURVE_STYLES.length] ?? FIRST_CURVE_STYLE;
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
    curves.forEach((curve, curveIndex) => {
      const style = readCurveStyle(curveIndex);
      const lineSeries = chart.addSeries(LineSeries, {
        color: readColor(style.colorVariable),
        lineStyle: style.lineStyle,
        title: curve.name,
      });
      const linePoints: LineData<UTCTimestamp>[] = curve.points.map((point) => ({
        time: (Date.parse(point.time_utc) / MILLISECONDS_PER_SECOND) as UTCTimestamp,
        value: Number(point.equity_usd),
      }));
      lineSeries.setData(linePoints);
    });
    chart.timeScale().fitContent();
    return () => {
      chart.remove();
    };
  });
</script>

<figure class="equity-chart">
  <div class="chart-canvas" role="img" aria-label={label} bind:this={chartContainer}></div>
  {#if curves.length > 1}
    <ul class="legend" aria-label={`${label} legend`}>
      {#each curves as curve, curveIndex (curveIndex)}
        <li>
          <span
            class="legend-line"
            class:dashed={readCurveStyle(curveIndex).lineStyle === LineStyle.Dashed}
            style:border-color={`var(${readCurveStyle(curveIndex).colorVariable})`}
          ></span>
          {curve.name}
        </li>
      {/each}
    </ul>
  {/if}
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

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
    font-size: 0.875rem;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 0.375rem;
  }

  .legend-line {
    display: inline-block;
    inline-size: 1.5rem;
    border-top: 2px solid;
  }

  .legend-line.dashed {
    border-top-style: dashed;
  }

  .chart-attribution {
    margin-top: 0.25rem;
    color: var(--color-muted);
    font-size: 0.75rem;
  }
</style>
