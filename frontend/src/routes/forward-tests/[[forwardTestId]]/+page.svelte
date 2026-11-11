<!-- Forward test page: a workbench (foundation/workbench, spec #99) with the structure of the backtest page. URL:
     /forward-tests/<id>; /forward-tests opens the newest forward test.
     Left: the "Forward tests" side column (ForwardTestList, live from /ws/forward-tests) with the "New forward test"
     button. Center: the panel of the open forward test (header line: number, strategy version, instrument, bar
     period, status, the allocated capital, "Split check needed: AAPL" while an instrument needs a split check, the red "Stop forward test" button while it can stop, "Backtest the same period", and "Delete forward test" after the end (a danger dialog asks first); then the
     key metric row and the equity and drawdown curves with the interruptions in grey) over the
     Fills / Comparison / Logs panel. Comparison links to the comparison with each backtest of the same period. Logs
     shows the current error and the events (start, interruptions, stop). The open forward test reads again every
     2 seconds. The address #start-forward-test (command palette) opens the New forward test dialog.
     A single-instrument forward test has the "Equity" / "Bars" switcher (?chart=bars): "Bars" shows the bar chart from
     the start to the stop, or to now, with the strategy indicators (docs/architecture/indicator.md section 23.9.8) and
     a mark for each fill (section 23.9.9). Then the pointer or the focus on a Fills row gives its mark the focus ring,
     and a click on a row selects it, shows "Bars", and scrolls the chart to the bar of the fill.
     Right: the "AI assistant" side column (routes/assistant/, docs/architecture/assistant.md 25.12). -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import Compare16 from '@carbon/icons/es/compare/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import {
    ChartViewSwitcher,
    formatChartViewSearch,
    readChartView,
    type ChartView,
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    formatPercent,
    KeyMetricRow,
    UniverseInstrumentTable,
    type TimeInterval,
  } from '#lib/backtest';
  import {
    DataTable,
    Dialog,
    IconButton,
    InlineNotification,
    StatusIndicator,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ChangeText, formatAmount, formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    FORWARD_TESTS_SOCKET_PATH,
    canBacktestSamePeriod,
    canDelete,
    canStop,
    deleteForwardTest,
    describeForwardTestStatus,
    describeForwardTestUniverse,
    readForwardTestInstrument,
    readStartCapital,
    findForwardTestStatusKind,
    ForwardTestFillTable,
    listForwardTestEvents,
    listForwardTests,
    readForwardTestDetail,
    showsCrashCount,
    startSamePeriodBacktest,
    stopForwardTest,
    type ForwardTest,
    type ForwardTestDetail,
  } from '#lib/forward_test';
  import {
    formatInstrument,
    RunAddIndicatorButton,
    RunBarChart,
    RunChart,
  } from '#lib/market_data';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../instrument_href';
  import { START_FORWARD_TEST_FORM_ID } from '../../palette_commands';
  import { RunWorkbench } from '../../run_workbench.svelte';
  import RunCenter from '../../RunCenter.svelte';
  import ForwardTestList from '../ForwardTestList.svelte';
  import StartForwardTestDialog from '../StartForwardTestDialog.svelte';
  import AssistantColumn from '../../assistant/AssistantColumn.svelte';

  // The same panels and sizes as the backtest page.
  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 160 },
    { id: 'tables', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the tables' },
  ];
  const COMPARISON_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Start' },
    { header: 'End' },
    { header: 'Return', align: 'right' },
  ];
  const EVENT_COLUMNS: TableColumn[] = [{ header: 'Time' }, { header: 'Event' }];
  type ForwardTestTable = 'fills' | 'instruments' | 'comparison' | 'logs';
  const TABLE_TABS: { value: ForwardTestTable; label: string }[] = [
    { value: 'fills', label: 'Fills' },
    { value: 'instruments', label: 'Instruments' },
    { value: 'comparison', label: 'Comparison' },
    { value: 'logs', label: 'Logs' },
  ];

  const routeForwardTestId = $derived(page.params['forwardTestId']);
  const forwardTestId = $derived(routeForwardTestId === undefined ? null : Number(routeForwardTestId));

  // The list and the open forward test read again after each forward test change that /ws/forward-tests pushes: a running
  // forward test gets new records.
  const workbench = new RunWorkbench<ForwardTest, ForwardTestDetail>({
    socketPath: FORWARD_TESTS_SOCKET_PATH,
    list: () => listForwardTests(fetch),
    readDetail: (id) => readForwardTestDetail(fetch, id),
    href: (id) => resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(id) }),
    openId: () => forwardTestId,
    readsDetailOnChange: true,
    startHash: `#${START_FORWARD_TEST_FORM_ID}`,
  });
  let selectedTable: ForwardTestTable = $state('fills');
  // The failed header action and the reason from the backend.
  let actionFailure = $state<{ title: string; message: string } | null>(null);
  let stoppingId = $state<number | null>(null);
  let isStartingBacktest = $state(false);
  // The forward test of the delete dialog: the open forward test, or the row of the list context menu.
  let deleteTarget = $state<ForwardTest | null>(null);
  let isDeleteDialogOpen = $state(false);
  let isDeleting = $state(false);

  const shownDetail = $derived(
    workbench.detail !== null && workbench.detail.forward_test.id === forwardTestId ? workbench.detail : null,
  );
  // An interruption that still lasts ends at the stop, or now (docs/architecture/forward_test.md 12.10).
  const chartInterruptions = $derived<TimeInterval[]>(
    (shownDetail?.forward_test.interruptions ?? []).map((interruption) => ({
      start_utc: interruption.started_at_utc,
      end_utc: interruption.ended_at_utc ?? shownDetail?.forward_test.stopped_at_utc ?? new Date().toISOString(),
    })),
  );

  const chartView = $derived(readChartView(page.url.searchParams));
  // The bar chart: the run indicators, the favorite indicators, and the link with the Fills rows (section 23.9.9).
  const runChart = new RunChart();
  $effect(() => {
    runChart.load(fetch);
  });

  function selectFillRow(row: number): void {
    if (forwardTestId === null) {
      return;
    }
    runChart.selectRow(String(forwardTestId), row);
    if (chartView !== 'bars') {
      changeChartView('bars');
    }
  }

  function changeChartView(view: ChartView): void {
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- the current path with a new search.
    void goto(page.url.pathname + formatChartViewSearch(page.url.searchParams, view), { replace: true, reset: false });
  }

  // A new open forward test has no failed action and no running stop.
  $effect(() => {
    if (forwardTestId !== null) {
      actionFailure = null;
      stoppingId = null;
    }
  });

  function openStartedForwardTest(started: ForwardTest): void {
    workbench.items = [started, ...workbench.items.filter((item) => item.id !== started.id)];
    void goto(resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(started.id) }));
  }

  async function stop(forwardTest: ForwardTest): Promise<void> {
    if (stoppingId !== null) {
      return;
    }
    stoppingId = forwardTest.id;
    actionFailure = null;
    const result = await stopForwardTest(fetch, forwardTest.id);
    stoppingId = null;
    if (result.kind === 'failed') {
      actionFailure = { title: 'Forward test not stopped', message: result.message };
      return;
    }
    // The socket pushes the list again later. The buttons show the accepted stop at once.
    workbench.items = workbench.items.map((item) =>
      item.id === forwardTest.id ? { ...item, desired_state: 'stopped' } : item,
    );
    if (workbench.detail?.forward_test.id === forwardTest.id) {
      workbench.detail = {
        ...workbench.detail,
        forward_test: { ...workbench.detail.forward_test, desired_state: 'stopped' },
      };
    }
  }

  // A normal backtest of the same strategy version, instrument, bar type, and period (docs/architecture 12.10).
  async function backtestSamePeriod(forwardTest: ForwardTest): Promise<void> {
    if (isStartingBacktest) {
      return;
    }
    isStartingBacktest = true;
    actionFailure = null;
    const result = await startSamePeriodBacktest(fetch, forwardTest.id);
    isStartingBacktest = false;
    if (result.kind === 'failed') {
      actionFailure = { title: 'Backtest not started', message: result.message };
      return;
    }
    await goto(
      resolve('/forward-tests/[forwardTestId]/comparison/[backtestId]', {
        forwardTestId: String(forwardTest.id),
        backtestId: String(result.backtestId),
      }),
    );
  }

  function requestDelete(forwardTest: ForwardTest): void {
    deleteTarget = forwardTest;
    isDeleteDialogOpen = true;
  }

  // After the delete of the open forward test, /forward-tests opens the newest forward test that is left.
  async function removeForwardTest(forwardTest: ForwardTest): Promise<void> {
    isDeleting = true;
    actionFailure = null;
    const result = await deleteForwardTest(fetch, forwardTest.id);
    isDeleting = false;
    isDeleteDialogOpen = false;
    if (result.kind === 'failed') {
      actionFailure = { title: 'Forward test not deleted', message: result.message };
      return;
    }
    workbench.removeItem(forwardTest.id);
    if (forwardTest.id === forwardTestId) {
      await goto(resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: undefined }), { replace: true });
    }
  }

  function describeStopButton(forwardTest: ForwardTest): string {
    return stoppingId === forwardTest.id ? 'Stopping forward test…' : 'Stop forward test';
  }

  function describeBacktestButton(forwardTest: ForwardTest): string {
    if (!canBacktestSamePeriod(forwardTest)) {
      return 'Backtest the same period: not available before the start balance is read';
    }
    return isStartingBacktest ? 'Starting backtest…' : 'Backtest the same period';
  }
</script>

{#snippet instrumentOrUniverse(forwardTest: ForwardTest, instrumentCount: number)}
  {@const instrument = readForwardTestInstrument(forwardTest)}
  {#if instrument === null}
    <span>{describeForwardTestUniverse(forwardTest, instrumentCount)}</span>
  {:else}
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolves the path. -->
    <a class="cds--link" href={createInstrumentHref(instrument)}>{instrument.symbol}</a>
  {/if}
{/snippet}

<Workbench>
  <SideColumn label="Forward tests" side="start" width="30rem" storageKey="atrade.forward-test-page.list-column">
    {#snippet actions()}
      <IconButton
        label="New forward test"
        icon={Add16}
        onclick={() => {
          workbench.isStartDialogOpen = true;
        }}
      />
    {/snippet}
    <LiveUpdatesNotification isConnected={workbench.isConnected} />
    <ForwardTestList
      forwardTests={workbench.items}
      openForwardTestId={forwardTestId}
      onStop={(forwardTest: ForwardTest) => void stop(forwardTest)}
      onDeleteRequest={requestDelete}
    />
  </SideColumn>

  <RunCenter {workbench} listTitle="Forward tests not read" detailTitle="Forward test not read">
    {#if shownDetail === null}
      <div class="atrade-run-empty">
        {#if workbench.isListRead && workbench.items.length === 0 && workbench.listMessage === '' && workbench.detailMessage === ''}
          <EmptyText text="No forward tests" />
        {/if}
      </div>
    {:else}
      {@const forwardTest = shownDetail.forward_test}
      {@const records = shownDetail}
      {@const chartInstrument = readForwardTestInstrument(forwardTest)}
      {@const chartKey = String(forwardTest.id)}
      <PanelSplit storageKey="atrade.forward-test-page.panel-split" panels={PANELS}>
        {#snippet panel(id, state)}
          {#if id === 'chart'}
            <Panel {...state} label={`Forward test #${String(forwardTest.id)}`}>
              {#snippet header()}
                <span class="atrade-run-status" role="status" aria-label="Forward test status">
                  <StatusIndicator
                    label={describeForwardTestStatus(forwardTest.status)}
                    kind={findForwardTestStatusKind(forwardTest.status)}
                  />
                  {#if showsCrashCount(forwardTest)}
                    <StatusIndicator kind="warning" label={`Crashes in a row: ${String(forwardTest.crash_count)} of 3`} />
                  {/if}
                  {#if forwardTest.split_checks_needed.length > 0}
                    <StatusIndicator
                      kind="warning"
                      label={`Split check needed: ${forwardTest.split_checks_needed.map((item) => item.symbol).join(', ')}`}
                    />
                  {/if}
                </span>
                <h1 class="atrade-run-title">
                  <span class="atrade-run-number">#{forwardTest.id}</span>
                  <a
                    class="cds--link"
                    href={resolve('/strategies/[strategyId]/versions/[versionNumber]', { strategyId: String(forwardTest.strategy_id), versionNumber: String(forwardTest.version_number) })}
                    >{formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}</a
                  >
                  {@render instrumentOrUniverse(forwardTest, records.instruments.length)}
                  <span class="atrade-run-period">{formatBarPeriod(forwardTest.bar_period)}</span>
                </h1>
                {#if forwardTest.allocated_capital_usd !== null}
                  {@const capitalNote = `Capital ${formatAmount(forwardTest.allocated_capital_usd)} USD`}
                  <span class="run-note run-capital" title={capitalNote}>{capitalNote}</span>
                {/if}
                <span class="atrade-run-actions">
                  {#if chartInstrument !== null}
                    <ChartViewSwitcher value={chartView} onValueChange={changeChartView} />
                  {/if}
                  {#if chartView === 'bars' && chartInstrument !== null}
                    <RunAddIndicatorButton chart={runChart} runKey={chartKey} strategyIndicators={forwardTest.strategy_indicators} />
                  {/if}
                  {#if canStop(forwardTest)}
                    <IconButton
                      label={describeStopButton(forwardTest)}
                      icon={StopFilledAlt16}
                      tone="error"
                      disabled={stoppingId === forwardTest.id}
                      onclick={() => void stop(forwardTest)}
                    />
                  {/if}
                  <IconButton
                    label={describeBacktestButton(forwardTest)}
                    icon={Compare16}
                    align="bottom-end"
                    disabled={!canBacktestSamePeriod(forwardTest) || isStartingBacktest}
                    onclick={() => void backtestSamePeriod(forwardTest)}
                  />
                  {#if canDelete(forwardTest)}
                    <IconButton
                      label="Delete forward test"
                      icon={TrashCan16}
                      align="bottom-end"
                      disabled={isDeleting}
                      onclick={() => {
                        requestDelete(forwardTest);
                      }}
                    />
                  {/if}
                </span>
              {/snippet}
              {#if actionFailure !== null}
                <InlineNotification
                  kind="error"
                  title={actionFailure.title}
                  subtitle={actionFailure.message}
                  lowContrast
                  onClose={() => {
                    actionFailure = null;
                  }}
                />
              {/if}
              {#if records.metrics !== null}
                <KeyMetricRow metrics={records.metrics} startCapitalUsd={readStartCapital(forwardTest)} />
              {/if}
              {#if chartView === 'bars' && chartInstrument !== null}
                <div class="chart">
                  <RunBarChart
                    instrument={chartInstrument}
                    barPeriod={forwardTest.bar_period}
                    range={{
                      startUtc: forwardTest.created_at_utc,
                      ...(forwardTest.stopped_at_utc === null ? {} : { endUtc: forwardTest.stopped_at_utc }),
                    }}
                    label="Bar chart of {formatInstrument(chartInstrument)}, {forwardTest.bar_period} bars"
                    chart={runChart}
                    runKey={chartKey}
                    strategyIndicators={forwardTest.strategy_indicators}
                    records={records.fills}
                  />
                </div>
              {:else if records.metrics !== null}
                <div class="chart">
                  <EquityDrawdownChart
                    curves={[{ name: 'Equity', points: records.equity_curve, startCapitalUsd: readStartCapital(forwardTest) }]}
                    label="Equity and drawdown"
                    interruptions={chartInterruptions}
                    fill
                  />
                </div>
              {/if}
            </Panel>
          {:else}
            <Panel
              {...state}
              label="Forward test tables"
              tabs={{
                label: 'Forward test tables',
                items: TABLE_TABS,
                value: selectedTable,
                onValueChange: (value: string) => {
                  selectedTable = value as ForwardTestTable;
                },
              }}
            >
              {#if selectedTable === 'fills'}
                {#if chartInstrument === null}
                  <ForwardTestFillTable fills={records.fills} />
                {:else}
                  <ForwardTestFillTable
                    fills={records.fills}
                    selectedIndex={runChart.readSelectedRow(chartKey)}
                    onRowPoint={(row: number | null) => {
                      runChart.pointedRow = row;
                    }}
                    onRowSelect={selectFillRow}
                  />
                {/if}
              {:else if selectedTable === 'instruments'}
                <UniverseInstrumentTable instruments={records.instruments} countHeader="Fills" />
              {:else if selectedTable === 'comparison'}
                {#if records.same_period_backtests.length === 0}
                  <EmptyText text="No backtests of the same period" />
                {:else}
                  <ScrollRegion label="Comparison" fill>
                    <DataTable columns={COMPARISON_COLUMNS} size="sm">
                      {#snippet rows()}
                        {#each records.same_period_backtests as backtest (backtest.id)}
                          <tr>
                            <th scope="row" align="right">
                              <StatusIndicator
                                label={describeBacktestStatus(backtest.status)}
                                kind={findBacktestStatusKind(backtest.status)}
                                align="right"
                              />
                              <a
                                class="cds--link"
                                aria-label={`Compare with backtest #${String(backtest.id)}`}
                                href={resolve('/forward-tests/[forwardTestId]/comparison/[backtestId]', {
                                  forwardTestId: String(forwardTest.id),
                                  backtestId: String(backtest.id),
                                })}>#{backtest.id}</a
                              >
                            </th>
                            <td>{formatUtcTime(backtest.start_utc)}</td>
                            <td>{formatUtcTime(backtest.end_utc)}</td>
                            <td align="right">
                              {#if backtest.metrics !== null}
                                <ChangeText
                                  value={Number(backtest.metrics.total_return_percent)}
                                  text={formatPercent(backtest.metrics.total_return_percent)}
                                />
                              {/if}
                            </td>
                          </tr>
                        {/each}
                      {/snippet}
                    </DataTable>
                  </ScrollRegion>
                {/if}
              {:else}
                <ScrollRegion label="Logs" fill>
                  {#if forwardTest.error_message !== null}
                    <pre class="atrade-run-log">{forwardTest.error_message}</pre>
                  {/if}
                  <DataTable columns={EVENT_COLUMNS} size="sm">
                    {#snippet rows()}
                      {#each listForwardTestEvents(forwardTest) as event, eventIndex (eventIndex)}
                        <tr>
                          <td>{formatUtcTime(event.timeUtc)}</td>
                          <td>{event.text}</td>
                        </tr>
                      {/each}
                    {/snippet}
                  </DataTable>
                </ScrollRegion>
              {/if}
            </Panel>
          {/if}
        {/snippet}
      </PanelSplit>
    {/if}
  </RunCenter>

  <AssistantColumn />
</Workbench>

{#if deleteTarget !== null}
  {@const target = deleteTarget}
  <Dialog
    open={isDeleteDialogOpen}
    onOpenChange={(open: boolean) => {
      isDeleteDialogOpen = open;
    }}
    title={`Delete forward test #${String(target.id)}?`}
    primaryText="Delete forward test"
    primaryKind="danger"
    busy={isDeleting}
    onPrimary={() => {
      void removeForwardTest(target);
    }}
  >
    <p>Its records are deleted. The paper account history stays.</p>
  </Dialog>
{/if}

<StartForwardTestDialog
  open={workbench.isStartDialogOpen}
  onOpenChange={workbench.changeStartDialog}
  onStarted={openStartedForwardTest}
/>

<style>
  /* The actions keep their place: a narrow header line clips the note, and its title gives the full text. */
  .run-note {
    flex: 0 1 auto;
    min-inline-size: 0;
    overflow: hidden;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--cds-text-secondary);
  }

  .run-capital {
    font-variant-numeric: tabular-nums;
  }

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }
</style>
