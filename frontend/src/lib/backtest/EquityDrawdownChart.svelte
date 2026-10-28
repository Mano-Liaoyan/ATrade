<!-- The equity curve of a backtest or a forward test and, under it, its drawdown curve (computeDrawdownCurve), on one
     lightweight-charts chart with 2 panes. The panes share one time scale, so both curves zoom and scroll together and
     their times stay aligned (spec #99, like QuantConnect). The drawdown is a negative percent, the same sign as the max
     drawdown metric. With `fill`, the chart fills its parent and follows each size change (autoSize).
     All colors are Carbon tokens: --cds-text-primary (equity), --cds-support-error (drawdown line, and its fill with
     alpha), and the theme colors of readChartThemeOptions. ChartFrame gives the canvas container and the TradingView
     attribution. The backtest page, the strategy page, and the forward test page all use it. -->
<script lang="ts">
  import {
    AreaSeries,
    createChart,
    LineSeries,
    type IChartApi,
    type ISeriesApi,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import { ChartFrame, readChartColor, readChartThemeOptions } from '#lib/foundation/chart_frame';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import { computeDrawdownCurve } from './drawdown_curve';

  interface Props {
    points: readonly { time_utc: string; equity_usd: string }[];
    /** The paper capital of a backtest or the start balance of a forward test: the first highest equity. */
    startCapitalUsd: string | null;
    label: string;
    fill?: boolean;
  }

  const { points, startCapitalUsd, label, fill = false }: Props = $props();

  const MILLISECONDS_PER_SECOND = 1000;
  const EQUITY_PANE_STRETCH = 3;
  const DRAWDOWN_PANE_STRETCH = 1;
  const DRAWDOWN_PANE_INDEX = 1;
  // The drawdown fill is the drawdown line color with this alpha (hex), so it stays a Carbon token color.
  const FILL_ALPHA_HEX = '33';
  const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i;

  let chartContainer: HTMLDivElement | undefined = $state();
  let chart: IChartApi | undefined = $state();
  let equitySeries: ISeriesApi<'Line'> | undefined = $state();
  let drawdownSeries: ISeriesApi<'Area'> | undefined = $state();

  function convertToTimestamp(timeUtc: string): UTCTimestamp {
    return (Date.parse(timeUtc) / MILLISECONDS_PER_SECOND) as UTCTimestamp;
  }

  function readDrawdownColors(): { lineColor: string; topColor: string; bottomColor: string } {
    const lineColor = readChartColor(chartContainer, '--cds-support-error');
    const fillColor = HEX_COLOR_PATTERN.test(lineColor) ? `${lineColor}${FILL_ALPHA_HEX}` : lineColor;
    return { lineColor, topColor: fillColor, bottomColor: fillColor };
  }

  function readPaneOptions(): { separatorColor: string } {
    return { separatorColor: readChartColor(chartContainer, '--cds-border-subtle-01') };
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
    const createdEquitySeries = createdChart.addSeries(LineSeries, {
      color: readChartColor(chartContainer, '--cds-text-primary'),
      lineWidth: 2,
      title: 'Equity',
      priceLineVisible: false,
    });
    const createdDrawdownSeries = createdChart.addSeries(
      AreaSeries,
      {
        ...readDrawdownColors(),
        invertFilledArea: true,
        lineWidth: 1,
        title: 'Drawdown %',
        priceLineVisible: false,
      },
      DRAWDOWN_PANE_INDEX,
    );
    const [equityPane, drawdownPane] = createdChart.panes();
    equityPane?.setStretchFactor(EQUITY_PANE_STRETCH);
    drawdownPane?.setStretchFactor(DRAWDOWN_PANE_STRETCH);
    chart = createdChart;
    equitySeries = createdEquitySeries;
    drawdownSeries = createdDrawdownSeries;
    const endColorSchemeWatch = watchColorScheme(() => {
      const options = readChartThemeOptions(chartContainer);
      createdChart.applyOptions({ ...options, layout: { ...options.layout, panes: readPaneOptions() } });
      createdEquitySeries.applyOptions({ color: readChartColor(chartContainer, '--cds-text-primary') });
      createdDrawdownSeries.applyOptions(readDrawdownColors());
    });
    return () => {
      endColorSchemeWatch();
      createdChart.remove();
      chart = undefined;
      equitySeries = undefined;
      drawdownSeries = undefined;
    };
  });

  $effect(() => {
    if (chart === undefined || equitySeries === undefined || drawdownSeries === undefined) {
      return;
    }
    equitySeries.setData(points.map((point) => ({ time: convertToTimestamp(point.time_utc), value: Number(point.equity_usd) })));
    drawdownSeries.setData(
      computeDrawdownCurve(points, startCapitalUsd).map((point) => ({
        time: convertToTimestamp(point.timeUtc),
        value: point.drawdownPercent,
      })),
    );
    chart.timeScale().fitContent();
  });
</script>

<ChartFrame {label} {fill} bind:canvas={chartContainer} />
