<!-- Backtest page: a workbench (foundation/workbench, spec #99) with the backtest list and the open backtest on one
     page, like QuantConnect. URL: /backtests/<id>; /backtests opens the newest backtest.
     Left: the "Backtests" side column (BacktestList) with the "New backtest" and "Backtest limits" buttons. Center:
     the panel of the open backtest (header line: number, strategy version, instrument, bar period, status, and the
     "Start forward test" button; then the key metric row and the equity and drawdown curves on one time axis) over the
     Trades / Orders / Logs / Metrics / Bar sources panel. The API has no orders, so Orders is an empty state. Logs
     shows the strategy error. Metrics shows the metric table (docs/architecture/backtest.md section 10.9.6). Bar
     sources shows the source order and the bar counts. An HK backtest and a US backtest before the Databento history
     show the survivorship bias warning over the key metrics.
     The list reads again while a backtest in it is queued or running; the open backtest reads again until its status
     is final. The address #start-backtest (command palette) opens the New backtest dialog.
     Right: the "AI assistant" side column (routes/assistant/, docs/architecture/assistant.md 25.12). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import ConnectionSignal16 from '@carbon/icons/es/connection-signal/16.js';
  import Settings16 from '@carbon/icons/es/settings/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import {
    BacktestLimitsForm,
    BacktestMetricTable,
    BacktestTradeTable,
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    formatPeriodCountHeader,
    formatUniverseLabel,
    isFinalStatus,
    KeyMetricRow,
    listBacktests,
    readBacktest,
    readBacktestInstrument,
    UniverseInstrumentTable,
    type Backtest,
    type BacktestDetail,
    type BacktestInstrument,
  } from '#lib/backtest';
  import { Dialog, IconButton, InlineNotification, StatusIndicator } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { startPolling } from '#lib/foundation/polling';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { isLiveBarPeriod, startForwardTest } from '#lib/forward_test';
  import { SurvivorshipBiasWarning } from '#lib/market_data';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../instrument_href';
  import { START_BACKTEST_FORM_ID } from '../../palette_commands';
  import BacktestList from '../BacktestList.svelte';
  import BarSourceTable from '../BarSourceTable.svelte';
  import StartBacktestDialog from '../StartBacktestDialog.svelte';
  import AssistantColumn from '../../assistant/AssistantColumn.svelte';

  // A backtest of a few years of daily bars ends in seconds. One read each second is enough.
  const STATUS_CHECK_INTERVAL_MILLISECONDS = 1000;
  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  const START_BACKTEST_HASH = `#${START_BACKTEST_FORM_ID}`;

  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 160 },
    { id: 'tables', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the tables' },
  ];
  type BacktestTable = 'trades' | 'instruments' | 'orders' | 'logs' | 'metrics' | 'bar-sources';
  const TABLE_TABS: { value: BacktestTable; label: string }[] = [
    { value: 'trades', label: 'Trades' },
    { value: 'instruments', label: 'Instruments' },
    { value: 'orders', label: 'Orders' },
    { value: 'logs', label: 'Logs' },
    { value: 'metrics', label: 'Metrics' },
    { value: 'bar-sources', label: 'Bar sources' },
  ];

  const routeBacktestId = $derived(page.params['backtestId']);
  const backtestId = $derived(routeBacktestId === undefined ? null : Number(routeBacktestId));

  let backtests: Backtest[] = $state([]);
  let isListRead = $state(false);
  let listMessage = $state('');
  // A new value reads the list again, for example after a new backtest starts.
  let listReadCount = $state(0);
  let backtest = $state<BacktestDetail | null>(null);
  let detailMessage = $state('');
  let selectedTable: BacktestTable = $state('trades');
  let isStartDialogOpen = $state(false);
  let isLimitsDialogOpen = $state(false);
  let forwardTestMessage = $state('');
  let isStartingForwardTest = $state(false);

  const shownBacktest = $derived(backtest !== null && backtest.id === backtestId ? backtest : null);
  // A forward test runs on live bars: the bar period of the backtest must be a live bar period.
  const hasLiveBarPeriod = $derived(shownBacktest !== null && isLiveBarPeriod(shownBacktest.bar_period));

  $effect(() => {
    // A new read count runs this effect again: its cleanup stops the old loop.
    listReadCount satisfies number;
    return startPolling(
      () => listBacktests(fetch),
      (result) => {
        isListRead = true;
        if (result.kind === 'failed') {
          listMessage = result.message;
          return true;
        }
        listMessage = '';
        backtests = result.value;
        return result.value.some((item) => !isFinalStatus(item.status));
      },
      LIST_CHECK_INTERVAL_MILLISECONDS,
      (message) => {
        listMessage = message;
      },
    );
  });

  // /backtests opens the newest backtest. The same page component stays, so an open dialog stays open. A navigation
  // that runs (for example a click on a header link) wins.
  $effect(() => {
    if (navigating.to !== null) {
      return;
    }
    const newest = backtests.reduce<Backtest | undefined>(
      (found, item) => (found === undefined || item.id > found.id ? item : found),
      undefined,
    );
    if (backtestId === null && newest !== undefined) {
      void goto(resolve('/backtests/[[backtestId]]', { backtestId: String(newest.id) }), {
        replace: true,
        reset: false,
      });
    }
  });

  // The open backtest reads again until its status is final.
  $effect(() => {
    if (backtestId === null) {
      return;
    }
    const id = backtestId;
    forwardTestMessage = '';
    return startPolling(
      () => readBacktest(fetch, id),
      (result) => {
        if (result.kind === 'failed') {
          detailMessage = result.message;
          return true;
        }
        detailMessage = '';
        backtest = result.value;
        return !isFinalStatus(result.value.status);
      },
      STATUS_CHECK_INTERVAL_MILLISECONDS,
      (message) => {
        detailMessage = message;
      },
    );
  });

  // The command palette goes to #start-backtest.
  $effect(() => {
    if (page.url.hash === START_BACKTEST_HASH) {
      isStartDialogOpen = true;
    }
  });

  function changeStartDialog(open: boolean): void {
    isStartDialogOpen = open;
    if (!open && page.url.hash === START_BACKTEST_HASH) {
      // Without the hash, the palette can open the dialog again.
      // eslint-disable-next-line svelte/no-navigation-without-resolve -- the current path, without its hash.
      void goto(page.url.pathname + page.url.search, { replace: true, reset: false });
    }
  }

  function openStartedBacktest(started: Backtest): void {
    listReadCount += 1;
    void goto(resolve('/backtests/[[backtestId]]', { backtestId: String(started.id) }));
  }

  async function startForwardTestFromBacktest(detail: BacktestDetail, instrument: BacktestInstrument): Promise<void> {
    if (isStartingForwardTest) {
      return;
    }
    isStartingForwardTest = true;
    forwardTestMessage = '';
    const result = await startForwardTest(fetch, {
      strategy_version_id: detail.strategy_version_id,
      symbol: instrument.symbol,
      exchange: instrument.exchange,
      currency: instrument.currency,
      bar_period: detail.bar_period,
      // The paper capital of the backtest is the allocated capital of the forward test (forward_test.md 12.18).
      allocated_capital_usd: detail.paper_capital_usd,
    });
    isStartingForwardTest = false;
    if (result.kind === 'failed') {
      forwardTestMessage = result.message;
      return;
    }
    await goto(resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(result.forwardTest.id) }));
  }

  function describeForwardTestButton(detail: BacktestDetail, instrument: BacktestInstrument | undefined): string {
    if (instrument === undefined) {
      return 'Start forward test: not available for a multi-instrument backtest';
    }
    if (!hasLiveBarPeriod) {
      return `Start forward test: not available for ${formatBarPeriod(detail.bar_period)} bars`;
    }
    return isStartingForwardTest ? 'Starting forward test…' : 'Start forward test';
  }
</script>

<Workbench>
  <SideColumn label="Backtests" side="start" width="36rem" storageKey="atrade.backtest-page.list-column">
    {#snippet actions()}
      <IconButton
        label="New backtest"
        icon={Add16}
        onclick={() => {
          isStartDialogOpen = true;
        }}
      />
      <IconButton
        label="Backtest limits"
        icon={Settings16}
        onclick={() => {
          isLimitsDialogOpen = true;
        }}
      />
    {/snippet}
    <BacktestList {backtests} errorMessage={listMessage} openBacktestId={backtestId} />
  </SideColumn>

  {#if shownBacktest === null}
    <div class="empty-main">
      {#if detailMessage !== ''}
        <InlineNotification kind="error" title="Backtest not read" subtitle={detailMessage} lowContrast />
      {:else if isListRead && backtests.length === 0 && listMessage === ''}
        <EmptyText text="No backtests" />
      {/if}
    </div>
  {:else}
    {@const detail = shownBacktest}
    {@const instrument = readBacktestInstrument(detail)}
    {@const universeLabel = formatUniverseLabel(detail, detail.instruments.length)}
    <PanelSplit storageKey="atrade.backtest-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'chart'}
          <Panel {...state} label={`Backtest #${String(detail.id)}`}>
            {#snippet header()}
              <span class="run-status" role="status" aria-label="Backtest status">
                <StatusIndicator label={describeBacktestStatus(detail.status)} kind={findBacktestStatusKind(detail.status)} />
              </span>
              <h1 class="run-title">
                <span class="run-number">#{detail.id}</span>
                <a class="cds--link" href={resolve('/strategies/[strategyId]/versions/[versionNumber]', { strategyId: String(detail.strategy_id), versionNumber: String(detail.version_number) })}
                  >{formatVersionLabel(detail.strategy_name, detail.version_number)}</a
                >
                {#if instrument !== undefined}
                  <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolves the path. -->
                  <a class="cds--link" href={createInstrumentHref(instrument)}>{instrument.symbol}</a>
                {:else if universeLabel !== undefined}
                  <span>{universeLabel}</span>
                {/if}
                <span class="run-period">{formatBarPeriod(detail.bar_period)}</span>
                {#if detail.sweep_id !== null}
                  <a class="cds--link" href={resolve('/sweeps/[[sweepId]]', { sweepId: String(detail.sweep_id) })}
                    >Parameter sweep #{detail.sweep_id}</a
                  >
                {/if}
              </h1>
              <span class="run-actions">
                <IconButton
                  label={describeForwardTestButton(detail, instrument)}
                  icon={ConnectionSignal16}
                  tone="interactive"
                  disabled={instrument === undefined || !hasLiveBarPeriod || isStartingForwardTest}
                  onclick={() => {
                    if (instrument !== undefined) {
                      void startForwardTestFromBacktest(detail, instrument);
                    }
                  }}
                />
              </span>
            {/snippet}
            {#if forwardTestMessage !== ''}
              <InlineNotification
                kind="error"
                title="Forward test not started"
                subtitle={forwardTestMessage}
                lowContrast
                onClose={() => {
                  forwardTestMessage = '';
                }}
              />
            {/if}
            {#if detail.survivorship_bias}
              <SurvivorshipBiasWarning />
            {/if}
            {#if detail.metrics !== null}
              <KeyMetricRow metrics={detail.metrics} startCapitalUsd={detail.paper_capital_usd} />
              <div class="chart">
                <EquityDrawdownChart
                  curves={[{ name: 'Equity', points: detail.equity_curve, startCapitalUsd: detail.paper_capital_usd }]}
                  label="Equity and drawdown"
                  fill
                />
              </div>
            {/if}
          </Panel>
        {:else}
          <Panel
            {...state}
            label="Backtest tables"
            tabs={{
              label: 'Backtest tables',
              items: TABLE_TABS,
              value: selectedTable,
              onValueChange: (value: string) => {
                selectedTable = value as BacktestTable;
              },
            }}
          >
            {#if selectedTable === 'trades'}
              <BacktestTradeTable trades={detail.trades} />
            {:else if selectedTable === 'instruments'}
              <UniverseInstrumentTable instruments={detail.instruments} periodHeader={formatPeriodCountHeader(detail)} />
            {:else if selectedTable === 'orders'}
              <EmptyText text="No orders" />
            {:else if selectedTable === 'metrics'}
              {#if detail.metrics === null}
                <EmptyText text="No metrics" />
              {:else}
                <BacktestMetricTable metrics={detail.metrics} />
              {/if}
            {:else if selectedTable === 'bar-sources'}
              <BarSourceTable sourceOrder={detail.source_order} barCountBySource={detail.bar_count_by_source} />
            {:else if detail.error_message === null}
              <EmptyText text="No logs" />
            {:else}
              <ScrollRegion label="Logs" fill>
                <pre class="log-text">{detail.error_message}</pre>
              </ScrollRegion>
            {/if}
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>
  {/if}

  <AssistantColumn />
</Workbench>

<StartBacktestDialog open={isStartDialogOpen} onOpenChange={changeStartDialog} onStarted={openStartedBacktest} />

<Dialog
  open={isLimitsDialogOpen}
  onOpenChange={(open: boolean) => {
    isLimitsDialogOpen = open;
  }}
  title="Backtest limits"
>
  {#if isLimitsDialogOpen}
    <BacktestLimitsForm />
  {/if}
</Dialog>

<style>
  .empty-main {
    flex: 1;
    min-inline-size: 0;
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: var(--cds-spacing-04);
  }

  /* One type size in the heading: Carbon links set their own size. */
  .run-title > :global(*) {
    font: inherit;
    letter-spacing: inherit;
  }

  .run-number {
    font-variant-numeric: tabular-nums;
    color: var(--cds-text-secondary);
  }

  .run-period {
    color: var(--cds-text-secondary);
  }

  .run-status {
    display: flex;
    flex: none;
  }

  .run-actions {
    display: flex;
    flex: none;
    margin-inline-start: auto;
  }

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .log-text {
    margin: 0;
    padding: var(--cds-spacing-05);
    color: var(--cds-text-error);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    white-space: pre-wrap;
  }
</style>
