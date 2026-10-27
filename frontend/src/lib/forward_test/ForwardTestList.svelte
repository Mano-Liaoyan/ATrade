<!-- The forward tests with their actual status from /ws/forward-tests. The row menu stops a running forward test and
     starts a backtest of the same period for one with a start balance (docs/architecture/forward_test.md 12.10). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import {
    DataTable,
    InlineNotification,
    OverflowMenu,
    StatusIndicator,
    type OverflowMenuItem,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount, formatBarPeriod } from '#lib/foundation/value_format';
  import {
    canBacktestSamePeriod,
    canStop,
    describeForwardTestStatus,
    findForwardTestStatusKind,
    formatLocalTime,
    showsCrashCount,
    stopForwardTest,
    type ForwardTest,
  } from './forward_test_api';

  interface Props {
    forwardTests: ForwardTest[];
    // The page starts the backtest and opens the comparison page.
    onBacktestSamePeriod: (forwardTestId: number) => void;
  }

  const { forwardTests, onBacktestSamePeriod }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Forward test' },
    { header: 'Strategy version' },
    { header: 'Instrument' },
    { header: 'Bar period' },
    { header: 'Status' },
    { header: 'Client ID', align: 'right' },
    { header: 'Start balance (USD)', align: 'right' },
    { header: 'Started' },
    { header: 'End time (local)' },
    { header: 'Actions', isMenu: true },
  ];

  let stoppingIds = $state<number[]>([]);
  let stopFailure = $state<{ forwardTestId: number; message: string } | null>(null);

  async function stop(forwardTestId: number): Promise<void> {
    stopFailure = null;
    stoppingIds = [...stoppingIds, forwardTestId];
    const result = await stopForwardTest(fetch, forwardTestId);
    if (result.kind === 'failed') {
      stoppingIds = stoppingIds.filter((stoppingId) => stoppingId !== forwardTestId);
      stopFailure = { forwardTestId, message: result.message };
    }
  }

  // Only the actions that apply to the forward test. A forward test without an action has no menu.
  function makeMenuItems(forwardTest: ForwardTest): OverflowMenuItem[] {
    const items: OverflowMenuItem[] = [];
    if (canStop(forwardTest)) {
      const isStopping = stoppingIds.includes(forwardTest.id);
      items.push({
        label: isStopping ? 'Stop requested' : 'Stop forward test',
        disabled: isStopping,
        danger: true,
        onSelect: () => void stop(forwardTest.id),
      });
    }
    if (canBacktestSamePeriod(forwardTest)) {
      items.push({
        label: 'Backtest the same period',
        onSelect: () => {
          onBacktestSamePeriod(forwardTest.id);
        },
      });
    }
    return items;
  }
</script>

<div class="forward-test-list">
  {#if stopFailure !== null}
    <InlineNotification
      kind="error"
      title={`Forward test ${String(stopFailure.forwardTestId)} not stopped`}
      subtitle={stopFailure.message}
      lowContrast
      onClose={() => (stopFailure = null)}
    />
  {/if}
  {#if forwardTests.length === 0}
    <p>No forward test yet.</p>
  {:else}
    <ScrollRegion label="Forward tests" maxHeight="24rem">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each forwardTests as forwardTest (forwardTest.id)}
            {@const menuItems = makeMenuItems(forwardTest)}
            <tr>
              <th scope="row">
                <a class="cds--link" href={resolve('/forward-tests/[forwardTestId]', { forwardTestId: String(forwardTest.id) })}
                  >#{forwardTest.id}</a
                >
              </th>
              <td>{forwardTest.strategy_name} v{forwardTest.version_number}</td>
              <td>{forwardTest.symbol} / {forwardTest.exchange} / {forwardTest.currency}</td>
              <td>{formatBarPeriod(forwardTest.bar_period)}</td>
              <td>
                <StatusIndicator
                  kind={findForwardTestStatusKind(forwardTest.status)}
                  label={describeForwardTestStatus(forwardTest.status)}
                />
                {#if showsCrashCount(forwardTest)}
                  <span class="note">Crashes in a row: {forwardTest.crash_count} of 3</span>
                {/if}
                {#if forwardTest.error_message !== null}
                  <span class="note error">{forwardTest.error_message}</span>
                {/if}
              </td>
              <td align="right">{forwardTest.client_id ?? ''}</td>
              <td align="right">
                {forwardTest.start_balance_usd === null ? '' : formatAmount(forwardTest.start_balance_usd)}
              </td>
              <td>{formatUtcTime(forwardTest.created_at_utc)}</td>
              <td>{formatLocalTime(forwardTest.end_time_utc)}</td>
              <td class="cds--table-column-menu">
                {#if menuItems.length > 0}
                  <OverflowMenu label={`Actions for forward test ${String(forwardTest.id)}`} items={menuItems} size="sm" />
                {/if}
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</div>

<style>
  .forward-test-list {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
  }

  p {
    margin: 0;
  }

  /* A long value can break anywhere. A column name breaks only between words. */
  .forward-test-list :global(td) {
    overflow-wrap: anywhere;
  }

  .note {
    display: block;
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    color: var(--cds-text-secondary);
  }

  .error {
    color: var(--cds-text-error);
  }
</style>
