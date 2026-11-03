<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).
     A live bar replaces the last candlestick or adds one after it (series.update), without a new fit of the view.
     ChartFrame (foundation/chart_frame) gives the canvas container and the TradingView attribution. With `fill`, the
     chart fills the height of its parent and follows each size change (autoSize).
     Indicators (docs/architecture/indicator.md section 23.9): each pane of `indicatorPanes` is a chart pane. The first
     is the price pane with the candlesticks; each own pane has its own price scale. The indicators draw as line and
     histogram series with the values of `indicatorSeries` (a bar without a value is whitespace data). Each pane has
     a legend at its top left (the price pane also the OHLC row), with the values at the crosshair bar, or at the last
     bar when the crosshair is not on the chart, and an options menu at its top right. With `onPanesChange`, each legend
     row has Hide or Show, Settings (a popover), and Remove. A theme change gives the lines the other palette and does
     not create the chart again. The backend calculates all values; the chart calculates none. -->
<script lang="ts">
  import {
    CandlestickSeries,
    createChart,
    HistogramSeries,
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
  import { isHistogramLine, readIndicatorPriceFormat, readPaletteColor, RSI_GUIDE_LEVELS } from './chart_indicator_styles';
  import { type OverflowMenuItem } from '#lib/foundation/carbon';
  import {
    buildLegendRows,
    findIndicatorSeries,
    findLegendIndex,
    findMaximizedStretchFactors,
    listPaneActions,
    moveOwnPane,
    removeChartIndicator,
    removeOwnPane,
    type ChartIndicator,
    type ChartIndicatorDefinition,
    type ChartLineStyle,
    type ChartPane,
    type LegendBar,
    type LegendRow,
    type LegendRowActions,
    type PaneAction,
    type PaneBox,
  } from './chart_indicators';
  import ChartPaneOverlay from './ChartPaneOverlay.svelte';
  import IndicatorSettings from './IndicatorSettings.svelte';
  import { replaceChartIndicator } from './indicator_settings';
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
    /** Gets the new panes after a change in a pane options menu or a legend row (Hide, Show, Settings, Remove). */
    onPanesChange?: (panes: ChartPane[]) => void;
  }

  const {
    bars,
    liveBar = null,
    label,
    fill = false,
    indicatorPanes = [{ indicators: [] }],
    indicatorSeries = null,
    catalog = [],
    onPanesChange,
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
  // The panes of the chart now, and the place of each over the canvas.
  let paneCount = $state(0);
  let paneBoxes: PaneBox[] = $state([]);
  // The maximized pane and the stretch factors of all panes from before "Maximize".
  let maximized: { paneIndex: number; factors: number[] } | null = $state(null);
  // The indicator whose settings popover is open, and the legend row that the popover is at.
  let settings = $state<{ paneIndex: number; indicatorIndex: number; anchor: HTMLElement } | null>(null);

  function toCandlestick(bar: Bar): CandlestickData<UTCTimestamp> {
    return { time: bar.time as UTCTimestamp, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
  }

  function readCandlestickOptions(): DeepPartial<CandlestickStyleOptions> {
    const upColor = readChartColor(chartContainer, '--cds-support-success');
    const downColor = readChartColor(chartContainer, '--cds-support-error');
    return { upColor, downColor, borderUpColor: upColor, borderDownColor: downColor, wickUpColor: upColor, wickDownColor: downColor };
  }

  // The user drags the line between 2 panes to change their heights (section 23.9.3). Not saved.
  function readPaneOptions(): { enableResize: boolean; separatorColor: string; separatorHoverColor: string } {
    return {
      enableResize: true,
      separatorColor: readChartColor(chartContainer, '--cds-border-subtle-01'),
      separatorHoverColor: readChartColor(chartContainer, '--cds-border-strong-01'),
    };
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
      layout: { ...themeOptions.layout, attributionLogo: true, panes: readPaneOptions() },
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
      const changedOptions = readChartThemeOptions(chartContainer);
      createdChart.applyOptions({ ...changedOptions, layout: { ...changedOptions.layout, panes: readPaneOptions() } });
      createdSeries.applyOptions(readCandlestickOptions());
      isDark = isDarkColorScheme();
    });
    return () => {
      endColorSchemeWatch();
      createdChart.unsubscribeCrosshairMove(followCrosshair);
      createdChart.remove();
      chart = undefined;
      candlestickSeries = undefined;
      paneCount = 0;
      maximized = null;
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

  // The chart has one pane for each pane of `indicatorPanes`: the price pane and the own panes, in this order. Each
  // change of the indicators, their values, or the theme draws all indicator series again. The own panes keep their
  // place and height (preserveEmptyPane), so a new value list does not change the heights that the user dragged.
  $effect(() => {
    const currentChart = chart;
    if (currentChart === undefined) {
      return;
    }
    const panes = indicatorPanes;
    untrack(() => {
      syncPaneCount(currentChart, panes.length);
    });
    const guideColor = readChartColor(chartContainer, '--cds-border-strong-01');
    const drawn: ISeriesApi<'Line' | 'Histogram'>[] = [];
    panes.forEach((pane, paneIndex) => {
      for (const indicator of pane.indicators) {
        if (!indicator.hidden) {
          drawn.push(...drawIndicator(currentChart, indicator, paneIndex, guideColor));
        }
      }
    });
    return () => {
      for (const series of drawn) {
        currentChart.removeSeries(series);
      }
    };
  });

  function syncPaneCount(currentChart: IChartApi, count: number): void {
    // A new or removed pane ends "Maximize". New values or a theme change keep it.
    if (maximized !== null && currentChart.panes().length !== Math.max(count, 1)) {
      restorePanes();
    }
    while (currentChart.panes().length < count) {
      currentChart.addPane(true);
    }
    while (currentChart.panes().length > Math.max(count, 1)) {
      currentChart.removePane(currentChart.panes().length - 1);
    }
    for (const pane of currentChart.panes().slice(1)) {
      pane.setPreserveEmptyPane(true);
    }
    paneCount = currentChart.panes().length;
  }

  function toSeriesPoints(times: readonly number[], values: readonly (number | null)[]): (LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp>)[] {
    return times.map((time, index) => {
      const value = values[index] ?? null;
      return value === null ? { time: time as UTCTimestamp } : { time: time as UTCTimestamp, value };
    });
  }

  function drawIndicator(currentChart: IChartApi, indicator: ChartIndicator, paneIndex: number, guideColor: string): ISeriesApi<'Line' | 'Histogram'>[] {
    const series = findIndicatorSeries(indicatorSeries, indicator);
    const times = indicatorSeries?.times ?? [];
    const priceFormat = readIndicatorPriceFormat(indicator.indicator);
    return indicator.lines.map((line) => {
      const color = readPaletteColor(line.color, isDark);
      const points = toSeriesPoints(times, series?.outputs[line.output] ?? []);
      if (isHistogramLine(indicator.indicator, line.output)) {
        const histogram = currentChart.addSeries(HistogramSeries, { color, priceFormat, priceLineVisible: false, lastValueVisible: false }, paneIndex);
        histogram.setData(points);
        return histogram;
      }
      const lineSeries = currentChart.addSeries(
        LineSeries,
        {
          color,
          lineWidth: line.width as LineWidth,
          lineStyle: LINE_STYLES[line.style],
          priceFormat,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        },
        paneIndex,
      );
      lineSeries.setData(points);
      if (indicator.indicator === 'rsi') {
        for (const price of RSI_GUIDE_LEVELS) {
          lineSeries.createPriceLine({ price, color: guideColor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: '' });
        }
      }
      return lineSeries;
    });
  }

  // The place of each pane over the canvas, for its legend and options button. A drag of the line between 2 panes, a
  // new pane, and a size change of the chart measure again.
  function measurePanes(): void {
    if (chart === undefined || chartContainer === undefined) {
      return;
    }
    const origin = chartContainer.getBoundingClientRect();
    const width = chart.timeScale().width();
    paneBoxes = chart.panes().map((pane) => {
      const rect = pane.getHTMLElement()?.getBoundingClientRect();
      return rect === undefined ? { top: 0, height: 0, width } : { top: rect.top - origin.top, height: rect.height, width };
    });
  }

  $effect(() => {
    const currentChart = chart;
    if (currentChart === undefined || paneCount === 0) {
      return;
    }
    const resizeObserver = new ResizeObserver(measurePanes);
    const frame = requestAnimationFrame(() => {
      for (const pane of currentChart.panes()) {
        const element = pane.getHTMLElement();
        if (element !== null) {
          resizeObserver.observe(element);
        }
      }
      measurePanes();
    });
    currentChart.timeScale().subscribeSizeChange(measurePanes);
    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      currentChart.timeScale().unsubscribeSizeChange(measurePanes);
    };
  });

  // "Maximize" gives one pane all the height; "Restore" gives back the stretch factors from before. Not saved.
  function maximizePane(paneIndex: number): void {
    if (chart === undefined) {
      return;
    }
    const panes = chart.panes();
    const factors = panes.map((pane) => pane.getStretchFactor());
    const maximizedFactors = findMaximizedStretchFactors(
      panes.map((pane) => pane.getHeight()),
      paneIndex,
    );
    panes.forEach((pane, index) => {
      pane.setStretchFactor(maximizedFactors[index] ?? 1);
    });
    maximized = { paneIndex, factors };
  }

  function restorePanes(): void {
    const saved = maximized;
    if (chart === undefined || saved === null) {
      return;
    }
    chart.panes().forEach((pane, index) => {
      pane.setStretchFactor(saved.factors[index] ?? 1);
    });
    maximized = null;
  }

  // A moved pane takes its height with it.
  function movePane(paneIndex: number, direction: 'up' | 'down'): void {
    restorePanes();
    const otherIndex = direction === 'up' ? paneIndex - 1 : paneIndex + 1;
    const [pane, otherPane] = [chart?.panes()[paneIndex], chart?.panes()[otherIndex]];
    if (pane !== undefined && otherPane !== undefined) {
      const factor = pane.getStretchFactor();
      pane.setStretchFactor(otherPane.getStretchFactor());
      otherPane.setStretchFactor(factor);
    }
    onPanesChange?.(moveOwnPane(indicatorPanes, paneIndex, direction));
  }

  function removePane(paneIndex: number): void {
    restorePanes();
    onPanesChange?.(removeOwnPane(indicatorPanes, paneIndex));
  }

  const ACTION_LABELS: Record<PaneAction, string> = {
    move_up: 'Move up',
    move_down: 'Move down',
    maximize: 'Maximize',
    restore: 'Restore',
    remove: 'Remove indicators',
  };

  function makeMenuItems(paneIndex: number): OverflowMenuItem[] {
    const actions = listPaneActions(paneIndex, indicatorPanes.length, maximized?.paneIndex === paneIndex);
    // Without onPanesChange the chart can change only the heights.
    const allowed = onPanesChange === undefined ? actions.filter((action) => action === 'maximize' || action === 'restore') : actions;
    const handlers: Record<PaneAction, () => void> = {
      move_up: () => {
        movePane(paneIndex, 'up');
      },
      move_down: () => {
        movePane(paneIndex, 'down');
      },
      maximize: () => {
        maximizePane(paneIndex);
      },
      restore: restorePanes,
      remove: () => {
        removePane(paneIndex);
      },
    };
    return allowed.map((action) => ({ label: ACTION_LABELS[action], danger: action === 'remove', onSelect: handlers[action] }));
  }

  const legendBar: LegendBar | null = $derived.by(() => {
    const allBars = liveBar !== null && canDrawLiveBar(bars, liveBar) ? [...bars.filter((bar) => bar.time !== liveBar.time), liveBar] : bars;
    const bar = crosshairTime === null ? allBars.at(-1) : allBars.find((item) => item.time === crosshairTime);
    if (bar === undefined) {
      return null;
    }
    return { open: formatPrice(bar.open), high: formatPrice(bar.high), low: formatPrice(bar.low), close: formatPrice(bar.close) };
  });

  function makeRowActions(paneIndex: number): LegendRowActions | undefined {
    const changePanes = onPanesChange;
    if (changePanes === undefined) {
      return undefined;
    }
    return {
      onToggleHidden: (row: LegendRow) => {
        const indicator = indicatorPanes[paneIndex]?.indicators[row.indicatorIndex];
        if (indicator !== undefined) {
          changePanes(replaceChartIndicator(indicatorPanes, paneIndex, row.indicatorIndex, { ...indicator, hidden: !indicator.hidden }));
        }
      },
      onOpenSettings: (row: LegendRow, anchor: HTMLElement) => {
        settings = { paneIndex, indicatorIndex: row.indicatorIndex, anchor };
      },
      onRemove: (row: LegendRow) => {
        changePanes(removeChartIndicator(indicatorPanes, paneIndex, row.indicatorIndex));
      },
    };
  }

  const settingsIndicator = $derived(settings === null ? undefined : indicatorPanes[settings.paneIndex]?.indicators[settings.indicatorIndex]);
  const settingsDefinition = $derived(catalog.find((definition) => definition.key === settingsIndicator?.indicator));

  const legendIndex = $derived(findLegendIndex(indicatorSeries?.times ?? [], crosshairTime));
  const paneLegends = $derived(
    indicatorPanes.map((pane) => buildLegendRows(pane.indicators, catalog, indicatorSeries, legendIndex, isDark)),
  );
</script>

<ChartFrame {label} {fill} bind:canvas={chartContainer}>
  {#snippet overlay()}
    {#each paneLegends as rows, paneIndex (paneIndex)}
      {@const box = paneBoxes[paneIndex]}
      <!-- A pane of height 0 (another pane is maximized) shows no legend and no button. -->
      {#if box !== undefined && (maximized === null || maximized.paneIndex === paneIndex)}
        <ChartPaneOverlay
          {box}
          bar={paneIndex === 0 ? legendBar : null}
          {rows}
          name={paneIndex === 0 ? 'bars' : (rows[0]?.name ?? 'indicators')}
          menuItems={makeMenuItems(paneIndex)}
          actions={makeRowActions(paneIndex)}
        />
      {/if}
    {/each}
  {/snippet}
</ChartFrame>

{#if settings !== null && settingsIndicator !== undefined && settingsDefinition !== undefined}
  {@const open = settings}
  {#key open}
    <IndicatorSettings
      anchor={open.anchor}
      definition={settingsDefinition}
      indicator={settingsIndicator}
      dark={isDark}
      onApply={(indicator: ChartIndicator) => {
        onPanesChange?.(replaceChartIndicator(indicatorPanes, open.paneIndex, open.indicatorIndex, indicator));
        settings = null;
      }}
      onClose={() => {
        settings = null;
      }}
    />
  {/key}
{/if}
