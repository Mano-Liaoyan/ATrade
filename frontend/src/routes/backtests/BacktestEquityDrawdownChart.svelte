<!-- PROTOTYPE (#99), throwaway: the equity curve and, below it, the drawdown curve of one backtest on one
     lightweight-charts chart with 2 panes, so both curves use the same time axis. The chart fills its container.
     The drawdown is computed from the equity points: (equity / highest equity so far - 1) * 100.

     Attribution notice of lightweight-charts (Apache License 2.0):
     TradingView Lightweight Charts™
     Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/
     The chart shows the TradingView attribution logo. -->
<script lang="ts">
  import {
    AreaSeries,
    createChart,
    LineSeries,
    type ChartOptions,
    type DeepPartial,
    type ISeriesApi,
    type LineData,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import type { EquityPoint } from '#lib/backtest';
  import { watchColorScheme } from '#lib/foundation/color_scheme';

  const { points, label }: { points: EquityPoint[]; label: string } = $props();

  const MILLISECONDS_PER_SECOND = 1000;
  const PERCENT = 100;
  const EQUITY_PANE_STRETCH = 3;
  const DRAWDOWN_PANE_STRETCH = 1;
  // The drawdown fill is the drawdown line color with this alpha (hex), so it stays a Carbon token color.
  const FILL_ALPHA_HEX = '33';
  const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i;

  let chartContainer: HTMLDivElement;

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
  }

  function readFillColor(variableName: string): string {
    const color = readColor(variableName);
    return HEX_COLOR_PATTERN.test(color) ? `${color}${FILL_ALPHA_HEX}` : color;
  }

  function convertToTimestamp(timeUtc: string): UTCTimestamp {
    return (Date.parse(timeUtc) / MILLISECONDS_PER_SECOND) as UTCTimestamp;
  }

  function computeDrawdown(equityPoints: EquityPoint[]): LineData<UTCTimestamp>[] {
    let highestEquity = 0;
    return equityPoints.map((point) => {
      const equity = Number(point.equity_usd);
      highestEquity = Math.max(highestEquity, equity);
      const drawdownPercent = highestEquity > 0 ? (equity / highestEquity - 1) * PERCENT : 0;
      return { time: convertToTimestamp(point.time_utc), value: drawdownPercent };
    });
  }

  function readThemeOptions(): DeepPartial<ChartOptions> {
    const gridColor = readColor('--cds-border-subtle-01');
    return {
      layout: {
        background: { color: readColor('--cds-background') },
        textColor: readColor('--cds-text-secondary'),
        fontFamily: getComputedStyle(chartContainer).fontFamily,
        panes: { separatorColor: readColor('--cds-border-subtle-01') },
      },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor },
    };
  }

  $effect(() => {
    const themeOptions = readThemeOptions();
    const chart = createChart(chartContainer, {
      autoSize: true,
      layout: { ...themeOptions.layout, attributionLogo: true },
      grid: themeOptions.grid,
      rightPriceScale: themeOptions.rightPriceScale,
      timeScale: { ...themeOptions.timeScale, timeVisible: false },
    });
    const equitySeries: ISeriesApi<'Line'> = chart.addSeries(LineSeries, {
      color: readColor('--cds-text-primary'),
      lineWidth: 2,
      title: 'Equity',
      priceLineVisible: false,
    });
    equitySeries.setData(
      points.map((point) => ({ time: convertToTimestamp(point.time_utc), value: Number(point.equity_usd) })),
    );
    const drawdownSeries: ISeriesApi<'Area'> = chart.addSeries(
      AreaSeries,
      {
        lineColor: readColor('--cds-support-error'),
        topColor: readFillColor('--cds-support-error'),
        bottomColor: readFillColor('--cds-support-error'),
        invertFilledArea: true,
        lineWidth: 1,
        title: 'Drawdown %',
        priceLineVisible: false,
        priceFormat: { type: 'percent' },
      },
      1,
    );
    drawdownSeries.setData(computeDrawdown(points));
    const [equityPane, drawdownPane] = chart.panes();
    equityPane?.setStretchFactor(EQUITY_PANE_STRETCH);
    drawdownPane?.setStretchFactor(DRAWDOWN_PANE_STRETCH);
    chart.timeScale().fitContent();
    const endColorSchemeWatch = watchColorScheme(() => {
      chart.applyOptions(readThemeOptions());
      equitySeries.applyOptions({ color: readColor('--cds-text-primary') });
      drawdownSeries.applyOptions({
        lineColor: readColor('--cds-support-error'),
        topColor: readFillColor('--cds-support-error'),
        bottomColor: readFillColor('--cds-support-error'),
      });
    });
    return () => {
      endColorSchemeWatch();
      chart.remove();
    };
  });
</script>

<div class="chart-canvas" role="img" aria-label={label} bind:this={chartContainer}></div>

<style>
  .chart-canvas {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }
</style>
