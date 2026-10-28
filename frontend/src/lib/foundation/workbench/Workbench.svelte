<!-- The workbench frame of a page: a row of side columns (SideColumn) and panels (PanelSplit) that fills the window
     below the app shell header. The page does not scroll: each region that can overflow scrolls in itself
     (ScrollRegion). The app shell gives the frame the window height when the main region has a workbench. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  const { children }: { children: Snippet } = $props();
</script>

<div class="atrade-workbench">
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
</style>
