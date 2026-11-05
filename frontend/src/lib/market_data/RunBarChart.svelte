<!-- The bar chart of a backtest or a forward test (docs/architecture/indicator.md section 23.9.8): the saved bars of
     one instrument and bar period in a fixed range, read with the source order of the run (a long range in windows,
     `run_bars.ts`), and the run panes of `chart` (the strategy indicators and the changes of the user, not saved).
     `records` (the trades or the fills of the table) give the trade marks (section 23.9.9). The table row under the
     pointer or the focus and the selected row (`chart`) ring their marks; the selected row centers its mark. With
     `isUniverseMember`, `instrument` is one member of a multi-instrument run: only its records get marks. -->
<script lang="ts">
  import { untrack } from 'svelte';
  import { InlineNotification } from '#lib/foundation/carbon';
  import BarChart from './BarChart.svelte';
  import type { BarPeriod, BarsRange, BarsResult } from './bars';
  import type { ChartPane } from './chart_indicators';
  import { listSeriesIndicators, type IndicatorSeriesResult } from './indicator_series';
  import type { Instrument } from './instrument_search';
  import { readRunBars, readRunIndicatorSeries } from './run_bars';
  import { findRingTrades, findRowTrade, type RunChart } from './run_chart.svelte';
  import type { StrategyIndicator } from './strategy_indicators';
  import { listChartTrades, type TradeRecord } from './trade_marks';

  interface Props {
    instrument: Instrument;
    barPeriod: BarPeriod;
    range: BarsRange;
    label: string;
    chart: RunChart;
    /** The run id. */
    runKey: string;
    strategyIndicators: readonly StrategyIndicator[];
    records: readonly TradeRecord[];
    isUniverseMember?: boolean;
  }

  const { instrument, barPeriod, range, label, chart, runKey, strategyIndicators, records, isUniverseMember = false }: Props = $props();

  const panes = $derived(chart.indicators.readPanes(runKey, strategyIndicators));
  const chartTrades = $derived(listChartTrades(records, isUniverseMember ? instrument : undefined));
  const selectedRow = $derived(chart.readSelectedRow(runKey));
  const ringTrades = $derived(findRingTrades(chartTrades.tradeIndexByRow, chart.pointedRow, selectedRow));
  const centerTrade = $derived(findRowTrade(chartTrades.tradeIndexByRow, selectedRow));

  function changePanes(nextPanes: ChartPane[]): void {
    chart.indicators.changePanes(runKey, nextPanes);
  }

  // The bars and the series keep the request that they belong to, so a new run shows no data of the run before.
  const barsKey = $derived(
    JSON.stringify([instrument.symbol, instrument.exchange, instrument.currency, barPeriod, range.startUtc, range.endUtc ?? null, range.sourceOrder ?? null]),
  );
  let loadedBars: { key: string; result: BarsResult } | undefined = $state();
  const barsResult = $derived(loadedBars?.key === barsKey ? loadedBars.result : undefined);
  const bars = $derived(barsResult?.kind === 'loaded' ? barsResult.bars : []);

  // The effects run again only for a new key: the page gives new objects for the same run after each read.
  $effect(() => {
    const key = barsKey;
    let isCurrent = true;
    const request = untrack(() => ({ instrument, barPeriod, range }));
    void readRunBars(fetch, request.instrument, request.barPeriod, request.range).then((result) => {
      if (isCurrent) {
        loadedBars = { key, result };
      }
    });
    return () => {
      isCurrent = false;
    };
  });

  let loadedSeries: { key: string; result: IndicatorSeriesResult } | undefined = $state();
  let seriesError: { key: string; message: string } | undefined = $state();
  const indicatorSeries = $derived(loadedSeries?.key === barsKey ? loadedSeries.result : null);
  const seriesErrorText = $derived(seriesError?.key === barsKey ? seriesError.message : null);

  // The series route reads only saved bars, so it runs after the bars route answered.
  $effect(() => {
    const indicators = listSeriesIndicators(panes);
    const firstBar = bars.at(0);
    const lastBar = bars.at(-1);
    if (firstBar === undefined || lastBar === undefined || indicators.length === 0) {
      return;
    }
    const key = barsKey;
    let isCurrent = true;
    const request = untrack(() => ({ instrument, barPeriod, sourceOrder: range.sourceOrder }));
    void readRunIndicatorSeries(fetch, {
      instrument: request.instrument,
      barPeriod: request.barPeriod,
      firstBarTime: firstBar.time,
      lastBarTime: lastBar.time,
      ...(request.sourceOrder === undefined || request.sourceOrder === null ? {} : { sourceOrder: request.sourceOrder }),
      indicators,
    }).then((result) => {
      if (!isCurrent) {
        return;
      }
      if (result.kind === 'ok') {
        loadedSeries = { key, result: result.value };
        seriesError = undefined;
      } else {
        seriesError = { key, message: result.message };
      }
    });
    return () => {
      isCurrent = false;
    };
  });
</script>

<div class="cds--visually-hidden">
  {#if barsResult?.kind === 'loaded'}
    <span role="status" aria-label="Bar count">{bars.length === 1 ? '1 bar' : `${String(bars.length)} bars`}</span>
  {/if}
</div>
<BarChart
  {bars}
  fill
  {label}
  indicatorPanes={panes}
  {indicatorSeries}
  catalog={chart.indicators.catalog}
  onPanesChange={changePanes}
  trades={chartTrades.trades}
  {barPeriod}
  {ringTrades}
  {centerTrade}
/>
{#if barsResult === undefined}
  <p class="chart-message" role="status">Loading bars.</p>
{:else if barsResult.kind === 'failed'}
  <div class="chart-message"><InlineNotification kind="error" title={barsResult.message} lowContrast /></div>
{:else if seriesErrorText !== null}
  <div class="chart-message"><InlineNotification kind="error" title={seriesErrorText} lowContrast /></div>
{/if}

<style>
  .chart-message {
    position: absolute;
    inset-block-start: var(--cds-spacing-05);
    inset-inline-start: var(--cds-spacing-07);
    margin: 0;
    padding: var(--cds-spacing-02) var(--cds-spacing-03);
    background: var(--cds-layer-01);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  /* An error notification over the chart: the notification has its own background and padding. */
  div.chart-message {
    padding: 0;
    background: none;
  }
</style>
