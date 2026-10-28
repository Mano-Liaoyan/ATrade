<!-- One line of metric tiles (MetricTile), each tile the same width, with 1px dividers. It is a description list named
     by `label`. All pages show their key metrics in this row (spec #99). With `columns`, the tiles fill that many
     columns and wrap to more lines (a narrow side column, for example the order panel of the instrument page). -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  const { label, columns, children }: { label: string; columns?: number; children: Snippet } = $props();
</script>

<dl
  class={['metric-row', columns !== undefined && 'metric-row--columns']}
  style:--metric-row-columns={columns}
  aria-label={label}
>
  {@render children()}
</dl>

<style>
  .metric-row {
    display: grid;
    flex: none;
    grid-auto-columns: minmax(0, 1fr);
    grid-auto-flow: column;
    gap: 1px;
    margin: 0;
    background: var(--cds-border-subtle-01);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .metric-row--columns {
    grid-auto-flow: row;
    grid-template-columns: repeat(var(--metric-row-columns), minmax(0, 1fr));
  }
</style>
