<!-- The equity curves of backtests or forward tests and, under them, their drawdown curves (computeDrawdownCurve), on one
     lightweight-charts chart with 2 panes. The panes share one time scale, so the curves zoom and scroll together and
     their times stay aligned (spec #99, like QuantConnect). The drawdown is a negative percent, the same sign as the max
     drawdown metric (formatMaxDrawdown). It is for the backtest page and, later, for the forward test page and the
     comparison pages:
     - `curves`: one curve, or 2 curves of a comparison. The second curve is dashed in the Carbon interactive color, and a
       page names the curves with their line styles (ComparedKeyMetrics): the chart has no legend.
     - `interruptions`: grey columns behind the equity curves and a list under the chart (forward tests).
     - New points of the same curves (a live forward test) do not reset the zoom. The chart fits all points only when it
       gets other curves (another name or another first time).
     With `fill`, the chart fills its parent and follows each size change (autoSize).
     All colors are Carbon tokens: the curve colors of readCurveStyle (equity), --cds-support-error (drawdown lines, and
     the fill of the first drawdown with alpha), --cds-layer-accent-01 (interruptions), and the theme colors of
     readChartThemeOptions. ChartFrame gives the canvas container and the TradingView attribution. -->
<script module lang="ts">
  import type { EquityPoint } from './backtest_api';

  /** One equity curve with the start capital, which is the first highest equity of its drawdown curve. */
  export interface DrawdownCurve {
    name: string;
    points: readonly EquityPoint[];
    /** The paper capital of a backtest or the start balance of a forward test. Null when not known. */
    startCapitalUsd: string | null;
  }
</script>

<script lang="ts">
  import {
    AreaSeries,
    createChart,
    HistogramSeries,
    LineSeries,
    type IChartApi,
    type ISeriesApi,
    type SeriesType,
  } from 'lightweight-charts';
  import { ChartFrame, readChartColor, readChartThemeOptions } from '#lib/foundation/chart_frame';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import InterruptionList from './InterruptionList.svelte';
  import { convertToTimestamp, readCurveStyle } from './chart_series';
  import { computeDrawdownCurve } from './drawdown_curve';
  import { findInterruptedTimes, type TimeInterval } from './interruption_marks';

  interface Props {
    curves: readonly DrawdownCurve[];
    label: string;
    interruptions?: readonly TimeInterval[];
    fill?: boolean;
  }

  const { curves, label, interruptions = [], fill = false }: Props = $props();

  const EQUITY_PANE_STRETCH = 3;
  const DRAWDOWN_PANE_STRETCH = 1;
  const EQUITY_PANE_INDEX = 0;
  const DRAWDOWN_PANE_INDEX = 1;
  // The grey columns fill the full equity pane height on their own hidden price scale.
  const INTERRUPTION_PRICE_SCALE_ID = 'interruptions';
  const INTERRUPTION_COLUMN_VALUE = 1;
  const INTERRUPTION_COLOR_VARIABLE = '--cds-layer-accent-01';
  const DRAWDOWN_COLOR_VARIABLE = '--cds-support-error';
  // The drawdown fill is the drawdown line color with this alpha (hex), so it stays a Carbon token color.
  const FILL_ALPHA_HEX = '33';
  const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i;
  // The drawdown axis shows a percent, like the max drawdown tile.
  const PERCENT_FORMAT = { type: 'percent', precision: 2, minMove: 0.01 } as const;
  // Each curve has 2 series: equity (even index) and drawdown (odd index).
  const SERIES_PER_CURVE = 2;

  let chartContainer: HTMLDivElement | undefined = $state();
  let chart: IChartApi | undefined = $state();
  // The series of the shown curves, and the curves that the last fit of the time scale had.
  let curveSeries: ISeriesApi<SeriesType>[] = [];
  let interruptionSeries: ISeriesApi<'Histogram'> | undefined;
  let fittedCurvesKey = '';

  function readDrawdownOptions(curveIndex: number): Record<string, string> {
    const lineColor = readChartColor(chartContainer, DRAWDOWN_COLOR_VARIABLE);
    if (curveIndex > 0) {
      return { color: lineColor };
    }
    const fillColor = HEX_COLOR_PATTERN.test(lineColor) ? `${lineColor}${FILL_ALPHA_HEX}` : lineColor;
    return { lineColor, topColor: fillColor, bottomColor: fillColor };
  }

  function readPaneOptions(): { separatorColor: string } {
    return { separatorColor: readChartColor(chartContainer, '--cds-border-subtle-01') };
  }

  // The other curves fit the time scale again: another count, another name, or another first time.
  function readCurvesKey(shownCurves: readonly DrawdownCurve[]): string {
    return shownCurves.map((curve) => `${curve.name}@${curve.points[0]?.time_utc ?? ''}`).join('|');
  }

  function applyColors(): void {
    const options = readChartThemeOptions(chartContainer);
    chart?.applyOptions({ ...options, layout: { ...options.layout, panes: readPaneOptions() } });
    interruptionSeries?.applyOptions({ color: readChartColor(chartContainer, INTERRUPTION_COLOR_VARIABLE) });
    curveSeries.forEach((series, seriesIndex) => {
      const curveIndex = Math.floor(seriesIndex / SERIES_PER_CURVE);
      series.applyOptions(
        seriesIndex % SERIES_PER_CURVE === 0
          ? { color: readChartColor(chartContainer, readCurveStyle(curveIndex).colorVariable) }
          : readDrawdownOptions(curveIndex),
      );
    });
  }

  // Each curve has an equity series (even index) and a drawdown series (odd index).
  function addCurveSeries(createdChart: IChartApi, curveIndex: number): ISeriesApi<SeriesType>[] {
    const style = readCurveStyle(curveIndex);
    const equitySeries = createdChart.addSeries(
      LineSeries,
      {
        color: readChartColor(chartContainer, style.colorVariable),
        lineStyle: style.lineStyle,
        lineWidth: 2,
        title: curves.length > 1 ? '' : 'Equity',
        priceLineVisible: false,
      },
      EQUITY_PANE_INDEX,
    );
    const drawdownSeries =
      curveIndex === 0
        ? createdChart.addSeries(
            AreaSeries,
            {
              ...readDrawdownOptions(0),
              invertFilledArea: true,
              lineWidth: 1,
              title: curves.length > 1 ? '' : 'Drawdown',
              priceLineVisible: false,
              priceFormat: PERCENT_FORMAT,
            },
            DRAWDOWN_PANE_INDEX,
          )
        : createdChart.addSeries(
            LineSeries,
            {
              ...readDrawdownOptions(curveIndex),
              lineStyle: style.lineStyle,
              lineWidth: 1,
              priceLineVisible: false,
              priceFormat: PERCENT_FORMAT,
            },
            DRAWDOWN_PANE_INDEX,
          );
    return [equitySeries, drawdownSeries];
  }

  $effect(() => {
    if (chartContainer === undefined) {
      return;
    }
    const themeOptions = readChartThemeOptions(chartContainer);
    const createdChart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true, panes: readPaneOptions() },
      grid: themeOptions.grid,
      rightPriceScale: themeOptions.rightPriceScale,
      timeScale: { ...themeOptions.timeScale, timeVisible: false },
    });
    chart = createdChart;
    const endColorSchemeWatch = watchColorScheme(applyColors);
    return () => {
      endColorSchemeWatch();
      createdChart.remove();
      chart = undefined;
      curveSeries = [];
      interruptionSeries = undefined;
      fittedCurvesKey = '';
    };
  });

  // Same curves: only new data. Other curve count: new series.
  $effect(() => {
    if (chart === undefined) {
      return;
    }
    if (interruptionSeries === undefined) {
      // Added first, so the curves are drawn on top of the grey columns.
      interruptionSeries = chart.addSeries(
        HistogramSeries,
        {
          color: readChartColor(chartContainer, INTERRUPTION_COLOR_VARIABLE),
          priceScaleId: INTERRUPTION_PRICE_SCALE_ID,
          lastValueVisible: false,
          priceLineVisible: false,
        },
        EQUITY_PANE_INDEX,
      );
      chart.priceScale(INTERRUPTION_PRICE_SCALE_ID, EQUITY_PANE_INDEX).applyOptions({
        visible: false,
        scaleMargins: { top: 0, bottom: 0 },
      });
    }
    if (curveSeries.length !== curves.length * SERIES_PER_CURVE) {
      for (const series of curveSeries) {
        chart.removeSeries(series);
      }
      const createdChart = chart;
      curveSeries = curves.flatMap((_, curveIndex) => addCurveSeries(createdChart, curveIndex));
      const [equityPane, drawdownPane] = chart.panes();
      equityPane?.setStretchFactor(EQUITY_PANE_STRETCH);
      drawdownPane?.setStretchFactor(DRAWDOWN_PANE_STRETCH);
    }
    interruptionSeries.setData(
      findInterruptedTimes(
        curves.map((curve) => curve.points),
        interruptions,
      ).map((timeUtc) => ({ time: convertToTimestamp(timeUtc), value: INTERRUPTION_COLUMN_VALUE })),
    );
    curves.forEach((curve, curveIndex) => {
      curveSeries[curveIndex * SERIES_PER_CURVE]?.setData(
        curve.points.map((point) => ({ time: convertToTimestamp(point.time_utc), value: Number(point.equity_usd) })),
      );
      curveSeries[curveIndex * SERIES_PER_CURVE + 1]?.setData(
        computeDrawdownCurve(curve.points, curve.startCapitalUsd).map((point) => ({
          time: convertToTimestamp(point.timeUtc),
          value: point.drawdownPercent,
        })),
      );
    });
    const curvesKey = readCurvesKey(curves);
    if (curvesKey !== fittedCurvesKey && curves.some((curve) => curve.points.length > 0)) {
      chart.timeScale().fitContent();
      fittedCurvesKey = curvesKey;
    }
  });
</script>

<ChartFrame {label} {fill} bind:canvas={chartContainer}>
  <InterruptionList {label} {interruptions} />
</ChartFrame>
