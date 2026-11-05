<!-- Bar chart: draws each bar as a candlestick with lightweight-charts. Bar times are UNIX timestamps (UTC).
     A live bar replaces the last candlestick or adds one after it (series.update), without a new fit of the view.
     ChartFrame (foundation/chart_frame) gives the canvas container and the TradingView attribution. With `fill`, the
     chart fills the height of its parent and follows each size change (autoSize).
     Indicators (docs/architecture/indicator.md section 23.9): each pane of `indicatorPanes` is a chart pane. The first
     is the price pane with the candlesticks; each own pane has its own price scale. The indicators draw as line and
     histogram series with the values of `indicatorSeries` (a bar without a value is whitespace data). Each pane has
     a legend at its top left (the price pane also the OHLC row), with the values at the crosshair bar, or at the last
     bar when the crosshair is not on the chart, and an options menu at its top right. Each indicator series shows the
     same value as a label in its color on the price axis of its pane, and the crosshair puts a dot on each line. With `onPanesChange`, each legend
     row has Hide or Show, Settings (a popover), and Remove. A theme change gives the lines the other palette and does
     not create the chart again. The backend calculates all values; the chart calculates none.
     With `trades`, the price pane shows a trade mark for each bar and side (section 23.9.9, `trade_marks.ts`). The
     pointer on a mark gives it the focus ring and a tooltip. `ringTrades` gives the marks of these trades the ring;
     a new `centerTrade` scrolls the chart so that the bar of the trade is in the center.
     With `onNeedOlderBars`, a scroll or drag of the user to the left near the first bar calls it (older_bars.ts). A
     new bar list that is the shown bars with older bars before them keeps the visible range; other new bars fit the
     view. -->
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
    type IPriceLine,
    type ISeriesApi,
    type LineData,
    type LineWidth,
    type LogicalRange,
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
  import { countPrependedBars, isMoveToFirstBar } from './older_bars';
  import TradeMarkLayer from './TradeMarkLayer.svelte';
  import {
    BAR_PERIOD_SECONDS,
    centerBar,
    findMarkAt,
    findTradeBarIndex,
    groupTradeMarks,
    TradeMarksPrimitive,
    type ChartTrade,
    type TradeMarkBox,
    type TradeMarkColors,
  } from './trade_marks';
  import type { BarPeriod } from './bars';

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
    /** The trades of a backtest or a forward test, for the trade marks. `barPeriod` places them on the bars. */
    trades?: ChartTrade[];
    barPeriod?: BarPeriod;
    /** The trades (indexes into `trades`) whose marks have the focus ring. */
    ringTrades?: number[];
    /** A new value scrolls the chart so that the bar of this trade is in the center. */
    centerTrade?: number | null;
    /** Called when the user scrolls or drags the chart to the left near the first bar. */
    onNeedOlderBars?: () => void;
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
    trades = [],
    barPeriod = '1-DAY',
    ringTrades = [],
    centerTrade = null,
    onNeedOlderBars,
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
  let tradeMarks: TradeMarksPrimitive | undefined = $state();
  // The place of each trade mark after the last redraw, and the mark under the pointer ("<bar index>:<side>").
  let markBoxes: TradeMarkBox[] = $state([]);
  let hoveredMarkKey: string | null = $state(null);
  // One price axis label for each drawn indicator series, with the values of the series (section 23.9.4).
  let axisLabels: { priceLine: IPriceLine; values: readonly (number | null)[] }[] = [];
  // The bars of the last setData, and whether the user moved the view after the last fit (a fit is no user move).
  let shownBars: readonly Bar[] = [];
  let isMovedByUser = false;

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
    const point = parameters.point;
    const box = point === undefined || (parameters.paneIndex ?? 0) !== 0 ? undefined : findMarkAt(markBoxes, point.x, point.y);
    hoveredMarkKey = box === undefined ? null : `${String(box.mark.barIndex)}:${box.mark.side}`;
  }

  // IBM Plex Mono semibold 11px (section 23.9.9).
  const MARK_FONT = "600 11px 'IBM Plex Mono', monospace";

  function readMarkColors(): TradeMarkColors {
    return {
      background: readChartColor(chartContainer, '--cds-background-inverse'),
      text: readChartColor(chartContainer, '--cds-text-inverse'),
      ring: readChartColor(chartContainer, '--cds-focus'),
      font: MARK_FONT,
    };
  }

  // The boxes change at each scroll and zoom. Only a real change updates the state. The chart calls this in the
  // calls of the effects (setData, addSeries): untrack, so that the effects do not depend on the boxes.
  function keepMarkBoxes(boxes: TradeMarkBox[]): void {
    untrack(() => {
      if (JSON.stringify(boxes) !== JSON.stringify(markBoxes)) {
        markBoxes = boxes;
      }
    });
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
    const createdMarks = new TradeMarksPrimitive(readMarkColors(), keepMarkBoxes);
    createdSeries.attachPrimitive(createdMarks);
    tradeMarks = createdMarks;
    // The canvas draws with the font only after it loads.
    void document.fonts.load(MARK_FONT).then(() => {
      createdMarks.setColors(readMarkColors());
    });
    candlestickSeries = createdSeries;
    chart = createdChart;
    isDark = isDarkColorScheme();
    createdChart.subscribeCrosshairMove(followCrosshair);
    const endColorSchemeWatch = watchColorScheme(() => {
      const changedOptions = readChartThemeOptions(chartContainer);
      createdChart.applyOptions({ ...changedOptions, layout: { ...changedOptions.layout, panes: readPaneOptions() } });
      createdSeries.applyOptions(readCandlestickOptions());
      createdMarks.setColors(readMarkColors());
      isDark = isDarkColorScheme();
    });
    return () => {
      endColorSchemeWatch();
      createdChart.unsubscribeCrosshairMove(followCrosshair);
      createdChart.remove();
      chart = undefined;
      candlestickSeries = undefined;
      tradeMarks = undefined;
      shownBars = [];
      markBoxes = [];
      paneCount = 0;
      maximized = null;
    };
  });

  $effect(() => {
    if (chart === undefined || candlestickSeries === undefined) {
      return;
    }
    const timeScale = chart.timeScale();
    const prependedCount = countPrependedBars(shownBars, bars);
    const visibleRange = timeScale.getVisibleLogicalRange();
    candlestickSeries.setData(bars.map(toCandlestick));
    if (prependedCount !== null && visibleRange !== null) {
      // The older bars are left of the view: the same bars stay visible.
      timeScale.setVisibleLogicalRange({ from: visibleRange.from + prependedCount, to: visibleRange.to + prependedCount });
    } else {
      timeScale.fitContent();
      isMovedByUser = false;
    }
    shownBars = bars;
    // The live bar that came before the bars is drawn again. A new live bar does not run this effect.
    const currentLiveBar = untrack(() => liveBar);
    if (currentLiveBar !== null && canDrawLiveBar(bars, currentLiveBar)) {
      candlestickSeries.update(toCandlestick(currentLiveBar));
    }
  });

  // Only a move of the user asks for older bars: the first fit shows the first bar too.
  $effect(() => {
    const currentChart = chart;
    const container = chartContainer;
    const needOlderBars = onNeedOlderBars;
    if (currentChart === undefined || container === undefined || needOlderBars === undefined) {
      return;
    }
    let previousFrom: number | null = null;
    const markUserMove = (): void => {
      isMovedByUser = true;
    };
    const followVisibleRange = (range: LogicalRange | null): void => {
      if (range === null) {
        return;
      }
      if (isMovedByUser && isMoveToFirstBar(previousFrom, range.from)) {
        needOlderBars();
      }
      previousFrom = range.from;
    };
    container.addEventListener('pointerdown', markUserMove, { capture: true });
    container.addEventListener('wheel', markUserMove, { capture: true, passive: true });
    currentChart.timeScale().subscribeVisibleLogicalRangeChange(followVisibleRange);
    return () => {
      container.removeEventListener('pointerdown', markUserMove, { capture: true });
      container.removeEventListener('wheel', markUserMove, { capture: true });
      currentChart.timeScale().unsubscribeVisibleLogicalRangeChange(followVisibleRange);
    };
  });

  $effect(() => {
    if (candlestickSeries === undefined || liveBar === null) {
      return;
    }
    if (canDrawLiveBar(untrack(() => bars), liveBar)) {
      candlestickSeries.update(toCandlestick(liveBar));
    }
  });

  $effect(() => {
    tradeMarks?.setMarks(
      groupTradeMarks(
        trades,
        bars.map((bar) => bar.time),
        BAR_PERIOD_SECONDS[barPeriod],
      ),
      bars,
    );
  });

  const hoveredTrades = $derived(
    markBoxes.find((box) => `${String(box.mark.barIndex)}:${box.mark.side}` === hoveredMarkKey)?.mark.tradeIndexes ?? [],
  );

  $effect(() => {
    tradeMarks?.setRingTrades([...ringTrades, ...hoveredTrades]);
  });

  // After the bars effect: a new bar list fits the content, then the chart scrolls to the trade again.
  $effect(() => {
    const currentChart = chart;
    const trade = centerTrade === null ? undefined : untrack(() => trades)[centerTrade];
    if (currentChart === undefined || trade === undefined || bars.length === 0) {
      return;
    }
    const barIndex = findTradeBarIndex(
      bars.map((bar) => bar.time),
      BAR_PERIOD_SECONDS[barPeriod],
      trade.time,
    );
    if (barIndex === -1) {
      return;
    }
    // The chart scrolls when it has its size: lightweight-charts fits the content again at the first size.
    let frame = 0;
    const center = (): void => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (currentChart.timeScale().width() > 0) {
          centerBar(currentChart, barIndex);
        }
      });
    };
    let isWaitingForSize = currentChart.timeScale().width() === 0;
    const centerAtFirstSize = (): void => {
      if (isWaitingForSize) {
        isWaitingForSize = false;
        center();
      }
    };
    currentChart.timeScale().subscribeSizeChange(centerAtFirstSize);
    center();
    return () => {
      cancelAnimationFrame(frame);
      currentChart.timeScale().unsubscribeSizeChange(centerAtFirstSize);
    };
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
    axisLabels = [];
    panes.forEach((pane, paneIndex) => {
      for (const indicator of pane.indicators) {
        if (!indicator.hidden) {
          drawn.push(...drawIndicator(currentChart, indicator, paneIndex, guideColor));
        }
      }
    });
    showAxisLabels(untrack(() => legendIndex));
    return () => {
      axisLabels = [];
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
      const values = series?.outputs[line.output] ?? [];
      const points = toSeriesPoints(times, values);
      const addAxisLabel = (drawnSeries: ISeriesApi<'Line' | 'Histogram'>): void => {
        const priceLine = drawnSeries.createPriceLine({ price: 0, color, lineVisible: false, axisLabelVisible: false, title: '' });
        axisLabels.push({ priceLine, values });
      };
      if (isHistogramLine(indicator.indicator, line.output)) {
        const histogram = currentChart.addSeries(HistogramSeries, { color, priceFormat, priceLineVisible: false, lastValueVisible: false }, paneIndex);
        histogram.setData(points);
        addAxisLabel(histogram);
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
        },
        paneIndex,
      );
      lineSeries.setData(points);
      addAxisLabel(lineSeries);
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
  // The label of each series shows its value at the legend bar; a bar without a value shows no label.
  function showAxisLabels(index: number | null): void {
    for (const { priceLine, values } of axisLabels) {
      const value = index === null ? null : (values[index] ?? null);
      priceLine.applyOptions(value === null ? { axisLabelVisible: false } : { price: value, axisLabelVisible: true });
    }
  }

  $effect(() => {
    showAxisLabels(legendIndex);
  });

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
    {#if trades.length > 0}
      <TradeMarkLayer boxes={markBoxes} {trades} {hoveredMarkKey} ringTrades={[...ringTrades, ...hoveredTrades]} />
    {/if}
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
