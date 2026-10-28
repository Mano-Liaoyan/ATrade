<!-- PROTOTYPE (#99), throwaway: the equity curve with the drawdown below it on the same time axis. It fills the height
     of its parent. Lightweight Charts by TradingView (Apache License 2.0); the chart shows the TradingView logo. -->
<script lang="ts">
  import {
    AreaSeries,
    createChart,
    LineSeries,
    type ChartOptions,
    type DeepPartial,
    type UTCTimestamp,
  } from 'lightweight-charts';
  import type { EquityPoint } from '#lib/backtest';
  import { watchColorScheme } from '#lib/foundation/color_scheme';
  import { computeDrawdown } from './workbench_layout';

  const { points, label }: { points: EquityPoint[]; label: string } = $props();

  const MILLISECONDS_PER_SECOND = 1000;
  const EQUITY_PANE_STRETCH = 3;
  const DRAWDOWN_PANE_INDEX = 1;

  let chartContainer: HTMLDivElement;

  function readColor(variableName: string): string {
    return getComputedStyle(chartContainer).getPropertyValue(variableName).trim();
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
      timeScale: { ...themeOptions.timeScale, timeVisible: true, secondsVisible: false },
    });
    const equitySeries = chart.addSeries(LineSeries, { color: readColor('--cds-text-primary'), title: 'Equity' });
    equitySeries.setData(
      points.map((point) => ({ time: convertToTimestamp(point.time_utc), value: Number(point.equity_usd) })),
    );
    const drawdownSeries = chart.addSeries(
      AreaSeries,
      {
        lineColor: readColor('--cds-support-error'),
        topColor: readColor('--cds-layer-accent-01'),
        bottomColor: readColor('--cds-layer-accent-01'),
        invertFilledArea: true,
        title: 'Drawdown %',
      },
      DRAWDOWN_PANE_INDEX,
    );
    drawdownSeries.setData(
      computeDrawdown(points).map((point) => ({
        time: convertToTimestamp(point.time_utc),
        value: point.drawdown_percent,
      })),
    );
    chart.panes()[0]?.setStretchFactor(EQUITY_PANE_STRETCH);
    chart.timeScale().fitContent();
    const endColorSchemeWatch = watchColorScheme(() => {
      chart.applyOptions(readThemeOptions());
      equitySeries.applyOptions({ color: readColor('--cds-text-primary') });
      drawdownSeries.applyOptions({
        lineColor: readColor('--cds-support-error'),
        topColor: readColor('--cds-layer-accent-01'),
        bottomColor: readColor('--cds-layer-accent-01'),
      });
    });
    return () => {
      endColorSchemeWatch();
      chart.remove();
    };
  });
</script>

<div class="run-chart" role="img" aria-label={label} bind:this={chartContainer}></div>

<style>
  .run-chart {
    position: relative;
    block-size: 100%;
    min-block-size: 0;
    overflow: hidden;
  }
</style>
