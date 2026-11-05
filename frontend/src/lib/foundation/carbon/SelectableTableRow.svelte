<!-- A Carbon data table row that the user can point at and select, for example a trade row that links to its mark on
     the bar chart (docs/architecture/indicator.md section 23.9.9). The row itself takes the focus. The pointer or the
     focus on the row gives `onRowPoint` the row index (null when it goes). A click on the row, or Enter, gives
     `onRowSelect` the index. The selected row has the Carbon selected row color and `aria-current`. The row header
     cell shows the row number, unless `hasRowNumber` is false. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    index: number;
    isSelected: boolean;
    hasRowNumber?: boolean;
    onRowPoint?: ((index: number | null) => void) | undefined;
    onRowSelect: (index: number) => void;
    children: Snippet;
  }

  const { index, isSelected, hasRowNumber = true, onRowPoint, onRowSelect, children }: Props = $props();
</script>

<tr
  class={['selectable-row', isSelected && 'cds--data-table--selected']}
  tabindex="0"
  aria-current={isSelected ? 'true' : undefined}
  onpointerenter={() => {
    onRowPoint?.(index);
  }}
  onpointerleave={() => {
    onRowPoint?.(null);
  }}
  onfocus={() => {
    onRowPoint?.(index);
  }}
  onblur={() => {
    onRowPoint?.(null);
  }}
  onclick={() => {
    onRowSelect(index);
  }}
  onkeydown={(event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      onRowSelect(index);
    }
  }}
>
  {#if hasRowNumber}
    <th scope="row" align="right">{index + 1}</th>
  {/if}
  {@render children()}
</tr>

<style>
  .selectable-row {
    cursor: pointer;
  }

  /* The Carbon focus: a 2px --cds-focus inset border. The cells draw it, because not all browsers draw an outline on a
     table row. */
  .selectable-row:focus {
    outline: none;
  }

  .selectable-row:focus-visible > :global(*) {
    box-shadow:
      inset 0 2px 0 0 var(--cds-focus),
      inset 0 -2px 0 0 var(--cds-focus);
  }

  .selectable-row:focus-visible > :global(:first-child) {
    box-shadow:
      inset 2px 0 0 0 var(--cds-focus),
      inset 0 2px 0 0 var(--cds-focus),
      inset 0 -2px 0 0 var(--cds-focus);
  }

  .selectable-row:focus-visible > :global(:last-child) {
    box-shadow:
      inset -2px 0 0 0 var(--cds-focus),
      inset 0 2px 0 0 var(--cds-focus),
      inset 0 -2px 0 0 var(--cds-focus);
  }
</style>
