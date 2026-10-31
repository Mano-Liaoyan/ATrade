<!-- The warning that a page shows while its live socket is not connected. openLiveSocket connects again by itself. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';

  interface Props {
    // The last value that openLiveSocket gave to onConnectionChange.
    isConnected: boolean;
  }

  const { isConnected }: Props = $props();
</script>

{#if !isConnected}
  <InlineNotification kind="warning" title="Live updates paused" lowContrast />
{/if}
