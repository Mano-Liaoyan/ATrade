<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).
     A live bar replaces the last candlestick or adds one after it (series.update), without a new fit of the view.
     ChartFrame (foundation/chart_frame) gives the canvas container and the TradingView attribution. With `fill`, the
     chart fills the height of its parent and follows each size change (autoSize). -->
<script lang="ts">
  import {
    CandlestickSeries,
    createChart,
    type CandlestickData,
    type CandlestickStyleOptions,
    type DeepPartial,
    type IChartApi,
    type ISeriesApi,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import { untrack } from 'svelte';
  import { ChartFrame, readChartColor, readChartThemeOptions } from '#lib/foundation/chart_frame';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import type { Bar } from './bars';
  import { canDrawLiveBar } from './live_bars';

  interface Props {
    bars: Bar[];
    liveBar?: Bar | null;
    label: string;
    fill?: boolean;
  }

  const { bars, liveBar = null, label, fill = false }: Props = $props();

  let chartContainer: HTMLDivElement | undefined = $state();
  let chart: IChartApi | undefined = $state();
  let candlestickSeries: ISeriesApi<'Candlestick'> | undefined = $state();

  function toCandlestick(bar: Bar): CandlestickData<UTCTimestamp> {
    return { time: bar.time as UTCTimestamp, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
  }

  function readCandlestickOptions(): DeepPartial<CandlestickStyleOptions> {
    const upColor = readChartColor(chartContainer, '--cds-support-success');
    const downColor = readChartColor(chartContainer, '--cds-support-error');
    return { upColor, downColor, borderUpColor: upColor, borderDownColor: downColor, wickUpColor: upColor, wickDownColor: downColor };
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
    const createdSeries = createdChart.addSeries(CandlestickSeries, readCandlestickOptions());
    candlestickSeries = createdSeries;
    chart = createdChart;
    const endColorSchemeWatch = watchColorScheme(() => {
      createdChart.applyOptions(readChartThemeOptions(chartContainer));
      createdSeries.applyOptions(readCandlestickOptions());
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

<ChartFrame {label} {fill} bind:canvas={chartContainer} />
