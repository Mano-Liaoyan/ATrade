<!-- The header cell of a sortable Carbon data table column (the table has class "cds--data-table--sort"). A click
     calls onSort. The sorted column shows an arrow up (ascending) or down (descending) and has aria-sort. -->
<script lang="ts">
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import ArrowsVertical16 from '@carbon/icons/es/arrows--vertical/16.js';
  import Icon from './Icon.svelte';

  interface Props {
    label: string;
    /** The direction of this column, or null when the table is sorted by another column. */
    direction: 'ascending' | 'descending' | null;
    align?: 'left' | 'right';
    onSort: () => void;
  }

  const { label, direction, align, onSort }: Props = $props();
</script>

<th scope="col" class="cds--table-sort__header" {align} aria-sort={direction ?? 'none'}>
  <button
    type="button"
    class={[
      'cds--table-sort',
      direction !== null && 'cds--table-sort--active',
      direction === 'descending' && 'cds--table-sort--descending',
    ]}
    onclick={onSort}
  >
    <span class="cds--table-sort__flex">
      <div class="cds--table-header-label" title={label}>{label}</div>
      <Icon icon={ArrowUp16} class="cds--table-sort__icon" />
      <Icon icon={ArrowsVertical16} class="cds--table-sort__icon-unsorted" />
    </span>
  </button>
</th>

<style>
  /* A number column puts its label at the end, like its cells. */
  th[align='right'] .cds--table-header-label {
    flex: 1;
    text-align: end;
  }
</style>
