<!-- Equity curves on one chart: one line point at the end of each bar. Times are UNIX timestamps (UTC).
     One curve is a backtest result. Two curves are a comparison (ComparisonView). The second curve is a dashed line
     in the accent color, so the user can tell the curves apart without color. A legend names each curve.
     Interruptions of a forward test are grey columns behind the curves, and a list names them as text.

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
  import {
    createChart,
    HistogramSeries,
    LineSeries,
    LineStyle,
    type ChartOptions,
    type DeepPartial,
    type HistogramData,
    type IChartApi,
    type ISeriesApi,
    type LineData,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { findInterruptedTimes, type TimeInterval } from './interruption_marks';

  interface Props {
    curves: EquityCurve[];
    label: string;
    interruptions?: TimeInterval[];
  }

  const { curves, label, interruptions = [] }: Props = $props();

  const MILLISECONDS_PER_SECOND = 1000;
  // The grey columns fill the full chart height on their own hidden price scale.
  const INTERRUPTION_PRICE_SCALE_ID = 'interruptions';
  const INTERRUPTION_COLUMN_VALUE = 1;
  interface CurveStyle {
    colorVariable: string;
    lineStyle: LineStyle;
  }

  const FIRST_CURVE_STYLE: CurveStyle = { colorVariable: '--color-text', lineStyle: LineStyle.Solid };
  const CURVE_STYLES: CurveStyle[] = [FIRST_CURVE_STYLE, { colorVariable: '--color-accent', lineStyle: LineStyle.Dashed }];

  let chartContainer: HTMLDivElement;
  // A series with the color token that it uses. A change of the color scheme reads each token again.
  type ColoredSeries = [ISeriesApi<'Line'> | ISeriesApi<'Histogram'>, string];

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  function convertToTimestamp(timeUtc: string): UTCTimestamp {
    return (Date.parse(timeUtc) / MILLISECONDS_PER_SECOND) as UTCTimestamp;
  }

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

  function addInterruptionColumns(chart: IChartApi): ColoredSeries[] {
    const interruptedTimes = findInterruptedTimes(
      curves.map((curve) => curve.points),
      interruptions,
    );
    if (interruptedTimes.length === 0) {
      return [];
    }
    const columnSeries = chart.addSeries(HistogramSeries, {
      color: readColor('--color-border'),
      priceScaleId: INTERRUPTION_PRICE_SCALE_ID,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale(INTERRUPTION_PRICE_SCALE_ID).applyOptions({ visible: false, scaleMargins: { top: 0, bottom: 0 } });
    const columns: HistogramData<UTCTimestamp>[] = interruptedTimes.map((timeUtc) => ({
      time: convertToTimestamp(timeUtc),
      value: INTERRUPTION_COLUMN_VALUE,
    }));
    columnSeries.setData(columns);
    return [[columnSeries, '--color-border']];
  }

  function readCurveStyle(curveIndex: number): CurveStyle {
    return CURVE_STYLES[curveIndex % CURVE_STYLES.length] ?? FIRST_CURVE_STYLE;
  }

  $effect(() => {
    const themeOptions = readThemeOptions();
    const chart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true },
      grid: themeOptions.grid,
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    // Added first, so the curves are drawn on top of the grey columns.
    const coloredSeries = addInterruptionColumns(chart);
    curves.forEach((curve, curveIndex) => {
      const style = readCurveStyle(curveIndex);
      const lineSeries = chart.addSeries(LineSeries, {
        color: readColor(style.colorVariable),
        lineStyle: style.lineStyle,
        title: curve.name,
      });
      const linePoints: LineData<UTCTimestamp>[] = curve.points.map((point) => ({
        time: convertToTimestamp(point.time_utc),
        value: Number(point.equity_usd),
      }));
      lineSeries.setData(linePoints);
      coloredSeries.push([lineSeries, style.colorVariable]);
    });
    chart.timeScale().fitContent();
    const endColorSchemeWatch = watchColorScheme(() => {
      chart.applyOptions(readThemeOptions());
      for (const [series, colorVariable] of coloredSeries) {
        series.applyOptions({ color: readColor(colorVariable) });
      }
    });
    return () => {
      endColorSchemeWatch();
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
  {#if interruptions.length > 0}
    <ul class="interruptions" aria-label={`${label} interruptions`}>
      {#each interruptions as interruption (interruption.start_utc)}
        <li>
          <span class="interruption-mark"></span>
          Interrupted from {formatUtcTime(interruption.start_utc)} to {formatUtcTime(interruption.end_utc)}
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

  .interruptions {
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
    font-size: 0.875rem;
  }

  .interruption-mark {
    display: inline-block;
    inline-size: 0.75rem;
    block-size: 0.75rem;
    margin-inline-end: 0.375rem;
    background: var(--color-border);
    vertical-align: middle;
  }

  .chart-attribution {
    margin-top: 0.25rem;
    color: var(--color-muted);
    font-size: 0.75rem;
  }
</style>
