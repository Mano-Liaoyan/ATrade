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
    type HistogramData,
    type IChartApi,
    type ISeriesApi,
    type LineData,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import { ChartFrame, readChartColor, readChartThemeOptions } from '#lib/foundation/chart_frame';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import ChartLegend from './ChartLegend.svelte';
  import { convertToTimestamp, readCurveStyle } from './chart_series';
  import { findInterruptedTimes, type TimeInterval } from './interruption_marks';

  interface Props {
    curves: EquityCurve[];
    label: string;
    interruptions?: TimeInterval[];
  }

  const { curves, label, interruptions = [] }: Props = $props();

  // The grey columns fill the full chart height on their own hidden price scale.
  const INTERRUPTION_PRICE_SCALE_ID = 'interruptions';
  const INTERRUPTION_COLUMN_VALUE = 1;
  const INTERRUPTION_COLOR_VARIABLE = '--cds-layer-accent-01';

  let chartContainer: HTMLDivElement | undefined = $state();
  // A series with the color token that it uses. A change of the color scheme reads each token again.
  type ColoredSeries = [ISeriesApi<'Line'> | ISeriesApi<'Histogram'>, string];

  function addInterruptionColumns(chart: IChartApi): ColoredSeries[] {
    const interruptedTimes = findInterruptedTimes(
      curves.map((curve) => curve.points),
      interruptions,
    );
    if (interruptedTimes.length === 0) {
      return [];
    }
    const columnSeries = chart.addSeries(HistogramSeries, {
      color: readChartColor(chartContainer, INTERRUPTION_COLOR_VARIABLE),
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

  $effect(() => {
    if (chartContainer === undefined) {
      return;
    }
    const themeOptions = readChartThemeOptions(chartContainer);
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
        color: readChartColor(chartContainer, style.colorVariable),
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
      chart.applyOptions(readChartThemeOptions(chartContainer));
      for (const [series, colorVariable] of coloredSeries) {
        series.applyOptions({ color: readChartColor(chartContainer, colorVariable) });
      }
    });
    return () => {
      endColorSchemeWatch();
      chart.remove();
    };
  });
</script>

<ChartFrame {label} height="min(24rem, 50vh)" minHeight="12rem" bind:canvas={chartContainer}>
  <ChartLegend {label} curveNames={curves.map((curve) => curve.name)} {interruptions} />
</ChartFrame>
