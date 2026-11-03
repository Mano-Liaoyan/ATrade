<!-- Backtest page: a workbench (foundation/workbench, spec #99) with the backtest list and the open backtest on one
     page, like QuantConnect. URL: /backtests/<id>; /backtests opens the newest backtest.
     Left: the "Backtests" side column (BacktestList) with the "New backtest" and "Backtest limits" buttons. Center:
     the panel of the open backtest (header line: number, strategy version, instrument, bar period, status, and the
     "Start forward test" button; then the key metric row and the equity and drawdown curves on one time axis) over the
     Trades / Orders / Logs / Metrics / Bar sources panel. The API has no orders, so Orders is an empty state. Logs
     shows the strategy error. Metrics shows the metric table (docs/architecture/backtest.md section 10.9.6). Bar
     sources shows the source order and the bar counts. An HK backtest and a US backtest before the Databento history
     show the survivorship bias warning over the key metrics. A backtest that used instruments that waited for the IBKR
     stock split check shows its warning there too.
     The list reads again after each backtest change that /ws/backtests pushes; the open backtest reads again when its
     list row changes. The address #start-backtest (command palette) opens the New backtest dialog.
     A single-instrument backtest has the "Equity" / "Bars" switcher (?chart=bars): "Bars" shows the bar chart of the
     backtest range with the strategy indicators (docs/architecture/indicator.md section 23.9.8) and a mark for each
     trade (section 23.9.9). Then the pointer or the focus on a Trades row gives its mark the focus ring, and a click
     on a row selects it, shows "Bars", and scrolls the chart to the bar of the trade.
     Right: the "AI assistant" side column (routes/assistant/, docs/architecture/assistant.md 25.12). -->
<script lang="ts">
  import { untrack } from 'svelte';
  import Add16 from '@carbon/icons/es/add/16.js';
  import ConnectionSignal16 from '@carbon/icons/es/connection-signal/16.js';
  import Settings16 from '@carbon/icons/es/settings/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import {
    BACKTESTS_SOCKET_PATH,
    ChartViewSwitcher,
    formatChartViewSearch,
    readChartView,
    type ChartView,
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
  import { readOnChange } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import { isLiveBarPeriod, startForwardTest } from '#lib/forward_test';
  import {
    AddIndicatorButton,
    ChartIndicatorSetStore,
    formatInstrument,
    listChartTrades,
    RunBarChart,
    RunChartIndicators,
    SplitCheckWarning,
    type ChartIndicatorDefinition,
    SurvivorshipBiasWarning,
    type ChartPane,
  } from '#lib/market_data';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../instrument_href';
  import { START_BACKTEST_FORM_ID } from '../../palette_commands';
  import BacktestList from '../BacktestList.svelte';
  import BarSourceTable from '../BarSourceTable.svelte';
  import StartBacktestDialog from '../StartBacktestDialog.svelte';
  import AssistantColumn from '../../assistant/AssistantColumn.svelte';

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

  const chartView = $derived(readChartView(page.url.searchParams));
  // The Trades row under the pointer or the focus, and the selected row of the open backtest (section 23.9.9).
  let pointedTradeRow: number | null = $state(null);
  let selectedTrade = $state<{ backtestId: number; row: number } | null>(null);
  const selectedTradeRow = $derived(selectedTrade?.backtestId === backtestId ? selectedTrade.row : null);
  const chartTrades = $derived(listChartTrades(shownBacktest?.trades ?? []));
  const ringTrades = $derived(
    [pointedTradeRow, selectedTradeRow].flatMap((row) => (row === null ? [] : [chartTrades.tradeIndexByRow[row] ?? null])).filter((index) => index !== null),
  );

  function selectTradeRow(row: number): void {
    if (backtestId === null) {
      return;
    }
    selectedTrade = { backtestId, row };
    if (chartView !== 'bars') {
      changeChartView('bars');
    }
  }
  // The indicators of the bar chart: the strategy indicators, and the changes of the user for the open backtest.
  const chartIndicators = new RunChartIndicators();
  $effect(() => {
    chartIndicators.loadCatalog(fetch);
  });
  // Only the favorites of the saved chart indicator set (indicator.md section 23.9.8). The run panes are not saved.
  const chartIndicatorSet = new ChartIndicatorSetStore();
  $effect(() => {
    void chartIndicatorSet.load(fetch);
  });

  function changeChartView(view: ChartView): void {
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the current path with a new search.
    void goto(page.url.pathname + formatChartViewSearch(page.url.searchParams, view), { replace: true, reset: false });
  }

  // /ws/backtests pushes each change of a backtest, also from other tabs, the assistant, and the backtest process.
  $effect(() =>
    readOnChange({
      socketPath: BACKTESTS_SOCKET_PATH,
      read: () => listBacktests(fetch),
      onResult: (result) => {
        isListRead = true;
        if (result.kind === 'failed') {
          listMessage = result.message;
          return;
        }
        listMessage = '';
        backtests = result.value;
      },
    }),
  );

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

  // The open backtest reads again when its list row changes (status or metrics): the list comes from /ws/backtests.
  const openListRowText = $derived(JSON.stringify(backtests.find((item) => item.id === backtestId) ?? null));

  $effect(() => {
    if (backtestId === null) {
      return;
    }
    openListRowText satisfies string;
    const id = backtestId;
    // A final backtest does not change any more.
    const shown = untrack(() => backtest);
    if (shown !== null && shown.id === id && isFinalStatus(shown.status)) {
      return;
    }
    let isActive = true;
    void readBacktest(fetch, id).then((result) => {
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        detailMessage = result.message;
        return;
      }
      detailMessage = '';
      backtest = result.value;
    });
    return () => {
      isActive = false;
    };
  });

  // A new open backtest has no failed start of a forward test.
  $effect(() => {
    backtestId satisfies number | null;
    forwardTestMessage = '';
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

  // A deleted open backtest: /backtests opens the newest backtest that is left.
  function removeDeletedBacktests(deletedIds: number[]): void {
    backtests = backtests.filter((item) => !deletedIds.includes(item.id));
    if (backtestId !== null && deletedIds.includes(backtestId)) {
      void goto(resolve('/backtests/[[backtestId]]', { backtestId: undefined }), { replace: true });
    }
  }

  function openStartedBacktest(started: Backtest): void {
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
    <BacktestList {backtests} errorMessage={listMessage} openBacktestId={backtestId} onDeleted={removeDeletedBacktests} />
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
    {@const chartKey = String(detail.id)}
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
                {#if instrument !== undefined}
                  <ChartViewSwitcher value={chartView} onValueChange={changeChartView} />
                {/if}
                {#if chartView === 'bars' && instrument !== undefined}
                  <AddIndicatorButton
                    catalog={chartIndicators.catalog}
                    favorites={chartIndicatorSet.favorites}
                    onToggleFavorite={(key: string) => {
                      chartIndicatorSet.toggleFavorite(fetch, key);
                    }}
                    onAdd={(definition: ChartIndicatorDefinition) => {
                      chartIndicators.add(chartKey, detail.strategy_indicators, definition);
                    }}
                  />
                {/if}
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
            {#if detail.has_split_check_pending}
              <SplitCheckWarning />
            {/if}
            {#if detail.metrics !== null}
              <KeyMetricRow metrics={detail.metrics} startCapitalUsd={detail.paper_capital_usd} />
            {/if}
            {#if chartView === 'bars' && instrument !== undefined}
              <div class="chart">
                <RunBarChart
                  {instrument}
                  barPeriod={detail.bar_period}
                  range={{ startUtc: detail.start_utc, endUtc: detail.end_utc, sourceOrder: detail.source_order }}
                  label="Bar chart of {formatInstrument(instrument)}, {detail.bar_period} bars"
                  catalog={chartIndicators.catalog}
                  panes={chartIndicators.readPanes(chartKey, detail.strategy_indicators)}
                  onPanesChange={(panes: ChartPane[]) => {
                    chartIndicators.changePanes(chartKey, panes);
                  }}
                  trades={chartTrades.trades}
                  {ringTrades}
                  centerTrade={selectedTradeRow === null ? null : (chartTrades.tradeIndexByRow[selectedTradeRow] ?? null)}
                />
              </div>
            {:else if detail.metrics !== null}
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
              {#if instrument === undefined}
                <BacktestTradeTable trades={detail.trades} />
              {:else}
                <BacktestTradeTable
                  trades={detail.trades}
                  selectedIndex={selectedTradeRow}
                  onRowPoint={(row: number | null) => {
                    pointedTradeRow = row;
                  }}
                  onRowSelect={selectTradeRow}
                />
              {/if}
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
    gap: var(--cds-spacing-02);
    align-items: center;
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
