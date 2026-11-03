<!-- The bar chart of a backtest or a forward test (docs/architecture/indicator.md section 23.9.8): the saved bars of
     one instrument and bar period in a fixed range, read with the source order of the run, and the indicators of
     `panes`. The page holds the panes (the strategy indicators and the changes of the user, not saved) and the
     "Add indicator" button of the header line. `trades` gives the trade marks (section 23.9.9); the page gives the
     trades of its table row under the pointer or the focus (`ringTrades`) and the selected row (`centerTrade`). -->
<script lang="ts">
  import { untrack } from 'svelte';
  import { InlineNotification } from '#lib/foundation/carbon';
  import BarChart from './BarChart.svelte';
  import { readBars, type BarPeriod, type BarsRange, type BarsResult } from './bars';
  import type { ChartIndicatorDefinition, ChartPane } from './chart_indicators';
  import { listSeriesIndicators, readIndicatorSeries, type IndicatorSeriesResult } from './indicator_series';
  import type { Instrument } from './instrument_search';
  import type { ChartTrade } from './trade_marks';

  interface Props {
    instrument: Instrument;
    barPeriod: BarPeriod;
    range: BarsRange;
    label: string;
    catalog: ChartIndicatorDefinition[];
    panes: ChartPane[];
    onPanesChange: (panes: ChartPane[]) => void;
    trades?: ChartTrade[];
    ringTrades?: number[];
    centerTrade?: number | null;
  }

  const { instrument, barPeriod, range, label, catalog, panes, onPanesChange, trades = [], ringTrades = [], centerTrade = null }: Props = $props();

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
    void readBars(fetch, request.instrument, request.barPeriod, request.range).then((result) => {
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
    void readIndicatorSeries(fetch, {
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
<BarChart {bars} fill {label} indicatorPanes={panes} {indicatorSeries} {catalog} {onPanesChange} {trades} {barPeriod} {ringTrades} {centerTrade} />
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
