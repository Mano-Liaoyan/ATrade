<!-- The strategy list of the strategy workbench (the body of the "Strategies" side column): 32px rows with the strategy
     name and its latest version. The open strategy has the Carbon selected row color, like the backtest list. A click
     on a row opens its strategy. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { DataTable, InlineNotification, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { StrategyListItem } from '#lib/strategy';

  interface Props {
    strategies: StrategyListItem[];
    /** The read error of the list, or an empty text. */
    errorMessage: string;
    openStrategyId: number | null;
  }

  const { strategies, errorMessage, openStrategyId }: Props = $props();

  const COLUMNS: TableColumn[] = [{ header: 'Strategy' }, { header: 'Version', align: 'right' }];

  function strategyHref(id: number): string {
    return resolve('/strategies/[strategyId]', { strategyId: String(id) });
  }

  function openRow(event: MouseEvent, id: number): void {
    // The link in the row does its own action.
    if (event.target instanceof Element && event.target.closest('a') !== null) {
      return;
    }
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- strategyHref resolves the path.
    void goto(strategyHref(id));
  }
</script>

{#if errorMessage !== ''}
  <InlineNotification kind="error" title="Strategies not read" subtitle={errorMessage} lowContrast />
{:else}
  <div class="list">
    <ScrollRegion label="Strategy list" fill>
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each strategies as item (item.id)}
            <tr
              class={['strategy-row', item.id === openStrategyId && 'cds--data-table--selected']}
              onclick={(event) => {
                openRow(event, item.id);
              }}
            >
              <th scope="row">
                <a
                  class="row-link"
                  href={resolve('/strategies/[strategyId]', { strategyId: String(item.id) })}
                  title={item.name}
                  aria-current={item.id === openStrategyId ? 'page' : undefined}>{item.name}</a
                >
              </th>
              <td align="right">v{item.latest_version_number}</td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  </div>
{/if}

<style>
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

  /* Fixed column widths: the table never is wider than the column. A long name ends with an ellipsis. */
  .list :global(table) {
    table-layout: fixed;
  }

  .list :global(th:nth-child(2)) {
    inline-size: var(--cds-spacing-11);
  }

  .list :global(td),
  .list :global(th) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .strategy-row {
    cursor: pointer;
  }

  .row-link {
    color: inherit;
    font-weight: inherit;
    text-decoration: none;
  }

  .row-link:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
