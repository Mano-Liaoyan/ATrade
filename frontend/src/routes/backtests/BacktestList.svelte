<!-- The backtest list of the backtest workbench (the body of the "Backtests" side column): 32px rows with the number,
     the strategy version, the instrument symbol, the status (icon and word), and the total return (ChangeText). The open
     backtest (or both compared backtests) has the Carbon selected row color. A click on a row opens its backtest.
     When 2 or more rows are checked, the Carbon batch action bar shows Compare: it opens the comparison of 2 backtests of the same strategy, and its
     text says why Compare is not available (docs/architecture section 9.5). -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import {
    checkComparisonSelection,
    describeBacktestStatus,
    findBacktestStatusKind,
    formatPercent,
    type Backtest,
  } from '#lib/backtest';
  import { Checkbox, DataTable, InlineNotification, StatusIndicator, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText } from '#lib/foundation/value_format';
  import { formatVersionLabel } from '#lib/strategy';

  interface Props {
    backtests: Backtest[];
    /** The read error of the list, or an empty text. */
    errorMessage: string;
    openBacktestId: number | null;
    /** The compared backtests of a comparison page: their rows have the open row color too. */
    comparedBacktestIds?: readonly number[];
  }

  const { backtests, errorMessage, openBacktestId, comparedBacktestIds = [] }: Props = $props();

  const COMPARED_BACKTEST_COUNT = 2;
  const COLUMNS: TableColumn[] = [
    { header: 'Select', isSelection: true },
    { header: '#', align: 'right' },
    { header: 'Strategy' },
    { header: 'Instrument' },
    { header: 'Status' },
    { header: 'Return', align: 'right' },
  ];

  let checkedIds: number[] = $state([]);
  const comparison = $derived(checkComparisonSelection(backtests, checkedIds));
  const showsBatchActions = $derived(checkedIds.length >= COMPARED_BACKTEST_COUNT);
  const selectionText = $derived.by(() => {
    if (comparison.kind === 'ready') {
      return '2 backtests selected';
    }
    return checkedIds.length > COMPARED_BACKTEST_COUNT
      ? 'Select only 2 backtests'
      : 'Only backtests of the same strategy can be compared';
  });

  function toggleChecked(id: number, isChecked: boolean): void {
    checkedIds = isChecked ? [...checkedIds, id] : checkedIds.filter((checkedId) => checkedId !== id);
  }

  function backtestHref(id: number): string {
    return resolve('/backtests/[[backtestId]]', { backtestId: String(id) });
  }

  function openRow(event: MouseEvent, id: number): void {
    // The checkbox and the link in the row do their own action.
    if (event.target instanceof Element && event.target.closest('a, input, label') !== null) {
      return;
    }
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- backtestHref resolves the path.
    void goto(backtestHref(id));
  }
</script>

{#if showsBatchActions}
  <section class="cds--table-toolbar cds--table-toolbar--sm cds--layout--size-sm batch-toolbar" aria-label="Selected backtests">
    <div class="cds--batch-actions cds--batch-actions--active">
      <div class="cds--batch-summary">
        <p class="cds--batch-summary__para" role="status" aria-label="Comparison selection">{selectionText}</p>
      </div>
      <div class="cds--action-list">
        {#if comparison.kind === 'ready'}
          <a
            class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm"
            href={resolve('/backtests/[backtestId]/comparison/[otherBacktestId]', {
              backtestId: String(comparison.firstBacktestId),
              otherBacktestId: String(comparison.secondBacktestId),
            })}>Compare</a
          >
        {:else}
          <button type="button" class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm" disabled>Compare</button>
        {/if}
        <button
          type="button"
          class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm cds--batch-summary__cancel"
          onclick={() => {
            checkedIds = [];
          }}>Cancel</button
        >
      </div>
    </div>
  </section>
{/if}

{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Backtests not read" subtitle={errorMessage} lowContrast />
{:else}
  <div class="list">
    <ScrollRegion label="Backtest list" fill>
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each backtests as item (item.id)}
            <tr
              class={[
                'backtest-row',
                (item.id === openBacktestId || comparedBacktestIds.includes(item.id)) && 'cds--data-table--selected',
              ]}
              onclick={(event) => {
                openRow(event, item.id);
              }}
            >
              <td class="cds--table-column-checkbox">
                <Checkbox
                  label={`Select backtest #${String(item.id)}`}
                  hideLabel
                  checked={checkedIds.includes(item.id)}
                  onCheckedChange={(isChecked: boolean) => {
                    toggleChecked(item.id, isChecked);
                  }}
                />
              </td>
              <th scope="row" align="right">
                <a
                  class="row-link"
                  href={resolve('/backtests/[[backtestId]]', { backtestId: String(item.id) })}
                  aria-current={item.id === openBacktestId ? 'page' : undefined}>#{item.id}</a
                >
              </th>
              <td>
                <span class="strategy-name" title={formatVersionLabel(item.strategy_name, item.version_number)}
                  >{formatVersionLabel(item.strategy_name, item.version_number)}</span
                >
              </td>
              <td>{item.symbol}</td>
              <td>
                <StatusIndicator label={describeBacktestStatus(item.status)} kind={findBacktestStatusKind(item.status)} />
              </td>
              <td align="right">
                {#if item.metrics !== null}
                  <ChangeText
                    value={Number(item.metrics.total_return_percent)}
                    text={formatPercent(item.metrics.total_return_percent)}
                  />
                {/if}
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  </div>
{/if}

<style>
  /* The Carbon batch action bar fills the toolbar line (32px, size sm) above the list. */
  .batch-toolbar {
    flex: none;
    position: relative;
    inline-size: 100%;
    block-size: var(--cds-spacing-07);
    min-block-size: var(--cds-spacing-07);
  }

  .list {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }

  .list :global(thead th) {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }

  /* Fixed column widths: the table never is wider than the column. Long text ends with an ellipsis. */
  .list :global(table) {
    table-layout: fixed;
  }

  .list :global(th:nth-child(1)) {
    inline-size: var(--cds-spacing-09);
  }

  .list :global(th:nth-child(2)) {
    inline-size: calc(var(--cds-spacing-09) + var(--cds-spacing-05));
  }

  .list :global(th:nth-child(4)) {
    inline-size: var(--cds-spacing-12);
  }

  .list :global(th:nth-child(5)),
  .list :global(th:nth-child(6)) {
    inline-size: calc(var(--cds-spacing-12) + var(--cds-spacing-06));
  }

  .list :global(td),
  .list :global(th) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .backtest-row {
    cursor: pointer;
  }

  /* A long strategy name ends with an ellipsis, so the status and the return stay in the column. */
  .strategy-name {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .row-link {
    color: inherit;
    font-variant-numeric: tabular-nums;
    text-decoration: none;
  }

  .row-link:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
