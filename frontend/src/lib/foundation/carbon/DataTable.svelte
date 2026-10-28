<!-- Carbon data table. The columns give the header row. The `rows` snippet renders the <tr> elements of <tbody>.
     A number column has align "right": its cells must also have align="right", and they use tabular numbers.
     A menu column (an overflow menu in each row) has a header that only screen readers read.
     A selection column (a Checkbox in each row) also has a header that only screen readers read.
     A row can start with <th scope="row">: it is the row header.
     The open row of a list has class "cds--data-table--selected" (selected row color and an interactive bar). -->
<script module lang="ts">
  export interface TableColumn {
    header: string;
    align?: 'left' | 'right';
    // The column of the row overflow menus: cells use class "cds--table-column-menu".
    isMenu?: boolean;
    // The column of the row selection checkboxes: cells use class "cds--table-column-checkbox".
    isSelection?: boolean;
  }
</script>

<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    columns: TableColumn[];
    size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    zebra?: boolean;
    rows: Snippet;
  }

  const { columns, size = 'lg', zebra = false, rows }: Props = $props();
</script>

<div class="cds--data-table-container data-table">
  <div class="cds--data-table-content">
    <table class={['cds--data-table', `cds--data-table--${size}`, zebra && 'cds--data-table--zebra']}>
      <thead>
        <tr>
          {#each columns as column (column.header)}
            {#if column.isMenu === true}
              <th scope="col" class="cds--table-column-menu"><span class="cds--visually-hidden">{column.header}</span></th>
            {:else if column.isSelection === true}
              <th scope="col" class="cds--table-column-checkbox"><span class="cds--visually-hidden">{column.header}</span></th>
            {:else}
              <th scope="col" align={column.align}><div class="cds--table-header-label">{column.header}</div></th>
            {/if}
          {/each}
        </tr>
      </thead>
      <tbody>
        {@render rows()}
      </tbody>
    </table>
  </div>
</div>

<style>
  /* Carbon aligns the number cells, but not the label inside a number header. */
  .data-table th[align='right'] .cds--table-header-label {
    text-align: end;
  }

  /* Carbon gives every th the header color. A row header (<th scope="row">) in the body looks like the other cells. */
  .data-table tbody :global(th) {
    background-color: transparent;
  }

  /* The open row of a list (the open instrument, backtest, forward test, or strategy) has the Carbon class
     cds--data-table--selected: the Carbon selected row color on every cell, also on the row header, and an interactive
     bar at the start of the row. All lists of all pages show the open row so. */
  .data-table tbody :global(tr.cds--data-table--selected > :is(td, th)) {
    background-color: var(--cds-layer-selected-01);
    color: var(--cds-text-primary);
  }

  .data-table tbody :global(tr.cds--data-table--selected > :first-child) {
    box-shadow: inset 3px 0 0 var(--cds-border-interactive);
  }

  .data-table :global(td[align='right']) {
    font-variant-numeric: tabular-nums;
  }
</style>
