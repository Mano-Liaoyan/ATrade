<!-- A Carbon data table row that the user can point at and select, for example a trade row that links to its mark on
     the bar chart (docs/architecture/indicator.md section 23.9.9). The pointer or the focus in the row gives `onRowPoint` the row index
     (null when it goes). A click on the row, or Enter on the number button of the row header, gives `onRowSelect` the
     index. The selected row has the Carbon selected row color, and its button is pressed. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    index: number;
    /** The accessible name of the number button in the row header, for example "Show trade 3 on the bar chart". */
    label: string;
    isSelected: boolean;
    onRowPoint?: ((index: number | null) => void) | undefined;
    onRowSelect: (index: number) => void;
    children: Snippet;
  }

  const { index, label, isSelected, onRowPoint, onRowSelect, children }: Props = $props();
</script>

<tr
  class={['selectable-row', isSelected && 'cds--data-table--selected']}
  onpointerenter={() => {
    onRowPoint?.(index);
  }}
  onpointerleave={() => {
    onRowPoint?.(null);
  }}
  onfocusin={() => {
    onRowPoint?.(index);
  }}
  onfocusout={() => {
    onRowPoint?.(null);
  }}
  onclick={() => {
    onRowSelect(index);
  }}
>
  <th scope="row" align="right">
    <button
      type="button"
      class="row-button"
      aria-label={label}
      aria-pressed={isSelected}
      onclick={(event: MouseEvent) => {
        // The row click handler selects the row.
        event.stopPropagation();
        onRowSelect(index);
      }}>{index + 1}</button
    >
  </th>
  {@render children()}
</tr>

<style>
  .selectable-row {
    cursor: pointer;
  }

  .row-button {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    font-variant-numeric: tabular-nums;
    cursor: pointer;
  }

  .row-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }
</style>
