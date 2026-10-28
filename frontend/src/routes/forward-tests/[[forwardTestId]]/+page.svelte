<!-- Forward test page: a workbench (foundation/workbench, spec #99) with the structure of the backtest page. URL:
     /forward-tests/<id>; /forward-tests opens the newest forward test.
     Left: the "Forward tests" side column (ForwardTestList, live from /ws/forward-tests) with the "New forward test"
     button. Center: the panel of the open forward test (header line: number, strategy version, instrument, bar
     period, status, the red "Stop forward test" button while it can stop, and "Backtest the same period"; then the
     key metric row and the equity and drawdown curves with the interruptions in grey) over the
     Fills / Comparison / Logs panel. Comparison links to the comparison with each backtest of the same period. Logs
     shows the current error and the events (start, interruptions, stop). The open forward test reads again every
     2 seconds. The address #start-forward-test (command palette) opens the New forward test dialog. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import Compare16 from '@carbon/icons/es/compare/16.js';
  import StopFilledAlt16 from '@carbon/icons/es/stop--filled--alt/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { navigating, page } from '$app/state';
  import {
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    formatPercent,
    KeyMetricRow,
    type TimeInterval,
  } from '#lib/backtest';
  import {
    DataTable,
    IconButton,
    InlineNotification,
    StatusIndicator,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ChangeText, formatBarPeriod } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    canBacktestSamePeriod,
    canStop,
    describeForwardTestStatus,
    findForwardTestStatusKind,
    ForwardTestFillTable,
    ForwardTestsOnInstrumentsFeed,
    listForwardTestEvents,
    readForwardTestDetail,
    showsCrashCount,
    startSamePeriodBacktest,
    stopForwardTest,
    type ForwardTest,
    type ForwardTestDetail,
  } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';
  import { createInstrumentHref } from '../../instrument_href';
  import { START_FORWARD_TEST_FORM_ID } from '../../palette_commands';
  import ForwardTestList from '../ForwardTestList.svelte';
  import StartForwardTestDialog from '../StartForwardTestDialog.svelte';

  const READ_INTERVAL_MILLISECONDS = 2000;
  const START_FORWARD_TEST_HASH = `#${START_FORWARD_TEST_FORM_ID}`;

  // The same panels and sizes as the backtest page.
  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 160 },
    { id: 'tables', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the tables' },
  ];
  const COMPARISON_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Status' },
    { header: 'Start' },
    { header: 'End' },
    { header: 'Return', align: 'right' },
  ];
  const EVENT_COLUMNS: TableColumn[] = [{ header: 'Time' }, { header: 'Event' }];
  type ForwardTestTable = 'fills' | 'comparison' | 'logs';
  const TABLE_TABS: { value: ForwardTestTable; label: string }[] = [
    { value: 'fills', label: 'Fills' },
    { value: 'comparison', label: 'Comparison' },
    { value: 'logs', label: 'Logs' },
  ];

  const routeForwardTestId = $derived(page.params['forwardTestId']);
  const forwardTestId = $derived(routeForwardTestId === undefined ? null : Number(routeForwardTestId));

  // The one /ws/forward-tests socket of the page: the list.
  const feed = new ForwardTestsOnInstrumentsFeed();
  let detail = $state<ForwardTestDetail | null>(null);
  let detailMessage = $state('');
  let selectedTable: ForwardTestTable = $state('fills');
  let isStartDialogOpen = $state(false);
  // The failed header action and the reason from the backend.
  let actionFailure = $state<{ title: string; message: string } | null>(null);
  let stoppingId = $state<number | null>(null);
  let isStartingBacktest = $state(false);

  const shownDetail = $derived(detail !== null && detail.forward_test.id === forwardTestId ? detail : null);
  // An interruption that still lasts ends at the stop, or now (docs/architecture/forward_test.md 12.10).
  const chartInterruptions = $derived<TimeInterval[]>(
    (shownDetail?.forward_test.interruptions ?? []).map((interruption) => ({
      start_utc: interruption.started_at_utc,
      end_utc: interruption.ended_at_utc ?? shownDetail?.forward_test.stopped_at_utc ?? new Date().toISOString(),
    })),
  );

  $effect(() => feed.start(window.location));

  // /forward-tests opens the newest forward test. The same page component stays, so an open dialog stays open. A
  // navigation that runs (for example a click on a header link) wins.
  $effect(() => {
    if (navigating.to !== null) {
      return;
    }
    const newest = feed.forwardTests.reduce<ForwardTest | undefined>(
      (found, item) => (found === undefined || item.id > found.id ? item : found),
      undefined,
    );
    if (forwardTestId === null && newest !== undefined) {
      void goto(resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(newest.id) }), {
        replace: true,
        reset: false,
      });
    }
  });

  // The open forward test reads again every 2 seconds: a running forward test gets new records.
  $effect(() => {
    if (forwardTestId === null) {
      return;
    }
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    // A new value only after a change: then the chart keeps its zoom while nothing changes.
    let lastDetailText = '';
    const id = forwardTestId;
    actionFailure = null;
    stoppingId = null;

    async function readDetail(): Promise<void> {
      const result = await readForwardTestDetail(fetch, id);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        detailMessage = result.message;
      } else {
        detailMessage = '';
        const detailText = JSON.stringify(result.value);
        if (detailText !== lastDetailText) {
          lastDetailText = detailText;
          detail = result.value;
        }
      }
      timer = setTimeout(() => void readDetail(), READ_INTERVAL_MILLISECONDS);
    }

    void readDetail();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  // The command palette goes to #start-forward-test.
  $effect(() => {
    if (page.url.hash === START_FORWARD_TEST_HASH) {
      isStartDialogOpen = true;
    }
  });

  function changeStartDialog(open: boolean): void {
    isStartDialogOpen = open;
    if (!open && page.url.hash === START_FORWARD_TEST_HASH) {
      // Without the hash, the palette can open the dialog again.
      // eslint-disable-next-line svelte/no-navigation-without-resolve -- the current path, without its hash.
      void goto(page.url.pathname + page.url.search, { replace: true, reset: false });
    }
  }

  function openStartedForwardTest(started: ForwardTest): void {
    feed.forwardTests = [started, ...feed.forwardTests.filter((item) => item.id !== started.id)];
    void goto(resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(started.id) }));
  }

  async function stop(forwardTest: ForwardTest): Promise<void> {
    if (stoppingId !== null) {
      return;
    }
    stoppingId = forwardTest.id;
    actionFailure = null;
    const result = await stopForwardTest(fetch, forwardTest.id);
    if (result.kind === 'failed') {
      stoppingId = null;
      actionFailure = { title: 'Forward test not stopped', message: result.message };
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

<Workbench>
  <SideColumn label="Forward tests" side="start" width="30rem" storageKey="atrade.forward-test-page.list-column">
    {#snippet actions()}
      <IconButton
        label="New forward test"
        icon={Add16}
        onclick={() => {
          isStartDialogOpen = true;
        }}
      />
    {/snippet}
    <LiveUpdatesNotification isConnected={feed.isConnected} />
    <ForwardTestList forwardTests={feed.forwardTests} openForwardTestId={forwardTestId} />
  </SideColumn>

  {#if shownDetail === null}
    <div class="empty-main">
      {#if detailMessage !== ''}
        <InlineNotification kind="error" title="Forward test not read" subtitle={detailMessage} lowContrast />
      {:else if feed.isConnected && feed.forwardTests.length === 0}
        <p class="empty-word">No forward tests</p>
      {/if}
    </div>
  {:else}
    {@const forwardTest = shownDetail.forward_test}
    {@const records = shownDetail}
    <PanelSplit storageKey="atrade.forward-test-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'chart'}
          <Panel {...state} label={`Forward test #${String(forwardTest.id)}`}>
            {#snippet header()}
              <h1 class="run-title">
                <span class="run-number">#{forwardTest.id}</span>
                <a
                  class="cds--link"
                  href={resolve('/strategies/[strategyId]', { strategyId: String(forwardTest.strategy_id) })}
                  >{formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}</a
                >
                <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolves the path. -->
                <a class="cds--link" href={createInstrumentHref(forwardTest)}>{forwardTest.symbol}</a>
                <span class="run-period">{formatBarPeriod(forwardTest.bar_period)}</span>
              </h1>
              <span class="run-status" role="status" aria-label="Forward test status">
                <StatusIndicator
                  label={describeForwardTestStatus(forwardTest.status)}
                  kind={findForwardTestStatusKind(forwardTest.status)}
                />
              </span>
              {#if showsCrashCount(forwardTest)}
                <span class="run-note">Crashes in a row: {forwardTest.crash_count} of 3</span>
              {/if}
              <span class="run-actions">
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
            {#if records.metrics === null}
              <div class="state-area">
                <StatusIndicator
                  label={describeForwardTestStatus(forwardTest.status)}
                  kind={findForwardTestStatusKind(forwardTest.status)}
                />
              </div>
            {:else}
              <KeyMetricRow metrics={records.metrics} startCapitalUsd={forwardTest.start_balance_usd} trades={records.fills} />
              <div class="chart">
                <EquityDrawdownChart
                  curves={[{ name: 'Equity', points: records.equity_curve, startCapitalUsd: forwardTest.start_balance_usd }]}
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
              <ForwardTestFillTable fills={records.fills} />
            {:else if selectedTable === 'comparison'}
              {#if records.same_period_backtests.length === 0}
                <p class="empty-word">No backtests of the same period</p>
              {:else}
                <ScrollRegion label="Comparison" fill>
                  <DataTable columns={COMPARISON_COLUMNS} size="sm">
                    {#snippet rows()}
                      {#each records.same_period_backtests as backtest (backtest.id)}
                        <tr>
                          <th scope="row" align="right">
                            <a
                              class="cds--link"
                              aria-label={`Compare with backtest #${String(backtest.id)}`}
                              href={resolve('/forward-tests/[forwardTestId]/comparison/[backtestId]', {
                                forwardTestId: String(forwardTest.id),
                                backtestId: String(backtest.id),
                              })}>#{backtest.id}</a
                            >
                          </th>
                          <td>
                            <StatusIndicator
                              label={describeBacktestStatus(backtest.status)}
                              kind={findBacktestStatusKind(backtest.status)}
                            />
                          </td>
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
                  <pre class="log-text">{forwardTest.error_message}</pre>
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
</Workbench>

<StartForwardTestDialog open={isStartDialogOpen} onOpenChange={changeStartDialog} onStarted={openStartedForwardTest} />

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

  .run-status,
  .run-note {
    flex: none;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    white-space: nowrap;
  }

  .run-note {
    color: var(--cds-text-secondary);
  }

  .run-actions {
    display: flex;
    flex: none;
    margin-inline-start: auto;
  }

  .state-area {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    font-size: var(--cds-heading-compact-02-font-size);
    line-height: var(--cds-heading-compact-02-line-height);
  }

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .empty-word {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
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
