<!-- Metric tiles (MetricTile), each tile the same width, with 1px dividers. It is a description list named by `label`.
     All pages show their key metrics in this row (spec #99). The tiles wrap to more lines when the width does not fit
     them, because a key metric that the user cannot read is worse than a shorter chart. With `columns`, the tiles fill
     that many columns (a narrow side column, for example the order panel of the instrument page). -->
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
    grid-template-columns: repeat(auto-fit, minmax(6.5rem, 1fr));
    gap: 1px;
    margin: 0;
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .metric-row--columns {
    grid-template-columns: repeat(var(--metric-row-columns), minmax(0, 1fr));
  }
</style>
