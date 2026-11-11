<!-- The forward test list of the forward test workbench (the body of the "Forward tests" side column): 32px rows with
     the actual status icon from /ws/forward-tests before the number (the tooltip names the status), the strategy
     version, and the instrument symbol. The open forward test has the Carbon selected row color. A click on a row opens its forward
     test. Stop and "Backtest the same period" are in the header line of the open forward test. A right-click on a row
     opens its context menu: "Open in new tab", "Stop forward test" while it can stop, and "Delete forward test" after
     its end. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { ContextMenu, DataTable, StatusIndicator, type ContextMenuItem, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    canDelete,
    canStop,
    describeForwardTestStatus,
    describeForwardTestUniverse,
    findForwardTestStatusKind,
    type ForwardTest,
  } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';

  interface Props {
    forwardTests: ForwardTest[];
    openForwardTestId: number | null;
    /** "Stop forward test" of the context menu. Without it, the menu has no Stop. */
    onStop?: (forwardTest: ForwardTest) => void;
    /** "Delete forward test" of the context menu: the page asks before the delete. Without it, the menu has no Delete. */
    onDeleteRequest?: (forwardTest: ForwardTest) => void;
  }

  const { forwardTests, openForwardTestId, onStop, onDeleteRequest }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Strategy' },
    { header: 'Instrument' },
  ];

  function forwardTestHref(id: number): string {
    return resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(id) });
  }

  function readMenuItems(key: string): ContextMenuItem[] {
    const forwardTest = forwardTests.find((item) => item.id === Number(key));
    if (forwardTest === undefined) {
      return [];
    }
    const items: ContextMenuItem[] = [
      {
        label: 'Open in new tab',
        onSelect: () => {
          window.open(forwardTestHref(forwardTest.id), '_blank', 'noopener');
        },
      },
    ];
    if (onStop !== undefined && canStop(forwardTest)) {
      items.push({
        label: 'Stop forward test',
        divider: true,
        danger: true,
        onSelect: () => {
          onStop(forwardTest);
        },
      });
    }
    if (onDeleteRequest !== undefined && canDelete(forwardTest)) {
      items.push({
        label: 'Delete forward test',
        divider: true,
        danger: true,
        onSelect: () => {
          onDeleteRequest(forwardTest);
        },
      });
    }
    return items;
  }

  function openRow(event: MouseEvent, id: number): void {
    // The link in the row does its own action.
    if (event.target instanceof Element && event.target.closest('a') !== null) {
      return;
    }
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- forwardTestHref resolves the path.
    void goto(forwardTestHref(id));
  }
</script>

<div class="list">
  <ContextMenu readLabel={(key: string) => `Forward test #${key}`} readItems={readMenuItems}>
    <ScrollRegion label="Forward test list" fill>
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each forwardTests as forwardTest (forwardTest.id)}
            {@const versionLabel = formatVersionLabel(forwardTest.strategy_name, forwardTest.version_number)}
            <tr
              data-context-key={forwardTest.id}
              class={['forward-test-row', forwardTest.id === openForwardTestId && 'cds--data-table--selected']}
              onclick={(event) => {
                openRow(event, forwardTest.id);
              }}
            >
              <th scope="row" align="right">
                <span class="status-id">
                  <StatusIndicator
                    kind={findForwardTestStatusKind(forwardTest.status)}
                    label={describeForwardTestStatus(forwardTest.status)}
                    align="right"
                  />
                  <a
                    class="row-link"
                    href={resolve('/forward-tests/[[forwardTestId]]', { forwardTestId: String(forwardTest.id) })}
                    aria-current={forwardTest.id === openForwardTestId ? 'page' : undefined}>#{forwardTest.id}</a
                  >
                </span>
              </th>
              <td><span class="strategy-name" title={versionLabel}>{versionLabel}</span></td>
              <td>{forwardTest.symbol ?? describeForwardTestUniverse(forwardTest)}</td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  </ContextMenu>
</div>

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

  /* Fixed column widths: the table never is wider than the column. Long text ends with an ellipsis. */
  .list :global(table) {
    table-layout: fixed;
  }

  /* The status icon and the number. */
  .list :global(th:nth-child(1)) {
    inline-size: var(--cds-spacing-12);
  }

  .list :global(th:nth-child(3)) {
    inline-size: calc(var(--cds-spacing-12) + var(--cds-spacing-09));
  }

  .list :global(td),
  .list :global(th) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .forward-test-row {
    cursor: pointer;
  }

  /* A long strategy name ends with an ellipsis, so the instrument stays in the column. */
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

  /* The status icon keeps the start of the cell and the number keeps the end, so the icons are in one line for
     each number length. */
  .status-id {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
  }

  .status-id > a {
    margin-inline-start: auto;
    font-variant-numeric: tabular-nums;
  }
</style>
