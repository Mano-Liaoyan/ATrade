<!-- The Bits UI tooltip provider. The app shell renders it once around all pages, so each Tooltip finds it. -->
<script lang="ts">
  import { Tooltip } from 'bits-ui';
  import type { Snippet } from 'svelte';

  const { children }: { children: Snippet } = $props();

  // Carbon opens a tooltip after a short delay. The Bits UI default (700 ms) feels slow.
  const OPEN_DELAY_MILLISECONDS = 100;
</script>

<Tooltip.Provider delayDuration={OPEN_DELAY_MILLISECONDS}>
  {@render children()}
</Tooltip.Provider>
