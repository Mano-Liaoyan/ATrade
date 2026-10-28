<!-- Equity curves on one chart: one line point at the end of each bar. Times are UNIX timestamps (UTC).
     One curve is a backtest result. Two curves are a comparison (ComparisonView). The second curve is a dashed line
     in the Carbon interactive color, so the user can tell the curves apart without color. A legend names each curve.
     All colors are Carbon tokens of the current theme (docs/architecture.md section 13).
     Interruptions of a forward test are grey columns behind the curves, and a list names them as text.
     ChartFrame (foundation/chart_frame) gives the canvas container and the TradingView attribution. -->
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
  import { ChartFrame } from '#lib/foundation/chart_frame';
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

  const FIRST_CURVE_STYLE: CurveStyle = { colorVariable: '--cds-text-primary', lineStyle: LineStyle.Solid };
  const CURVE_STYLES: CurveStyle[] = [FIRST_CURVE_STYLE, { colorVariable: '--cds-interactive', lineStyle: LineStyle.Dashed }];
  const INTERRUPTION_COLOR_VARIABLE = '--cds-layer-accent-01';

  let chartContainer: HTMLDivElement | undefined = $state();
  // A series with the color token that it uses. A change of the color scheme reads each token again.
  type ColoredSeries = [ISeriesApi<'Line'> | ISeriesApi<'Histogram'>, string];

  function readContainerStyle(): CSSStyleDeclaration {
    return getComputedStyle(chartContainer ?? document.documentElement);
  }

  function readColor(variableName: string): string {
    return readContainerStyle().getPropertyValue(variableName).trim();
  }

  function convertToTimestamp(timeUtc: string): UTCTimestamp {
    return (Date.parse(timeUtc) / MILLISECONDS_PER_SECOND) as UTCTimestamp;
  }

  function readThemeOptions(): DeepPartial<ChartOptions> {
    const gridColor = readColor('--cds-border-subtle-01');
    return {
      layout: {
        background: { color: readColor('--cds-layer-01') },
        textColor: readColor('--cds-text-secondary'),
        // IBM Plex Sans from the Carbon reset.
        fontFamily: readContainerStyle().fontFamily,
      },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor },
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
      color: readColor(INTERRUPTION_COLOR_VARIABLE),
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
    return [[columnSeries, INTERRUPTION_COLOR_VARIABLE]];
  }

  function readCurveStyle(curveIndex: number): CurveStyle {
    return CURVE_STYLES[curveIndex % CURVE_STYLES.length] ?? FIRST_CURVE_STYLE;
  }

  $effect(() => {
    if (chartContainer === undefined) {
      return;
    }
    const themeOptions = readThemeOptions();
    const chart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true },
      grid: themeOptions.grid,
      rightPriceScale: themeOptions.rightPriceScale,
      timeScale: { ...themeOptions.timeScale, timeVisible: true, secondsVisible: false },
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

<ChartFrame {label} height="min(24rem, 50vh)" minHeight="12rem" bind:canvas={chartContainer}>
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
</ChartFrame>

<style>
  .legend,
  .interruptions {
    margin: var(--cds-spacing-03) 0 0;
    padding: 0;
    list-style: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-05);
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .legend-line {
    display: inline-block;
    inline-size: var(--cds-spacing-07);
    border-top: 2px solid;
  }

  .legend-line.dashed {
    border-top-style: dashed;
  }

  .interruption-mark {
    display: inline-block;
    inline-size: var(--cds-spacing-04);
    block-size: var(--cds-spacing-04);
    margin-inline-end: var(--cds-spacing-03);
    background: var(--cds-layer-accent-01);
    vertical-align: middle;
  }
</style>
