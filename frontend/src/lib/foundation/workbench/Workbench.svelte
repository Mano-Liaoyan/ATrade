<!-- The workbench frame of a page: a row of side columns (SideColumn) and panels (PanelSplit) that fills the window
     below the app shell header. The page does not scroll: each region that can overflow scrolls in itself
     (ScrollRegion). The app shell gives the frame the window height when the main region has a workbench. While a
     side column is maximized, each other part of the row (the center area) is a 32px rail, and its content stays in
     the page. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { provideWorkbenchRail } from './workbench_rail.svelte';

  const { children }: { children: Snippet } = $props();

  const rail = provideWorkbenchRail();
</script>

<div class={['atrade-workbench', rail.isRail && 'atrade-workbench--rail']}>
  {@render children()}
</div>

<style>
  .atrade-workbench {
    display: flex;
    block-size: 100%;
    min-block-size: 0;
    min-inline-size: 0;
    background: var(--cds-background);
  }

  .atrade-workbench--rail > :global(:not(.side-column)) {
    flex: none;
    inline-size: var(--cds-spacing-07);
    min-inline-size: 0;
    border-inline-end: 1px solid var(--cds-border-subtle-01);
    overflow: hidden;
  }

  .atrade-workbench--rail > :global(:not(.side-column)) > :global(*) {
    display: none;
  }
</style>
