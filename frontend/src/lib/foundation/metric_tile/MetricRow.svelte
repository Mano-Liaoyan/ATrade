<!-- One line of metric tiles (MetricTile), each tile the same width, with 1px dividers. It is a description list named
     by `label`. All pages show their key metrics in this row (spec #99). -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  const { label, children }: { label: string; children: Snippet } = $props();
</script>

<dl class="metric-row" aria-label={label}>
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
</style>
