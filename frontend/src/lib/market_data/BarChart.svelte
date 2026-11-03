<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).
     A live bar replaces the last candlestick or adds one after it (series.update), without a new fit of the view.
     ChartFrame (foundation/chart_frame) gives the canvas container and the TradingView attribution. With `fill`, the
     chart fills the height of its parent and follows each size change (autoSize).
     Indicators (docs/architecture/indicator.md section 23.9): the price pane indicators of `indicatorPanes` draw as
     line series with the values of `indicatorSeries` (a bar without a value is whitespace data). The legend at the top
     left shows the OHLC row and one row for each indicator, at the crosshair bar, or at the last bar when the
     crosshair is not on the chart. The backend calculates all values; the chart calculates none. -->
<script lang="ts">
  import {
    CandlestickSeries,
    createChart,
    LineSeries,
    LineStyle,
    type CandlestickData,
    type CandlestickStyleOptions,
    type DeepPartial,
    type IChartApi,
    type ISeriesApi,
    type LineData,
    type LineWidth,
    type MouseEventParams,
    type UTCTimestamp,
    type WhitespaceData,
  } from 'lightweight-charts';
  import { untrack } from 'svelte';
  import { CHART_PRICE_FORMAT, ChartFrame, readChartColor, readChartThemeOptions } from '#lib/foundation/chart_frame';
  import { isDarkColorScheme, watchColorScheme } from '#lib/foundation/color_scheme';
  import { formatPrice } from '#lib/foundation/value_format';
  import type { Bar } from './bars';
  import { readIndicatorPriceFormat, readPaletteColor } from './chart_indicator_styles';
  import {
    buildLegendRows,
    findIndicatorSeries,
    findLegendIndex,
    type ChartIndicatorDefinition,
    type ChartLineStyle,
    type ChartPane,
    type LegendBar,
  } from './chart_indicators';
  import ChartLegend from './ChartLegend.svelte';
  import type { IndicatorSeriesResult } from './indicator_series';
  import { canDrawLiveBar } from './live_bars';

  interface Props {
    bars: Bar[];
    liveBar?: Bar | null;
    label: string;
    fill?: boolean;
    /** The indicators of the chart. The first pane is the price pane. */
    indicatorPanes?: ChartPane[];
    /** The values of the indicators, from POST /api/market-data/indicator-series. */
    indicatorSeries?: IndicatorSeriesResult | null;
    /** The indicator catalog, for the legend names. */
    catalog?: ChartIndicatorDefinition[];
  }

  const {
    bars,
    liveBar = null,
    label,
    fill = false,
    indicatorPanes = [{ indicators: [] }],
    indicatorSeries = null,
    catalog = [],
  }: Props = $props();

  const LINE_STYLES: Record<ChartLineStyle, LineStyle> = {
    solid: LineStyle.Solid,
    dashed: LineStyle.Dashed,
    dotted: LineStyle.Dotted,
  };

  let chartContainer: HTMLDivElement | undefined = $state();
  let chart: IChartApi | undefined = $state();
  let candlestickSeries: ISeriesApi<'Candlestick'> | undefined = $state();
  // The palette of the lines follows the theme (section 23.9.3).
  let isDark = $state(false);
  // The bar time under the crosshair, or null when the crosshair is not on the chart.
  let crosshairTime: number | null = $state(null);

  function toCandlestick(bar: Bar): CandlestickData<UTCTimestamp> {
    return { time: bar.time as UTCTimestamp, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
  }

  function readCandlestickOptions(): DeepPartial<CandlestickStyleOptions> {
    const upColor = readChartColor(chartContainer, '--cds-support-success');
    const downColor = readChartColor(chartContainer, '--cds-support-error');
    return { upColor, downColor, borderUpColor: upColor, borderDownColor: downColor, wickUpColor: upColor, wickDownColor: downColor };
  }

  function followCrosshair(parameters: MouseEventParams): void {
    crosshairTime = parameters.time === undefined ? null : (parameters.time as number);
  }

  $effect(() => {
    if (chartContainer === undefined) {
      return;
    }
    const themeOptions = readChartThemeOptions(chartContainer);
    const createdChart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true },
      grid: themeOptions.grid,
      rightPriceScale: themeOptions.rightPriceScale,
      timeScale: { ...themeOptions.timeScale, timeVisible: true, secondsVisible: false },
    });
    const createdSeries = createdChart.addSeries(CandlestickSeries, { ...readCandlestickOptions(), priceFormat: CHART_PRICE_FORMAT });
    candlestickSeries = createdSeries;
    chart = createdChart;
    isDark = isDarkColorScheme();
    createdChart.subscribeCrosshairMove(followCrosshair);
    const endColorSchemeWatch = watchColorScheme(() => {
      createdChart.applyOptions(readChartThemeOptions(chartContainer));
      createdSeries.applyOptions(readCandlestickOptions());
      isDark = isDarkColorScheme();
    });
    return () => {
      endColorSchemeWatch();
      createdChart.unsubscribeCrosshairMove(followCrosshair);
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

  const priceIndicators = $derived(indicatorPanes[0]?.indicators ?? []);

  // The lines of the price pane indicators. Each change of the indicators, their values, or the theme draws them again.
  $effect(() => {
    const currentChart = chart;
    if (currentChart === undefined) {
      return;
    }
    const lines: ISeriesApi<'Line'>[] = [];
    for (const indicator of priceIndicators) {
      if (indicator.hidden) {
        continue;
      }
      const series = findIndicatorSeries(indicatorSeries, indicator);
      for (const line of indicator.lines) {
        const lineSeries = currentChart.addSeries(LineSeries, {
          color: readPaletteColor(line.color, isDark),
          lineWidth: line.width as LineWidth,
          lineStyle: LINE_STYLES[line.style],
          priceFormat: readIndicatorPriceFormat(indicator.indicator),
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        const values = series?.outputs[line.output] ?? [];
        const times = indicatorSeries?.times ?? [];
        lineSeries.setData(
          times.map((time, index): LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp> => {
            const value = values[index] ?? null;
            return value === null ? { time: time as UTCTimestamp } : { time: time as UTCTimestamp, value };
          }),
        );
        lines.push(lineSeries);
      }
    }
    return () => {
      for (const lineSeries of lines) {
        currentChart.removeSeries(lineSeries);
      }
    };
  });

  const legendBar: LegendBar | null = $derived.by(() => {
    const allBars = liveBar !== null && canDrawLiveBar(bars, liveBar) ? [...bars.filter((bar) => bar.time !== liveBar.time), liveBar] : bars;
    const bar = crosshairTime === null ? allBars.at(-1) : allBars.find((item) => item.time === crosshairTime);
    if (bar === undefined) {
      return null;
    }
    return { open: formatPrice(bar.open), high: formatPrice(bar.high), low: formatPrice(bar.low), close: formatPrice(bar.close) };
  });

  const legendRows = $derived(
    buildLegendRows(
      priceIndicators,
      catalog,
      indicatorSeries,
      findLegendIndex(indicatorSeries?.times ?? [], crosshairTime),
      isDark,
    ),
  );
</script>

<ChartFrame {label} {fill} bind:canvas={chartContainer}>
  {#snippet overlay()}
    <ChartLegend bar={legendBar} rows={legendRows} />
  {/snippet}
</ChartFrame>
